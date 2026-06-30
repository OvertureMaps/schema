from typing import cast

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.json_schema import JsonDict
from util import assert_subset

from overture.schema.system import create_model
from overture.schema.system.model_constraint import (
    FieldEqCondition,
    ModelConstraint,
    Not,
    RequireAnyTrueConstraint,
    require_any_true,
)


@pytest.mark.parametrize("conditions", [[], ()])
def test_error_not_enough_conditions(conditions: list[FieldEqCondition]) -> None:
    with pytest.raises(ValueError, match="`conditions` must contain at least one item"):
        require_any_true(*conditions)


@pytest.mark.parametrize("conditions", [["foo"], [FieldEqCondition("foo", True), 42]])
def test_error_invalid_condition_types(conditions: list[object]) -> None:
    with pytest.raises(TypeError, match="`conditions` must contain only `Condition`"):
        require_any_true(*cast(tuple[FieldEqCondition, ...], tuple(conditions)))


@pytest.mark.parametrize(
    "constraint,model_class",
    [
        (
            RequireAnyTrueConstraint(FieldEqCondition("foo", True)),
            create_model("case1", bar=(bool, ...)),
        ),
        (
            RequireAnyTrueConstraint(Not(FieldEqCondition("foo", True))),
            create_model("case2", bar=(bool, ...)),
        ),
        (
            RequireAnyTrueConstraint(FieldEqCondition("foo", True)),
            create_model(
                "case3",
                bar=(bool | None, ...),
                baz=(int | None, ...),
            ),
        ),
    ],
)
def test_error_invalid_model_class(
    constraint: RequireAnyTrueConstraint, model_class: type[BaseModel]
) -> None:
    with pytest.raises(TypeError):
        constraint.validate_class(model_class)

    with pytest.raises(TypeError):
        constraint.decorate(model_class)


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"foo": None, "bar": None}, {"foo": False, "bar": False}],
)
def test_error_no_true_value(kwargs: dict[str, bool | None]) -> None:
    @require_any_true(FieldEqCondition("foo", True), FieldEqCondition("bar", True))
    class TestModel(BaseModel):
        foo: bool | None = None
        bar: bool | None = None

    with pytest.raises(
        ValidationError,
        match=r"at least one field from the condition group \[foo, bar\] must be True, but none is True",
    ):
        TestModel(**kwargs)


@pytest.mark.parametrize(
    "foo,bar",
    [(True, True), (True, False), (False, True), (None, True), (True, None)],
)
def test_valid_model_instance(foo: bool | None, bar: bool | None) -> None:
    @require_any_true(FieldEqCondition("foo", True), FieldEqCondition("bar", True))
    class TestModel(BaseModel):
        foo: bool | None = None
        bar: bool | None = None

    TestModel(foo=foo, bar=bar)


def test_valid_model_instance_single_condition() -> None:
    @require_any_true(FieldEqCondition("foo", "bar"))
    class TestModel(BaseModel):
        foo: str | None = None

    TestModel(foo="bar")


@pytest.mark.parametrize("kwargs", [{}, {"foo": None}, {"foo": "baz"}])
def test_error_no_matching_generic_condition(kwargs: dict[str, str | None]) -> None:
    @require_any_true(FieldEqCondition("foo", "bar"))
    class TestModel(BaseModel):
        foo: str | None = None

    with pytest.raises(
        ValidationError,
        match=r"at least one condition from the condition group \[FieldEqCondition\(field_name='foo', value='bar'\)\] must be True, but none is True",
    ):
        TestModel(**kwargs)


def test_model_json_schema_no_model_config() -> None:
    @require_any_true(FieldEqCondition("foo", True), FieldEqCondition("bar", True))
    class TestModel(BaseModel):
        foo: bool | None = None
        bar: bool | None = Field(default=None, alias="baz")

    actual = TestModel.model_json_schema()
    expect = {
        "anyOf": [
            {"required": ["foo"], "properties": {"foo": {"const": True}}},
            {"required": ["baz"], "properties": {"baz": {"const": True}}},
        ]
    }
    assert expect == TestModel.model_config["json_schema_extra"]
    assert_subset(expect, actual, "expect", "actual")


@pytest.mark.parametrize(
    "base_json_schema,expect",
    [
        (
            None,
            {
                "anyOf": [
                    {"required": ["foo"], "properties": {"foo": {"const": True}}},
                    {"required": ["baz"], "properties": {"baz": {"const": True}}},
                ]
            },
        ),
        (
            {"random": "value"},
            {
                "random": "value",
                "anyOf": [
                    {"required": ["foo"], "properties": {"foo": {"const": True}}},
                    {"required": ["baz"], "properties": {"baz": {"const": True}}},
                ],
            },
        ),
        (
            {"anyOf": 123},
            {
                "allOf": [
                    {"anyOf": 123},
                    {
                        "anyOf": [
                            {
                                "required": ["foo"],
                                "properties": {"foo": {"const": True}},
                            },
                            {
                                "required": ["baz"],
                                "properties": {"baz": {"const": True}},
                            },
                        ]
                    },
                ]
            },
        ),
    ],
)
def test_model_json_schema_with_model_config(
    base_json_schema: JsonDict | None, expect: JsonDict
) -> None:
    @require_any_true(FieldEqCondition("foo", True), FieldEqCondition("bar", True))
    class TestModel(BaseModel):
        model_config = ConfigDict(json_schema_extra=base_json_schema)

        foo: bool | None = None
        bar: bool | None = Field(default=None, alias="baz")

    actual = TestModel.model_json_schema()
    assert_subset(expect, actual, "expect", "actual")


def test_model_json_schema_with_generic_condition() -> None:
    @require_any_true(
        FieldEqCondition("foo", "bar"), Not(FieldEqCondition("baz", "qux"))
    )
    class TestModel(BaseModel):
        foo: str | None = None
        baz: str | None = None

    actual = TestModel.model_json_schema()
    expect = {
        "anyOf": [
            {
                "required": ["foo"],
                "properties": {"foo": {"const": "bar"}},
            },
            {
                "not": {"properties": {"baz": {"const": "qux"}}},
            },
        ]
    }
    assert expect == TestModel.model_config["json_schema_extra"]
    assert_subset(expect, actual, "expect", "actual")


def test_model_constraints() -> None:
    constraint = RequireAnyTrueConstraint(
        FieldEqCondition("foo", True), FieldEqCondition("bar", True)
    )

    class TestModel(BaseModel):
        foo: bool | None = None
        bar: bool | None = None

    assert 0 == len(ModelConstraint.get_model_constraints(TestModel))

    new_model_class = constraint.decorate(TestModel)

    assert (constraint,) == ModelConstraint.get_model_constraints(new_model_class)
