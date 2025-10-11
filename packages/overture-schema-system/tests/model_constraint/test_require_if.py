import sys
from pathlib import Path
from typing import cast

import pytest
from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import JsonDict

from overture.schema.system import create_model
from overture.schema.system.model_constraint import (
    Condition,
    FieldEqCondition,
    ModelConstraint,
    RequireIfConstraint,
    require_if,
)

sys.path.insert(0, str(Path(__file__).parent))  # Needed to import `util` peer module.

from util import assert_subset


@pytest.mark.parametrize("field_names", [[], ()])
def test_error_not_enough_field_names(field_names: list[str]):
    with pytest.raises(ValueError, match="`field_names` cannot be empty, but it is"):
        require_if(field_names, FieldEqCondition("foo", 42))


def test_error_invalid_condition() -> None:
    with pytest.raises(
        TypeError, match="`condition` must be a `Condition`, but 42 has type `int`"
    ):
        RequireIfConstraint(["foo"], cast(Condition, 42))


@pytest.mark.parametrize(
    "constraint,model_class",
    [
        (
            RequireIfConstraint(["foo"], FieldEqCondition("bar", 42)),
            create_model("case1", foo=(int, ...), bar=(int, ...)),
        ),
        (
            RequireIfConstraint(["bar"], FieldEqCondition("foo", 42)),
            create_model("case2", foo=(int | None, None)),
        ),
        (
            RequireIfConstraint(["bar"], FieldEqCondition("foo", 42)),
            create_model("case3", bar=(int | None, None)),
        ),
    ],
)
def test_error_invalid_model_class(
    constraint: RequireIfConstraint, model_class: type[BaseModel]
) -> None:
    with pytest.raises(TypeError):
        constraint.validate_class(model_class)

    with pytest.raises(TypeError):
        constraint.decorate(model_class)


@pytest.mark.parametrize(
    "constraint",
    [
        (RequireIfConstraint(["foo"], FieldEqCondition("qux", 42))),
        (RequireIfConstraint(["bar"], FieldEqCondition("qux", 42))),
        (RequireIfConstraint(["foo", "bar"], FieldEqCondition("qux", 42))),
        (RequireIfConstraint(["foo", "baz"], FieldEqCondition("qux", 42))),
        (RequireIfConstraint(["bar", "baz"], FieldEqCondition("qux", 42))),
        (RequireIfConstraint(["foo", "bar", "baz"], FieldEqCondition("qux", 42))),
    ],
)
def test_error_invalid_model_instance(constraint: RequireIfConstraint) -> None:
    class TestModel(BaseModel):
        foo: int | None = None
        bar: int | None = None
        baz: int | None = None
        qux: int

    model_instance = TestModel(baz=41, qux=42)

    constraint.validate_class(TestModel)
    with pytest.raises(
        ValueError,
        match="at least one field is missing an explicit value when it should have one:",
    ):
        constraint.validate_instance(model_instance)


def test_create_success() -> None:
    condition = FieldEqCondition("foo", 42)
    constraint = RequireIfConstraint(["bar"], condition)
    assert constraint.field_names == ("bar",)
    assert constraint.condition is condition

    not_condition = ~FieldEqCondition("foo", 42)
    not_constraint = RequireIfConstraint(("baz", "qux"), not_condition)
    assert not_constraint.field_names == ("baz", "qux")
    assert not_constraint.condition is not_condition


@pytest.mark.parametrize("field_names", [["foo"], ["bar"], ["foo", "bar"]])
def test_valid_model_instance_condition_true(field_names: list[str]) -> None:
    class TestModel(BaseModel):
        foo: int | None = None
        bar: int | None = None
        baz: int

    constraint = RequireIfConstraint(field_names, FieldEqCondition("baz", 42))
    constraint.validate_instance(TestModel(foo=40, bar=41, baz=42))


@pytest.mark.parametrize("field_names", [["foo"], ["bar"], ["foo", "bar"]])
def test_valid_model_instance_condition_false(field_names) -> None:
    class TestModel(BaseModel):
        foo: int | None = None
        bar: int | None = None
        baz: int

    constraint = RequireIfConstraint(field_names, ~FieldEqCondition("baz", 42))
    constraint.validate_instance(TestModel(bar=41, baz=42))


def test_model_json_schema_no_model_config() -> None:
    @require_if(["foo", "baz"], FieldEqCondition("qux", 42))
    class TestModel(BaseModel):
        foo: int | None = Field(default=None, alias="bar")
        baz: str | None = None
        qux: int = Field(alias="corge")

    actual = TestModel.model_json_schema()
    expect = {
        "if": {"properties": {"corge": {"const": 42}}},
        "then": {"required": ["bar", "baz"]},
    }
    assert expect == TestModel.model_config["json_schema_extra"]
    assert_subset(expect, actual, "expect", "actual")


@pytest.mark.parametrize(
    "base_json_schema,expect",
    [
        (
            None,
            {
                "if": {"not": {"properties": {"qux": {"const": 42}}}},
                "then": {"required": ["foo", "baz"]},
            },
        ),
        (
            {"random": "value"},
            {
                "random": "value",
                "if": {"not": {"properties": {"qux": {"const": 42}}}},
                "then": {"required": ["foo", "baz"]},
            },
        ),
        (
            {"if": 123},
            {
                "allOf": [
                    {"if": 123},
                    {
                        "if": {"not": {"properties": {"qux": {"const": 42}}}},
                        "then": {"required": ["foo", "baz"]},
                    },
                ]
            },
        ),
    ],
)
def test_model_json_schema_with_model_config(
    base_json_schema: JsonDict | None, expect: JsonDict
) -> None:
    @require_if(["foo", "bar"], ~FieldEqCondition("qux", 42))
    class TestModel(BaseModel):
        model_config = ConfigDict(json_schema_extra=base_json_schema)

        foo: int | None = None
        bar: str | None = Field(default=None, alias="baz")
        qux: int

    actual = TestModel.model_json_schema()
    assert_subset(expect, actual, "expect", "actual")


def test_model_constraints() -> None:
    constraint = RequireIfConstraint(["foo"], FieldEqCondition("bar", "baz"))

    class TestModel(BaseModel):
        foo: int | None = None
        bar: str

    assert 0 == len(ModelConstraint.get_model_constraints(TestModel))

    new_model_class = constraint.decorate(TestModel)

    assert (constraint,) == ModelConstraint.get_model_constraints(new_model_class)
