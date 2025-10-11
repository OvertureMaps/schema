import sys
from pathlib import Path
from typing import Annotated, Union

import pytest
from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import JsonDict

from overture.schema.system import create_model
from overture.schema.system.model_constraint import (
    ModelConstraint,
    RadioGroupConstraint,
    radio_group,
)

sys.path.insert(0, str(Path(__file__).parent))  # Needed to import `util` peer module.

from util import assert_subset


@pytest.mark.parametrize("field_names", [[], (), ["foo"], ("bar",)])
def test_error_not_enough_field_names(field_names: list[str]):
    with pytest.raises(
        ValueError, match="`field_names` must contain at least two items"
    ):
        radio_group(*field_names)


@pytest.mark.parametrize(
    "constraint,model_class",
    [
        (
            RadioGroupConstraint("foo", "bar"),
            create_model("case1", foo=(bool, ...), bar=(int, ...)),
        ),
        (
            RadioGroupConstraint("bar", "baz"),
            create_model(
                "case2",
                bar=(bool | None, ...),
                baz=(Union[bool, int, None], ...),  # noqa: UP007
            ),
        ),
        (
            RadioGroupConstraint("foo", "bar", "baz"),
            create_model(
                "case3", foo=(bool | None, ...), bar=(Annotated[bool, "qux"], ...)
            ),
        ),
    ],
)
def test_error_invalid_model_class(
    constraint: RadioGroupConstraint, model_class: type[BaseModel]
) -> None:
    with pytest.raises(TypeError):
        constraint.validate_class(model_class)

    with pytest.raises(TypeError):
        constraint.decorate(model_class)


@pytest.mark.parametrize(
    "constraint",
    [
        RadioGroupConstraint("foo", "bar"),
        RadioGroupConstraint("foo", "baz"),
        RadioGroupConstraint("bar", "baz"),
        RadioGroupConstraint("foo", "bar", "baz"),
        RadioGroupConstraint("qux", "corge"),
    ],
)
def test_error_invalid_model_instance(constraint: RadioGroupConstraint) -> None:
    class TestModel(BaseModel):
        foo: bool = False
        bar: bool | None = None
        baz: Annotated[Annotated[bool, "inner"] | None, "outer"]
        qux: bool = True
        corge: bool = True

    model_instance = TestModel(baz="False")

    constraint.validate_class(TestModel)

    with pytest.raises(
        ValueError,
        match=r"exactly one field from the `bool` field group \[[\w, ]+\] must be True, but",
    ):
        constraint.validate_instance(model_instance)


@pytest.mark.parametrize(
    "field_names",
    [
        ["foo", "bar"],
        ["foo", "baz"],
        ["foo", "bar", "baz"],
        ["bar", "qux"],
        ["baz", "qux"],
        ["bar", "baz", "qux"],
    ],
)
def test_valid_model_instance(field_names: list[str]) -> None:
    class TestModel(BaseModel):
        foo: bool
        bar: bool
        baz: bool | None
        qux: bool | None

    constraint = RadioGroupConstraint(*field_names)
    constraint.validate_instance(TestModel(foo=True, bar=False, baz=None, qux=True))


def test_model_json_schema_no_model_config() -> None:
    @radio_group("foo", "baz", "qux")
    class TestModel(BaseModel):
        foo: bool = Field(default=None, alias="bar")
        baz: bool
        qux: bool = Field(alias="corge")

    actual = TestModel.model_json_schema()
    expect = {
        "oneOf": [
            {"properties": {"bar": {"const": True}}},
            {"properties": {"baz": {"const": True}}},
            {"properties": {"corge": {"const": True}}},
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
                "oneOf": [
                    {"properties": {"foo": {"const": True}}},
                    {"properties": {"baz": {"const": True}}},
                ]
            },
        ),
        (
            {"random": "value"},
            {
                "random": "value",
                "oneOf": [
                    {"properties": {"foo": {"const": True}}},
                    {"properties": {"baz": {"const": True}}},
                ],
            },
        ),
        (
            {"oneOf": 123},
            {
                "allOf": [
                    {"oneOf": 123},
                    {
                        "oneOf": [
                            {"properties": {"foo": {"const": True}}},
                            {"properties": {"baz": {"const": True}}},
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
    @radio_group("foo", "bar")
    class TestModel(BaseModel):
        model_config = ConfigDict(json_schema_extra=base_json_schema)

        foo: bool | None = None
        bar: bool | None = Field(default=True, alias="baz")

    actual = TestModel.model_json_schema()
    assert_subset(expect, actual, "expect", "actual")


def test_model_constraints() -> None:
    constraint = RadioGroupConstraint("foo", "bar")

    class TestModel(BaseModel):
        foo: bool
        bar: bool

    assert 0 == len(ModelConstraint.get_model_constraints(TestModel))

    new_model_class = constraint.decorate(TestModel)

    assert (constraint,) == ModelConstraint.get_model_constraints(new_model_class)
