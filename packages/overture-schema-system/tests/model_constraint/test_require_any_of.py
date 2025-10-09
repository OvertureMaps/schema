import sys
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.json_schema import JsonDict

from overture.schema.system.model_constraint import (
    ModelConstraint,
    RequireAnyOfConstraint,
    require_any_of,
)

sys.path.insert(0, str(Path(__file__).parent))  # Needed to import `util` peer module.

from util import assert_subset


@pytest.mark.parametrize("field_names", [[], ["foo"]])
def test_error_not_enough_field_names(field_names: list[str]):
    with pytest.raises(
        ValueError, match="field_names` must contain at least two items"
    ):
        require_any_of(*field_names)


@pytest.mark.parametrize("field_names", [["foo", "foo"], ["bar", "foo", "bar"]])
def test_error_duplicate_field_names(field_names: list[str]):
    with pytest.raises(ValueError, match="`field_names` must not contain duplicates"):
        require_any_of(*field_names)


def test_error_invalid_model_class():
    expect = "specifies fields that are not in the model class `TestModel`: foo, bar"

    with pytest.raises(TypeError, match=expect):

        @require_any_of("foo", "bar")
        class TestModel(BaseModel):
            baz: int

    with pytest.raises(TypeError, match=expect):

        class TestModel(BaseModel):
            baz: int

        RequireAnyOfConstraint("foo", "bar").validate_class(TestModel)


def test_error_invalid_model_instance():
    @require_any_of("foo", "bar")
    class TestModel(BaseModel):
        foo: int | None = None
        bar: str | None = None

    with pytest.raises(
        ValidationError,
        match="at least one of these fields must have a value, but none do: foo, bar",
    ):
        TestModel(foo=None, bar=None)


@pytest.mark.parametrize("foo,bar", [(42, "hello"), (42, None), (None, "hello")])
def test_valid_model_instance(foo: int | None, bar: str | None):
    @require_any_of("foo", "bar")
    class TestModel(BaseModel):
        foo: int | None = None
        bar: str | None = None

    TestModel(foo=foo, bar=bar)


def test_model_json_schema_no_model_config():
    @require_any_of("foo", "bar")
    class TestModel(BaseModel):
        foo: int | None = None
        bar: str | None = Field(default=None, alias="baz")

    actual = TestModel.model_json_schema()
    expect = {"anyOf": [{"required": ["foo"]}, {"required": ["baz"]}]}
    assert expect == TestModel.model_config["json_schema_extra"]
    assert_subset(expect, actual, "expect", "actual")


@pytest.mark.parametrize(
    "base_json_schema,expect",
    [
        (None, {"anyOf": [{"required": ["foo"]}, {"required": ["baz"]}]}),
        (
            {"anyOf": "anything"},
            {
                "allOf": [
                    {"anyOf": "anything"},
                    {"anyOf": [{"required": ["foo"]}, {"required": ["baz"]}]},
                ]
            },
        ),
    ],
)
def test_model_json_schema_with_model_config(
    base_json_schema: JsonDict | None, expect: JsonDict
):
    @require_any_of("foo", "bar")
    class TestModel(BaseModel):
        model_config = ConfigDict(json_schema_extra=base_json_schema)

        foo: int | None = None
        bar: str | None = Field(default=None, alias="baz")

    actual = TestModel.model_json_schema()
    assert_subset(expect, actual, "expect", "actual")


def test_model_constraints():
    constraint = RequireAnyOfConstraint("foo", "bar")

    class TestModel(BaseModel):
        foo: int | None = None
        bar: str | None = None

    assert 0 == len(ModelConstraint.get_model_constraints(TestModel))

    new_model_class = constraint.decorate(TestModel)

    assert (constraint,) == ModelConstraint.get_model_constraints(new_model_class)
