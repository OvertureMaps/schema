import re
from typing import cast

import pytest
from pydantic import ConfigDict
from pydantic.json_schema import JsonSchemaValue

from overture.schema.system._json_schema import (
    get_static_json_schema,
    put_all_of,
    put_any_of,
    put_if,
    put_not,
    put_one_of,
    put_properties,
    put_required,
    try_move,
)

####################################################################################################
#                                     get_static_json_schema                                       #
####################################################################################################


@pytest.mark.parametrize(
    "config,expect",
    [
        (ConfigDict(), {}),
        (ConfigDict(json_schema_extra=None), {}),
        (ConfigDict(json_schema_extra={}), {}),
        (ConfigDict(json_schema_extra={"foo": "bar"}), {"foo": "bar"}),
    ],
)
def test_get_static_json_schema_success(
    config: ConfigDict, expect: JsonSchemaValue
) -> None:
    actual = get_static_json_schema(config)

    assert expect == actual
    assert actual is config["json_schema_extra"]


def test_get_static_json_schema_error_invalid_type() -> None:
    with pytest.raises(
        ValueError,
        match='expected value of config\'s "json_schema_extra" key to be a `dict`, but it is a `function`',
    ):
        get_static_json_schema(ConfigDict(json_schema_extra=lambda _: None))


####################################################################################################
#                                           put_all_of                                             #
####################################################################################################


@pytest.mark.parametrize(
    "json_schema,operands,expect",
    [
        ({}, [{}, {}], {"allOf": [{}, {}]}),
        (
            {"foo": "bar"},
            [{"baz": "qux"}, {"corge": True, "garply": False}],
            {"foo": "bar", "allOf": [{"baz": "qux"}, {"corge": True, "garply": False}]},
        ),
        (
            {"allOf": ["hello"]},
            [{"foo": "bar"}, {"baz": "qux"}],
            {"allOf": ["hello", {"foo": "bar"}, {"baz": "qux"}]},
        ),
    ],
)
def test_put_all_of_success(
    json_schema: JsonSchemaValue,
    operands: list[JsonSchemaValue],
    expect: JsonSchemaValue,
) -> None:
    put_all_of(json_schema, operands)

    assert expect == json_schema


def test_put_all_of_error_too_few_operands() -> None:
    with pytest.raises(ValueError, match="`operands` cannot be empty"):
        put_all_of({}, [])


@pytest.mark.parametrize(
    "operands", [cast(list[JsonSchemaValue], False), [{}, cast(JsonSchemaValue, False)]]
)
def test_put_all_of_error_bad_type(operands: list[JsonSchemaValue]) -> None:
    with pytest.raises(TypeError):
        put_all_of({}, operands)


def test_put_any_of_error_existing_all_of_not_list() -> None:
    with pytest.raises(
        ValueError, match='expected value of "allOf" key to be a `list`'
    ):
        put_all_of({"allOf": False}, [{}, {}])


####################################################################################################
#                                           put_any_of                                             #
####################################################################################################


@pytest.mark.parametrize(
    "json_schema,operands,expect",
    [
        ({}, [{}, {}], {"anyOf": [{}, {}]}),
        (
            {"foo": 1},
            [{"bar": 2}, {"baz": 3}],
            {"foo": 1, "anyOf": [{"bar": 2}, {"baz": 3}]},
        ),
        (
            {"anyOf": "foo"},
            [{}, {}],
            {"allOf": [{"anyOf": "foo"}, {"anyOf": [{}, {}]}]},
        ),
        (
            {"anyOf": "foo", "bar": [1, 2]},
            [{"baz": 3}, {"qux": 4}],
            {
                "allOf": [{"anyOf": "foo"}, {"anyOf": [{"baz": 3}, {"qux": 4}]}],
                "bar": [1, 2],
            },
        ),
    ],
)
def test_put_any_of_success(
    json_schema: JsonSchemaValue,
    operands: list[JsonSchemaValue],
    expect: JsonSchemaValue,
) -> None:
    put_any_of(json_schema, operands)

    assert expect == json_schema


