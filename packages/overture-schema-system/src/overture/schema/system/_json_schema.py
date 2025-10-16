from collections.abc import Callable
from typing import Any, TypeVar, cast, get_origin

from pydantic import ConfigDict
from pydantic.json_schema import JsonSchemaValue, JsonValue


def get_static_json_schema(config: ConfigDict) -> JsonSchemaValue:
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
    _verify_json_schema_value(('json_schema', json_schema))
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
    _verify_json_schema_value(('json_schema', json_schema))
    _verify_operands_not_empty(JsonSchemaValue, operands)
    prev: JsonSchemaValue = {}
    try_move("anyOf", json_schema, prev)
    if not prev:
        json_schema["anyOf"] = cast(JsonValue, operands)
    else:
        put_all_of(json_schema, [prev, {"anyOf": cast(JsonValue, operands)}])


def put_one_of(json_schema: JsonSchemaValue, operands: list[JsonSchemaValue]) -> None:
    _verify_json_schema_value(('json_schema', json_schema))
    _verify_operands_not_empty(JsonSchemaValue, operands)
    prev: JsonSchemaValue = {}
    try_move("oneOf", json_schema, prev)
    if not prev:
        json_schema["oneOf"] = cast(JsonValue, operands)
    else:
        put_all_of(json_schema, [prev, {"oneOf": cast(JsonValue, operands)}])


def put_not(json_schema: JsonSchemaValue, operand: JsonSchemaValue) -> None:
    _verify_json_schema_value(('json_schema', json_schema), ('operand', operand))
    prev: JsonSchemaValue = {}
    try_move("not", json_schema, prev)

    # Simple case: if the JSON didn't already have a "not", we just add it.
    if not prev:
        json_schema["not"] = operand
        return

    not_schema = prev["not"]
    if not isinstance(not_schema, get_origin(JsonSchemaValue)):
        raise ValueError(
            f'expected value of "not" key to be a `JsonSchemaValue`, but it is a {type(not_schema).__name__} in the JSON Schema {json_schema}'
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
    _verify_json_schema_value(('json_schema', json_schema))
    if condition is not None:
        _verify_json_schema_value(('condition', condition))
    if when_true is not None:
        _verify_json_schema_value(('when_true', when_true))
    if when_false is not None:
        _verify_json_schema_value(('when_false', when_false))

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


def put_required(
        json_schema: JsonSchemaValue,
        operands: list[str]
) -> None:
    _verify_json_schema_value(('json_schema', json_schema))
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
    _verify_json_schema_value(('json_schema', json_schema), ('new_properties', new_properties))
    if "properties" in json_schema:
        properties = json_schema["properties"]
    else:
        properties = {}
        json_schema["properties"] = properties
    for k, v in new_properties.items():
        if k not in properties:
            properties[k] = v
        else:
            _merge(v, properties[k], k)


def try_move(key: str, src: JsonSchemaValue, dst: JsonSchemaValue) -> None:
    try:
        value = src[key]
        dst[key] = value
        del src[key]
    except KeyError:
        pass

T = TypeVar('T', JsonSchemaValue, str)

def _verify_json_schema_value(*candidates: tuple[str, JsonSchemaValue]) -> None:
    origin = get_origin(JsonSchemaValue)
    for target in candidates:
        if not isinstance(target[1], origin):
            raise TypeError(f"`{target[0]}` must be a `JsonSchemaValue` value, but {repr(target[1])} has type `{type(target[1]).__name__}`")

def _verify_operands_not_empty(tp: T, operands: list[T]) -> None:
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
    origin = get_origin(JsonSchemaValue)
    if not isinstance(dst, origin):
        raise ValueError(f"`put_properties` merge conflict: `dst[{repr(k)}]` exists but `src` cannot be merged in because `dst` is not a `JsonSchemaValue` (full path: {repr(loc)})")
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
        elif isinstance(v, origin):
            _merge(v, dst[k], *loc, k)
        elif dst[k] != v:
            ValueError(f"`put_properties` merge conflict: `dst[{repr(k)}]={repr(dst[k])}` exists and does not equal `src[{repr(k)}]={repr(v)}` (full path: {repr(loc)})")
