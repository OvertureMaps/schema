from typing import cast

import pytest
from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import JsonDict
from util import assert_subset

from overture.schema.system import create_model
from overture.schema.system.model_constraint import (
    Condition,
    FieldEqCondition,
    ForbidIfConstraint,
    ModelConstraint,
    forbid_if,
)


@pytest.mark.parametrize("field_names", [[], ()])
def test_error_not_enough_field_names(field_names: list[str]):
    with pytest.raises(ValueError, match="`field_names` cannot be empty, but it is"):
        forbid_if(field_names, FieldEqCondition("foo", 42))


def test_error_invalid_condition() -> None:
    with pytest.raises(
        TypeError, match="`condition` must be a `Condition`, but 42 has type `int`"
    ):
        ForbidIfConstraint(["foo"], cast(Condition, 42))


@pytest.mark.parametrize(
    "constraint,model_class",
    [
        (
            ForbidIfConstraint(["foo"], FieldEqCondition("bar", 42)),
            create_model("case1", foo=(int, ...), bar=(int, ...)),
        ),
        (
            ForbidIfConstraint(["bar"], FieldEqCondition("foo", 42)),
            create_model("case2", foo=(int | None, None)),
        ),
        (
            ForbidIfConstraint(["bar"], FieldEqCondition("foo", 42)),
            create_model("case3", bar=(int | None, None)),
        ),
    ],
)
def test_error_invalid_model_class(
    constraint: ForbidIfConstraint, model_class: type[BaseModel]
) -> None:
    with pytest.raises(TypeError):
        constraint.validate_class(model_class)

    with pytest.raises(TypeError):
        constraint.decorate(model_class)


@pytest.mark.parametrize(
    "constraint",
    [
        (ForbidIfConstraint(["foo"], FieldEqCondition("qux", 42))),
        (ForbidIfConstraint(["bar"], FieldEqCondition("qux", 42))),
        (ForbidIfConstraint(["foo", "bar"], FieldEqCondition("qux", 42))),
        (ForbidIfConstraint(["foo", "baz"], FieldEqCondition("qux", 42))),
        (ForbidIfConstraint(["bar", "baz"], FieldEqCondition("qux", 42))),
        (ForbidIfConstraint(["foo", "bar", "baz"], FieldEqCondition("qux", 42))),
    ],
)
def test_error_invalid_model_instance(constraint: ForbidIfConstraint) -> None:
    class TestModel(BaseModel):
        foo: int | None = None
        bar: int | None = None
        baz: int | None = None
        qux: int

    model_instance = TestModel(foo=40, bar=41, qux=42)

    constraint.validate_class(TestModel)
    with pytest.raises(
        ValueError, match="at least one field has an explicit value when it should not"
    ):
        constraint.validate_instance(model_instance)


def test_create_success() -> None:
    condition = FieldEqCondition("foo", 42)
    constraint = ForbidIfConstraint(("bar",), condition)
    assert constraint.field_names == ("bar",)
    assert constraint.condition is condition

    not_condition = ~FieldEqCondition("foo", 42)
    not_constraint = ForbidIfConstraint(["baz", "qux"], not_condition)
    assert not_constraint.field_names == ("baz", "qux")
    assert not_constraint.condition is not_condition


@pytest.mark.parametrize("field_names", [["foo"], ["bar"], ["foo", "bar"]])
def test_valid_model_instance_condition_true(field_names: list[str]) -> None:
    class TestModel(BaseModel):
        foo: int | None = None
        bar: int | None = None
        baz: int

    constraint = ForbidIfConstraint(field_names, FieldEqCondition("baz", 42))
    constraint.validate_instance(TestModel(baz=42))


@pytest.mark.parametrize("field_names", [["foo"], ["bar"], ["foo", "bar"]])
def test_valid_model_instance_condition_false(field_names: list[str]) -> None:
    class TestModel(BaseModel):
        foo: int | None = None
        bar: int | None = None
        baz: int | None = None

    constraint = ForbidIfConstraint(field_names, FieldEqCondition("baz", 42))
    constraint.validate_instance(TestModel(foo=42))


def test_model_json_schema_no_model_config() -> None:
    @forbid_if(["foo", "bar"], FieldEqCondition("qux", 42))
    class TestModel(BaseModel):
        foo: int | None = None
        bar: str | None = Field(default=None, alias="baz")
        qux: int

    actual = TestModel.model_json_schema()
    expect = {
        "if": {"properties": {"qux": {"const": 42}}},
        "then": {"not": {"required": ["foo", "baz"]}},
    }
    assert expect == TestModel.model_config["json_schema_extra"]
    assert_subset(expect, actual, "expect", "actual")


@pytest.mark.parametrize(
    "base_json_schema,expect",
    [
        (
            None,
            {
                "if": {"not": {"properties": {"corge": {"const": 42}}}},
                "then": {"not": {"required": ["bar", "baz"]}},
            },
        ),
        (
            {"random": "value"},
            {
                "random": "value",
                "if": {"not": {"properties": {"corge": {"const": 42}}}},
                "then": {"not": {"required": ["bar", "baz"]}},
            },
        ),
        (
            {"if": 123},
            {
                "allOf": [
                    {"if": 123},
                    {
                        "if": {"not": {"properties": {"corge": {"const": 42}}}},
                        "then": {"not": {"required": ["bar", "baz"]}},
                    },
                ]
            },
        ),
    ],
)
def test_model_json_schema_with_model_config(
    base_json_schema: JsonDict | None, expect: JsonDict
) -> None:
    @forbid_if(["foo", "baz"], ~FieldEqCondition("qux", 42))
    class TestModel(BaseModel):
        model_config = ConfigDict(json_schema_extra=base_json_schema)

        foo: int | None = Field(default=None, alias="bar")
        baz: str | None = None
        qux: int = Field(alias="corge")

    actual = TestModel.model_json_schema()
    assert_subset(expect, actual, "expect", "actual")


def test_model_constraints() -> None:
    constraint = ForbidIfConstraint(["foo"], FieldEqCondition("bar", "baz"))

    class TestModel(BaseModel):
        foo: int | None = None
        bar: str

    assert 0 == len(ModelConstraint.get_model_constraints(TestModel))

    new_model_class = constraint.decorate(TestModel)

    assert (constraint,) == ModelConstraint.get_model_constraints(new_model_class)