def test_put_any_of_error_too_few_operands() -> None:
    with pytest.raises(ValueError, match="`operands` cannot be empty"):
        put_any_of({}, [])


@pytest.mark.parametrize(
    "operands", [cast(list[JsonSchemaValue], False), [{}, cast(JsonSchemaValue, False)]]
)
def test_put_any_of_error_bad_type(operands: list[JsonSchemaValue]) -> None:
    with pytest.raises(TypeError):
        put_any_of({}, operands)


####################################################################################################
#                                           put_one_of                                             #
####################################################################################################


@pytest.mark.parametrize(
    "json_schema,operands,expect",
    [
        ({}, [{}, {}], {"oneOf": [{}, {}]}),
        (
            {"foo": 1},
            [{"bar": 2}, {"baz": 3}],
            {"foo": 1, "oneOf": [{"bar": 2}, {"baz": 3}]},
        ),
        (
            {"oneOf": "foo"},
            [{}, {}],
            {"allOf": [{"oneOf": "foo"}, {"oneOf": [{}, {}]}]},
        ),
        (
            {"oneOf": "foo", "bar": [1, 2]},
            [{"baz": 3}, {"qux": 4}],
            {
                "allOf": [{"oneOf": "foo"}, {"oneOf": [{"baz": 3}, {"qux": 4}]}],
                "bar": [1, 2],
            },
        ),
    ],
)
def test_put_one_of_success(
    json_schema: JsonSchemaValue,
    operands: list[JsonSchemaValue],
    expect: JsonSchemaValue,
) -> None:
    put_one_of(json_schema, operands)

    assert expect == json_schema


def test_put_one_of_error_too_few_operands() -> None:
    with pytest.raises(ValueError, match="`operands` cannot be empty"):
        put_one_of({}, [])


@pytest.mark.parametrize(
    "operands", [cast(list[JsonSchemaValue], False), [{}, cast(JsonSchemaValue, False)]]
)
def test_put_one_of_error_bad_type(operands: list[JsonSchemaValue]) -> None:
    with pytest.raises(TypeError):
        put_one_of({}, operands)


####################################################################################################
#                                             put_not                                              #
####################################################################################################


@pytest.mark.parametrize(
    "json_schema,operand,expect",
    [
        ({}, {}, {"not": {}}),
        ({"foo": "bar"}, {"baz": "qux"}, {"foo": "bar", "not": {"baz": "qux"}}),
        ({"not": {"anyOf": []}}, {}, {"not": {"anyOf": [{}]}}),
        (
            {"not": {"anyOf": [1, 2]}},
            {"foo": "bar"},
            {"not": {"anyOf": [1, 2, {"foo": "bar"}]}},
        ),
        ({"not": {}}, {}, {"not": {"anyOf": [{}, {}]}}),
        (
            {"not": {"foo": "bar"}},
            {"baz": "qux"},
            {"not": {"anyOf": [{"foo": "bar"}, {"baz": "qux"}]}},
        ),
        (
            {"not": {"foo": "bar", "anyOf": []}},
            {"baz": "qux"},
            {"not": {"anyOf": [{"foo": "bar", "anyOf": []}, {"baz": "qux"}]}},
        ),
    ],
)
def test_put_not_success(
    json_schema: JsonSchemaValue, operand: JsonSchemaValue, expect: JsonSchemaValue
) -> None:
    put_not(json_schema, operand)

    assert expect == json_schema


def test_put_not_error_invalid_operand() -> None:
    with pytest.raises(
        TypeError,
        match="`operand` must be a `JsonSchemaValue` value, but 123 has type `int`",
    ):
        put_not({}, cast(JsonSchemaValue, 123))


def test_put_not_error_invalid_not_value() -> None:
    with pytest.raises(
        TypeError, match='expected value of "not" key to be a `JsonSchemaValue`'
    ):
        put_not({"not": []}, {})


def test_put_not_error_invalid_not_any_of_value() -> None:
    with pytest.raises(
        ValueError, match='expected value of "anyOf" key under "not" to be a `list`'
    ):
        put_not({"not": {"anyOf": {}}}, {})


