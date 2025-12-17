from collections.abc import Callable
from typing import Any, TypeVar, cast, get_origin

from pydantic import ConfigDict
from pydantic.json_schema import JsonSchemaValue, JsonValue


def get_static_json_schema_extra(config: ConfigDict) -> JsonSchemaValue:
    """
    Get the static *extra* JSON Schema from a Pydantic model config dictionary.

    Parameters
    ----------
    config : ConfigDict
        Config dictionary

    Returns
    -------
    JsonSchemaValue
        Extra JSON Schema from `config`, or `{}` if `config` has no extra JSON Schema

    Raises
    ------
    ValueError
        If `config` contains dynamic extra JSON Schema (`JsonSchemaExtraCallable`)
    """
    json_schema: (
        JsonSchemaValue
        | Callable[[JsonSchemaValue], None]
        | Callable[[JsonSchemaValue, type[Any]], None]
        | None
    ) = config.get("json_schema_extra", None)
    if json_schema is None:
        json_schema = {}
        config["json_schema_extra"] = json_schema
    else:
        origin = cast(type, get_origin(JsonSchemaValue))
        if isinstance(json_schema, origin):
            return cast(JsonSchemaValue, json_schema)
        else:
            raise ValueError(
                f'expected value of config\'s "json_schema_extra" key to be a `{origin.__name__}`, but it is a `{type(json_schema).__name__}`'
            )
    return json_schema


def put_all_of(json_schema: JsonSchemaValue, operands: list[JsonSchemaValue]) -> None:
    """
    Insert an `"allOf"` schema composition clause into a JSON Schema.

    If the target JSON Schema already contains an `"allOf"` clause, the `operands` are added to the
    existing `"allOf"` clause.

    Parameters
    ----------
    json_schema : JsonSchemaValue
        Target JSON Schema
    operands : list[JsonSchemaValue]
        Non-empty list of operands for the `"allOf"` clause
    """
    _verify_json_schema_value(("json_schema", json_schema))
    _verify_operands_not_empty(JsonSchemaValue, operands)
    if "allOf" not in json_schema:
        json_schema["allOf"] = cast(JsonValue, operands)
    else:
        maybe_list = json_schema["allOf"]
        if isinstance(maybe_list, list):
            maybe_list += operands
        else:
            raise ValueError(
                f'expected value of "allOf" key to be a `list`, but it is a `{type(maybe_list).__name__}` in the JSON Schema {json_schema}'
            )


def put_any_of(json_schema: JsonSchemaValue, operands: list[JsonSchemaValue]) -> None:
    """
    Insert an `"anyOf"` schema composition clause into a JSON Schema.

    If the target JSON Schema already contains an `"anyOf"` clause, the existing clause is retained
    and the new one is added by adding both new and existing `"anyOf"` clauses to an `"allOf"`
    clause using `put_all_of`.

    Parameters
    ----------
    json_schema : JsonSchemaValue
        Target JSON Schema
    operands : list[JsonSchemaValue]
        Non-empty list of operands for the `"anyOf"` clause
    """
    _verify_json_schema_value(("json_schema", json_schema))
    _verify_operands_not_empty(JsonSchemaValue, operands)
    prev: JsonSchemaValue = {}
    try_move("anyOf", json_schema, prev)
    if not prev:
        json_schema["anyOf"] = cast(JsonValue, operands)
    else:
        put_all_of(json_schema, [prev, {"anyOf": cast(JsonValue, operands)}])


def put_one_of(json_schema: JsonSchemaValue, operands: list[JsonSchemaValue]) -> None:
    """
    Insert a `"oneOf"` schema composition clause into a JSON Schema.

    If the target JSON Schema already contains a `"oneOf"` clause, the existing clause is retained
    and the new one is added by adding both new and existing `"oneOf"` clauses to an `"allOf"`
    clause using `put_all_of`.

    Parameters
    ----------
    json_schema : JsonSchemaValue
        Target JSON Schema
    operands : list[JsonSchemaValue]
        Non-empty list of operands for the `"allOf"` clause
    """
    _verify_json_schema_value(("json_schema", json_schema))
    _verify_operands_not_empty(JsonSchemaValue, operands)
    prev: JsonSchemaValue = {}
    try_move("oneOf", json_schema, prev)
    if not prev:
        json_schema["oneOf"] = cast(JsonValue, operands)
    else:
        put_all_of(json_schema, [prev, {"oneOf": cast(JsonValue, operands)}])


