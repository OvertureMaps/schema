from typing import Annotated, Union

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.json_schema import JsonDict
from util import assert_subset

from overture.schema.system import create_model
from overture.schema.system.model_constraint import (
    ModelConstraint,
    RequireAnyTrueConstraint,
    require_any_true,
)


@pytest.mark.parametrize("field_names", [[], (), ["foo"], ("bar",)])
def test_error_not_enough_field_names(field_names: list[str]) -> None:
    with pytest.raises(
        ValueError, match="`field_names` must contain at least two items"
    ):
        require_any_true(*field_names)


@pytest.mark.parametrize("field_names", [["foo", "foo"], ["bar", "foo", "bar"]])
def test_error_duplicate_field_names(field_names: list[str]) -> None:
    with pytest.raises(ValueError, match="`field_names` must not contain duplicates"):
        require_any_true(*field_names)


@pytest.mark.parametrize(
    "constraint,model_class",
    [
        (
            RequireAnyTrueConstraint("foo", "bar"),
            create_model("case1", foo=(bool, ...), bar=(int, ...)),
        ),
        (
            RequireAnyTrueConstraint("bar", "baz"),
            create_model(
                "case2",
                bar=(bool | None, ...),
                baz=(Union[bool, int, None], ...),  # noqa: UP007
            ),
        ),
        (
            RequireAnyTrueConstraint("foo", "bar", "baz"),
            create_model(
                "case3",
                foo=(bool | None, ...),
                bar=(Annotated[bool, "x"], ...),
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
    @require_any_true("foo", "bar")
    class TestModel(BaseModel):
        foo: bool | None = None
        bar: bool | None = None

    with pytest.raises(
        ValidationError,
        match=r"at least one field from the `bool` field group \[foo, bar\] must be True, but none is True",
    ):
        TestModel(**kwargs)


@pytest.mark.parametrize(
    "foo,bar",
    [(True, True), (True, False), (False, True), (None, True), (True, None)],
)
def test_valid_model_instance(foo: bool | None, bar: bool | None) -> None:
    @require_any_true("foo", "bar")
    class TestModel(BaseModel):
        foo: bool | None = None
        bar: bool | None = None

    TestModel(foo=foo, bar=bar)


def test_model_json_schema_no_model_config() -> None:
    @require_any_true("foo", "bar")
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
    @require_any_true("foo", "bar")
    class TestModel(BaseModel):
        model_config = ConfigDict(json_schema_extra=base_json_schema)

        foo: bool | None = None
        bar: bool | None = Field(default=None, alias="baz")

    actual = TestModel.model_json_schema()
    assert_subset(expect, actual, "expect", "actual")


def test_model_constraints() -> None:
    constraint = RequireAnyTrueConstraint("foo", "bar")

    class TestModel(BaseModel):
        foo: bool | None = None
        bar: bool | None = None

    assert 0 == len(ModelConstraint.get_model_constraints(TestModel))

    new_model_class = constraint.decorate(TestModel)

    assert (constraint,) == ModelConstraint.get_model_constraints(new_model_class)