####################################################################################################
#                                             put_if                                               #
####################################################################################################


@pytest.mark.parametrize(
    "json_schema,condition,when_true,when_false,expect",
    [
        ({}, {"foo": 1}, {"bar": 2}, None, {"if": {"foo": 1}, "then": {"bar": 2}}),
        (
            {},
            {"foo": 1},
            {"bar": 2},
            {"baz": 3},
            {"if": {"foo": 1}, "then": {"bar": 2}, "else": {"baz": 3}},
        ),
        (
            {"if": 0},
            {"foo": 1},
            {"bar": 2},
            {"baz": 3},
            {
                "allOf": [
                    {"if": 0},
                    {"if": {"foo": 1}, "then": {"bar": 2}, "else": {"baz": 3}},
                ]
            },
        ),
        (
            {"then": 0},
            {"foo": 1},
            {"bar": 2},
            {"baz": 3},
            {
                "allOf": [
                    {"then": 0},
                    {"if": {"foo": 1}, "then": {"bar": 2}, "else": {"baz": 3}},
                ]
            },
        ),
        (
            {"else": 0},
            {"foo": 1},
            {"bar": 2},
            {"baz": 3},
            {
                "allOf": [
                    {"else": 0},
                    {"if": {"foo": 1}, "then": {"bar": 2}, "else": {"baz": 3}},
                ]
            },
        ),
        (
            {"if": 0, "then": -1},
            {"foo": 1},
            {"bar": 2},
            {"baz": 3},
            {
                "allOf": [
                    {"if": 0, "then": -1},
                    {"if": {"foo": 1}, "then": {"bar": 2}, "else": {"baz": 3}},
                ]
            },
        ),
        (
            {"if": 0, "then": -1, "else": -2},
            {"foo": 1},
            {"bar": 2},
            {"baz": 3},
            {
                "allOf": [
                    {"if": 0, "then": -1, "else": -2},
                    {"if": {"foo": 1}, "then": {"bar": 2}, "else": {"baz": 3}},
                ]
            },
        ),
    ],
)
def test_put_if_success(
    json_schema: JsonSchemaValue,
    condition: JsonSchemaValue,
    when_true: JsonSchemaValue,
    when_false: JsonSchemaValue,
    expect: JsonSchemaValue,
) -> None:
    put_if(json_schema, condition, when_true, when_false)

    assert expect == json_schema


####################################################################################################
#                                          put_required                                            #
####################################################################################################


def test_put_required_error_invalid_json_schema() -> None:
    with pytest.raises(
        TypeError,
        match="`json_schema` must be a `JsonSchemaValue` value, but True has type `bool`",
    ):
        put_required(cast(JsonSchemaValue, True), ["foo"])


@pytest.mark.parametrize(
    "operands,expect_error_type",
    [
        (42, TypeError),
        ([42], TypeError),
        ([], ValueError),
    ],
)
def test_put_required_error_invalid_operands(
    operands: object, expect_error_type: type[Exception]
) -> None:
    with pytest.raises(expect_error_type):
        put_required({}, cast(list[str], operands))


@pytest.mark.parametrize(
    "json_schema,operands,expect",
    [
        ({}, ["foo"], {"required": ["foo"]}),
        ({}, ["foo", "bar"], {"required": ["foo", "bar"]}),
        ({"required": []}, ["foo"], {"required": ["foo"]}),
        ({"required": []}, ["bar", "foo"], {"required": ["bar", "foo"]}),
        ({"required": ["baz"]}, ["foo"], {"required": ["baz", "foo"]}),
        (
            {"required": ["baz"]},
            ["foo", "baz", "bar", "qux"],
            {"required": ["baz", "foo", "bar", "qux"]},
        ),
        (
            {"required": ["qux", "corge"]},
            ["baz", "bar", "qux"],
            {"required": ["qux", "corge", "baz", "bar"]},
        ),
    ],
)
def test_put_required_success(
    json_schema: JsonSchemaValue, operands: list[str], expect: JsonSchemaValue
) -> None:
    put_required(json_schema, operands)

    assert expect == json_schema


####################################################################################################
#                                         put_properties                                           #
####################################################################################################


