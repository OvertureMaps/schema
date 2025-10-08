from typing import get_origin

from pydantic import ConfigDict
from pydantic.json_schema import JsonDict


def get_static_json_schema(config: ConfigDict) -> JsonDict:
    json_schema: JsonDict | None = config.get("json_schema_extra", None)
    if json_schema is None:
        json_schema = {}
        config["json_schema_extra"] = {}
    else:
        origin = get_origin(JsonDict)
        if isinstance(json_schema, origin):
            return json_schema
        else:
            raise TypeError(
                'expected value of "json_schema_extra" key to be a `{origin.__name__}`, but it is a `{type(json_schema).__name__}`'
            )
    return json_schema


def put_all_of(json_schema: JsonDict, *args: JsonDict):
    _verify_tuple_len_2(args)
    if "allOf" not in json_schema:
        json_schema["allOf"] = args
    else:
        maybe_list = json_schema["allOf"]
        if isinstance(maybe_list, list):
            maybe_list += args
        else:
            raise TypeError(
                f'expected value of "anyOf" key to be a `list`, but it is a `{type(maybe_list).__name__}` in the JSON Schema {json_schema}'
            )


def put_any_of(json_schema: JsonDict, *args: JsonDict):
    _verify_tuple_len_2(args)
    prev: JsonDict = {}
    _try_move("anyOf", json_schema, prev)
    if not prev:
        json_schema["anyOf"] = args
    else:
        put_all_of(json_schema, prev, {"anyOf": args})


def put_one_of(json_schema: JsonDict, *args: JsonDict):
    _verify_tuple_len_2(args)
    prev: JsonDict = {}
    _try_move("oneOf", json_schema, prev)
    if not prev:
        json_schema["oneOf"] = args
    else:
        put_all_of(json_schema, prev, {"oneOf": args})


def put_if(
    json_schema: JsonDict,
    condition: JsonDict,
    when_true: JsonDict,
    when_false: JsonDict | None,
):
    prev: JsonDict = {}
    _try_move("if", json_schema, prev)
    _try_move("then", json_schema, prev)
    _try_move("else", json_schema, prev)

    def _put(dst: JsonDict) -> JsonDict:
        dst["if"] = condition
        dst["then"] = when_true
        dst["else"] = when_false
        return dst

    if not prev:
        _put(json_schema)
    else:
        put_all_of(json_schema, prev, _put({}))


def _verify_tuple_len_2(args: tuple[JsonDict]):
    if not isinstance(args, tuple):
        raise TypeError(
            f"`args` must be a `tuple`, but {args} is a {type(args).__name__}"
        )
    if len(args) < 2:
        raise ValueError(
            f"`args` must have length at least 2, but {args} only has length {len(args)}"
        )
    origin = get_origin(JsonDict)
    mismatches = [a for a in args if not isinstance(a, origin)]
    if mismatches:
        raise TypeError(
            "`args` items must be `JsonDict` values, but these items are not: {mismatches}"
        )


def _try_move(key: str, src: JsonDict, dst: JsonDict):
    try:
        value = src[key]
        dst[key] = value
        del src[key]
    except KeyError:
        pass