def put_not(json_schema: JsonSchemaValue, operand: JsonSchemaValue) -> None:
    """
    Insert a `"not"` schema composition clause into a JSON Schema.

    If the target JSON Schema already contains a `"not"` clause, the existing clause is retained
    and the new one is added by refactoring the schema. Several refactorings are possible but in
    all cases the `"not"` clause will remain and will contain an `"anyOf"` clause as its direct
    child, and `operand` as a child of the `"anyOf"` clause.

    Parameters
    ----------
    json_schema : JsonSchemaValue
        Target JSON Schema
    operand : JsonSchemaValue
        Operand for the `"not"` clause
    """
    _verify_json_schema_value(("json_schema", json_schema), ("operand", operand))
    prev: JsonSchemaValue = {}
    try_move("not", json_schema, prev)

    # Simple case: if the JSON didn't already have a "not", we just add it.
    if not prev:
        json_schema["not"] = operand
        return

    not_schema = prev["not"]
    if not isinstance(not_schema, cast(type, get_origin(JsonSchemaValue))):
        raise TypeError(
            f'expected value of "not" key to be a `JsonSchemaValue`, but {repr(not_schema)} has type `{type(not_schema).__name__}` in the JSON Schema {json_schema}'
        )
    not_schema = cast(JsonSchemaValue, not_schema)

    # Next simplest case: the only child of the "not" is "anyOf".
    if len(not_schema) == 1 and "anyOf" in not_schema:
        not_any_of_schema = not_schema["anyOf"]
        if not isinstance(not_any_of_schema, list):
            raise ValueError(
                f'expected value of "anyOf" key under "not" to be a `list`, but is a {type(not_any_of_schema).__name__} in the JSON Schema {json_schema}'
            )
        not_any_of_schema.append(operand)
        json_schema["not"] = not_schema
        return

    # Most complex case: "not" either contains multiple keys, or a key that's not "anyOf".
    json_schema["not"] = {
        "anyOf": [
            not_schema,
            operand,
        ]
    }


def put_if(
    json_schema: JsonSchemaValue,
    condition: JsonSchemaValue | None,
    when_true: JsonSchemaValue | None,
    when_false: JsonSchemaValue | None = None,
) -> None:
    """
    Insert `"if"`/`"then"` conditional schema application elements with an optional `"else"` clause
    into a JSON Schema.

    If the target JSON Schema does not already contain an `"if"`/`"then"`/`"else"` elements, the new
    elements are added directly into the JSON Schema. If it does already contain them, then the
    existing `"if"`/`"then"`/`"else"` elements are moved into a separate object, the new ones are
    inserted into a second separate object, and both of these objects are added into the JSON
    Schema using `put_all_of`.

    Parameters
    ----------
    json_schema : JsonSchemaValue
        Target JSON Schema
    condition : JsonSchemaValue | None
        Operand for the `"if"` clause
    when_true : JsonSchemaValue | None
        Operand for the `"then"` clause
    when_false : JsonSchemaValue | None
        Operand for the `"else"` clause
    """
    _verify_json_schema_value(("json_schema", json_schema))
    if condition is not None:
        _verify_json_schema_value(("condition", condition))
    if when_true is not None:
        _verify_json_schema_value(("when_true", when_true))
    if when_false is not None:
        _verify_json_schema_value(("when_false", when_false))

    prev: JsonSchemaValue = {}
    try_move("if", json_schema, prev)
    try_move("then", json_schema, prev)
    try_move("else", json_schema, prev)

    def _put(dst: JsonSchemaValue) -> JsonSchemaValue:
        if condition:
            dst["if"] = condition
        if when_true:
            dst["then"] = when_true
        if when_false:
            dst["else"] = when_false
        return dst

    if not prev:
        _put(json_schema)
    else:
        put_all_of(json_schema, [prev, _put({})])


def put_required(json_schema: JsonSchemaValue, operands: list[str]) -> None:
    """
    Insert a `"required"` validation clause into a JSON Schema.

    If the target JSON Schema already contains a `"required"` clause, the existing clause is
    retained and `operands` is merged into it by appending the items that aren't already in the
    `"required"` clause to the end of it, in the order in which they appear in `operands`.

    Parameters
    ----------
    json_schema : JsonSchemaValue
        Target JSON Schema
    operands : list[str]
        Operands for the `"required"` clause
    """
    _verify_json_schema_value(("json_schema", json_schema))
    _verify_operands_not_empty(str, operands)
    if "required" in json_schema:
        required = json_schema["required"]
    else:
        required = []
        json_schema["required"] = required
    required += [p for p in operands if p not in required]