def test_put_properties_error_invalid_json_schema_type() -> None:
    with pytest.raises(
        TypeError,
        match="`json_schema` must be a `JsonSchemaValue` value, but 42 has type `int`",
    ):
        put_properties(cast(JsonSchemaValue, 42), {})


def test_put_properties_error_invalid_new_properties_type() -> None:
    with pytest.raises(
        TypeError,
        match="`new_properties` must be a `JsonSchemaValue` value, but 'foo' has type `str`",
    ):
        put_properties({}, cast(JsonSchemaValue, "foo"))


def test_put_properties_error_invalid_existing_properties_type() -> None:
    with pytest.raises(
        TypeError,
        match='expected value of "properties" key to be a `JsonSchemaValue`, but 42 has type `int`',
    ):
        put_properties({"properties": 42}, {})


def test_put_properties_error_invalid_new_property_value_type() -> None:
    with pytest.raises(
        TypeError,
        match="expected property value for 'foo' key to be a `JsonSchemaValue`, but 'bar' has type `str`",
    ):
        put_properties({}, {"foo": "bar"})


@pytest.mark.parametrize(
    "json_schema,new_properties",
    [
        (
            {"properties": {"foo": "bar"}},
            {"foo": {"type": "integer"}},
        ),
        (
            {
                "properties": {
                    "foo": {
                        "bar": "baz",
                    }
                }
            },
            {
                "foo": {
                    "bar": {"type": "integer"},
                }
            },
        ),
    ],
)
def test_put_properties_error_merge_conflict_dst_type(
    json_schema: JsonSchemaValue, new_properties: JsonSchemaValue
) -> None:
    with pytest.raises(
        TypeError,
        match="put_properties` merge conflict: `dst` exists but `src` cannot be merged in because `dst` is not a `JsonSchemaValue`",
    ):
        put_properties(json_schema, new_properties)


def test_put_properties_error_merge_conflict_dst_value() -> None:
    with pytest.raises(
        ValueError,
        match=re.escape(
            "`put_properties` merge conflict: `dst['type']='bar'` exists and does not equal `src['type']='baz'`"
        ),
    ):
        put_properties(
            {
                "properties": {
                    "foo": {
                        "type": "bar",
                    }
                }
            },
            {
                "foo": {
                    "type": "baz",
                },
            },
        )


@pytest.mark.parametrize(
    "json_schema,new_properties,expect",
    [
        ({}, {}, {}),
        ({}, {"foo": {}}, {"properties": {"foo": {}}}),
        ({"properties": {"foo": {}}}, {"foo": {}}, {"properties": {"foo": {}}}),
        (
            {"properties": {"foo": {}}},
            {"bar": {"baz": "qux"}},
            {"properties": {"foo": {}, "bar": {"baz": "qux"}}},
        ),
        (
            {"properties": {"foo": {"bar": "baz"}}},
            {"foo": {"qux": "corge"}},
            {"properties": {"foo": {"bar": "baz", "qux": "corge"}}},
        ),
        (
            {"properties": {"foo": {"bar": "baz", "qux": {"corge": "garply"}}}},
            {"foo": {"qux": {"hello": [42]}}},
            {
                "properties": {
                    "foo": {"bar": "baz", "qux": {"corge": "garply", "hello": [42]}}
                }
            },
        ),
    ],
)
def test_put_properties_success(
    json_schema: JsonSchemaValue,
    new_properties: JsonSchemaValue,
    expect: JsonSchemaValue,
) -> None:
    put_properties(json_schema, new_properties)

    assert expect == json_schema


####################################################################################################
#                                            try_move                                              #
####################################################################################################


def test_try_move_existing_key() -> None:
    src = {"foo": "bar"}
    dst: JsonSchemaValue = {}

    try_move("foo", src, dst)

    assert {} == src
    assert {"foo": "bar"} == dst


def test_try_move_missing_key() -> None:
    src = {"foo": "bar"}
    dst: JsonSchemaValue = {}

    try_move("baz", src, dst)

    assert {"foo": "bar"} == src
    assert {} == dst
