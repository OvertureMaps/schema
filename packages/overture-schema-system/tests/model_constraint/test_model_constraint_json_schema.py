from typing import cast

import pytest
from pydantic import ConfigDict
from pydantic.json_schema import JsonDict

from overture.schema.system.model_constraint.json_schema import (
    get_static_json_schema,
    put_all_of,
    put_any_of,
    put_if,
    put_not,
    put_one_of,
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
def test_get_static_json_schema_success(config: ConfigDict, expect: JsonDict) -> None:
    actual = get_static_json_schema(config)

    assert expect == actual
    assert actual is config["json_schema_extra"]


def test_get_static_json_schema_error_invalid_type() -> None:
    with pytest.raises(
        ValueError,
        match='expected value of config\'s "json_schema_extra" key to be a `dict`, but it is a `function`',
    ):
        get_static_json_schema(ConfigDict(json_schema_extra=lambda _: {}))


####################################################################################################
#                                         test_put_all_of                                          #
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
    json_schema: JsonDict, operands: list[JsonDict], expect: JsonDict
) -> None:
    put_all_of(json_schema, operands)

    assert expect == json_schema


@pytest.mark.parametrize("operands", [[], [{}]])
def test_put_all_of_error_too_few_operands(operands: list[JsonDict]) -> None:
    with pytest.raises(ValueError, match="`operands` must have length at least 2"):
        put_all_of({}, operands)


@pytest.mark.parametrize(
    "operands", [cast(list[JsonDict], False), [{}, cast(JsonDict, False)]]
)
def test_put_all_of_error_bad_type(operands: list[JsonDict]) -> None:
    with pytest.raises(TypeError):
        put_all_of({}, operands)


def test_put_any_of_error_existing_all_of_not_list():
    with pytest.raises(
        ValueError, match='expected value of "allOf" key to be a `list`'
    ):
        put_all_of({"allOf": False}, [{}, {}])


####################################################################################################
#                                         test_put_any_of                                          #
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
    json_schema: JsonDict, operands: list[JsonDict], expect: JsonDict
) -> None:
    put_any_of(json_schema, operands)

    assert expect == json_schema


@pytest.mark.parametrize("operands", [[], [{}]])
def test_put_any_of_error_too_few_operands(operands: list[JsonDict]) -> None:
    with pytest.raises(ValueError, match="`operands` must have length at least 2"):
        put_any_of({}, operands)


@pytest.mark.parametrize(
    "operands", [cast(list[JsonDict], False), [{}, cast(JsonDict, False)]]
)
def test_put_any_of_error_bad_type(operands: list[JsonDict]) -> None:
    with pytest.raises(TypeError):
        put_any_of({}, operands)


####################################################################################################
#                                         test_put_one_of                                          #
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
    json_schema: JsonDict, operands: list[JsonDict], expect: JsonDict
) -> None:
    put_one_of(json_schema, operands)

    assert expect == json_schema


@pytest.mark.parametrize("operands", [[], [{}]])
def test_put_one_of_error_too_few_operands(operands: list[JsonDict]) -> None:
    with pytest.raises(ValueError, match="`operands` must have length at least 2"):
        put_one_of({}, operands)


@pytest.mark.parametrize(
    "operands", [cast(list[JsonDict], False), [{}, cast(JsonDict, False)]]
)
def test_put_one_of_error_bad_type(operands: list[JsonDict]) -> None:
    with pytest.raises(TypeError):
        put_one_of({}, operands)


####################################################################################################
#                                           test_put_not                                           #
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
    json_schema: JsonDict, operand: JsonDict, expect: JsonDict
) -> None:
    put_not(json_schema, operand)

    assert expect == json_schema


def test_put_not_error_invalid_operand() -> None:
    with pytest.raises(
        TypeError, match="`operand` must be a `JsonDict` value, but it is not"
    ):
        put_not({}, cast(JsonDict, 123))


def test_put_not_error_invalid_not_value() -> None:
    with pytest.raises(
        ValueError, match='expected value of "not" key to be a `JsonDict`'
    ):
        put_not({"not": []}, {})


def test_put_not_error_invalid_not_any_of_value() -> None:
    with pytest.raises(
        ValueError, match='expected value of "anyOf" key under "not" to be a `list`'
    ):
        put_not({"not": {"anyOf": {}}}, {})


####################################################################################################
#                                           test_put_if                                            #
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
    json_schema: JsonDict,
    condition: JsonDict,
    when_true: JsonDict,
    when_false: JsonDict,
    expect: JsonDict,
) -> None:
    put_if(json_schema, condition, when_true, when_false)

    assert expect == json_schema