def put_properties(
    json_schema: JsonSchemaValue,
    new_properties: JsonSchemaValue,
) -> None:
    """
    Insert members into the `"properties"` applicator keyword within the schema for a value of type
    `"object"`.

    If the target JSON Schema already contains a `"properties"` clause, the new properties from
    `new_properties` are merged into it. Otherwise, a new `"properties"` clause is inserted into
    `json_schema` and and all properties from `new_properties` are inserted into it.

    Parameters
    ----------
    json_schema : JsonSchemaValue
        Target JSON Schema
    new_properties : JsonSchemaValue
        New properties to add to the `"properties"` clause within `json_schema`

    Raises
    ------
    ValueError
        If a property entry in `new_properties` can't be merged into the `"properties"` clause of
        `json_schema` because there's an existing `"properties"` clause that contains a property
        with the same name but a different value
    """
    _verify_json_schema_value(
        ("json_schema", json_schema), ("new_properties", new_properties)
    )
    origin = cast(type, get_origin(JsonSchemaValue))
    if "properties" in json_schema:
        properties = json_schema["properties"]
        if not isinstance(properties, origin):
            raise TypeError(
                f'expected value of "properties" key to be a `JsonSchemaValue`, but {repr(properties)} has type `{type(properties).__name__}` in the JSON Schema {json_schema}'
            )
        already_in = True
    else:
        properties = {}
        already_in = False
    for k, v in new_properties.items():
        if not isinstance(v, origin):
            raise TypeError(
                f"expected property value for {repr(k)} key to be a `JsonSchemaValue`, but {repr(v)} has type `{type(v).__name__}` in the new properties {repr(new_properties)}"
            )
        elif k not in properties:
            properties[k] = v
        else:
            _merge(cast(JsonSchemaValue, v), properties[k], k)
    if not already_in and properties:
        json_schema["properties"] = properties


def try_move(key: str, src: JsonSchemaValue, dst: JsonSchemaValue) -> None:
    """
    Move a key (that may not exist) from one JSON Schema to another one.

    Removes the key `key` and its value from `src` and inserts them into `dst`. If `src` does not
    contain the key `key`, nothing happens.

    Parameters
    ----------
    key : str
        Key to move from `src` to `dst`
    src : JsonSchemaValue
        Source JSON Schema from which to move `key` and its value
    dst : JsonSchemaValue
        Destination JSON Schema into which to move `key` and its value
    """
    try:
        value = src[key]
        dst[key] = value
        del src[key]
    except KeyError:
        pass


T = TypeVar("T", JsonSchemaValue, str)


def _verify_json_schema_value(*candidates: tuple[str, JsonSchemaValue]) -> None:
    origin = cast(type, get_origin(JsonSchemaValue))
    for target in candidates:
        if not isinstance(target[1], origin):
            raise TypeError(
                f"`{target[0]}` must be a `JsonSchemaValue` value, but {repr(target[1])} has type `{type(target[1]).__name__}`"
            )


def _verify_operands_not_empty(tp: type[T], operands: list[T]) -> None:
    if not isinstance(operands, list):
        raise TypeError(
            f"`operands` must be a `list`, but {operands} has type `{type(operands).__name__}`"
        )
    if len(operands) == 0:
        raise ValueError("`operands` cannot be empty, but it is")
    origin = get_origin(tp)
    if origin:
        target = cast(type, origin)
    else:
        target = tp
    mismatches = [a for a in operands if not isinstance(a, target)]
    if mismatches:
        raise TypeError(
            "`operands` items must be `{target.__name__}` values, but these items are not: {mismatches}"
        )


def _merge(src: JsonSchemaValue, dst: JsonValue, *loc: str) -> None:
    origin = cast(type, get_origin(JsonSchemaValue))
    if not isinstance(dst, origin):
        raise TypeError(
            f"`put_properties` merge conflict: `dst` exists but `src` cannot be merged in because `dst` is not a `JsonSchemaValue` (full path: {repr(loc)}) (`dst` value {repr(dst)} has type `{type(dst).__name__}`)"
        )
    dst = cast(JsonSchemaValue, dst)
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
        elif isinstance(v, origin):
            _merge(cast(JsonSchemaValue, v), dst[k], *loc, k)
        elif dst[k] != v:
            raise ValueError(
                f"`put_properties` merge conflict: `dst[{repr(k)}]={repr(dst[k])}` exists and does not equal `src[{repr(k)}]={repr(v)}` (full path: {repr(loc)})"
            )
