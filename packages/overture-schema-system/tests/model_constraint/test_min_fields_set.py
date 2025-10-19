import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from pydantic import BaseModel, ConfigDict

from overture.schema.system import create_model
from overture.schema.system.model_constraint import (
    MinFieldsSetConstraint,
    min_fields_set,
)

sys.path.insert(0, str(Path(__file__).parent.parent))  # Needed to import `util` module.

from util import assert_subset


def test_error_invalid_count_type() -> None:
    with pytest.raises(
        TypeError, match="`count` must be an `int`, but 'foo' is a `str`"
    ):
        min_fields_set(cast(int, "foo"))


@pytest.mark.parametrize("count", [-1, 0])
def test_error_invalid_count_value(count: int) -> None:
    with pytest.raises(ValueError, match="`count` must be a positive number"):
        min_fields_set(count)


@pytest.mark.parametrize(
    "count,model_class",
    [
        (1, create_model("case11")),
        (1, create_model("case12", __config__=ConfigDict(extra="forbid"))),
        (1, create_model("case13", __config__=ConfigDict(extra="ignore"))),
        (2, create_model("case21", foo=(int | None, ...))),
        (
            2,
            create_model(
                "case22", foo=(int | None, ...), __config__=ConfigDict(extra="forbid")
            ),
        ),
        (
            2,
            create_model(
                "case23", foo=(int | None, ...), __config__=ConfigDict(extra="ignore")
            ),
        ),
    ],
)
def test_error_invalid_model_class(count: int, model_class: type[BaseModel]) -> None:
    constraint = MinFieldsSetConstraint(count)

    with pytest.raises(TypeError):
        constraint.validate_class(model_class)

    with pytest.raises(TypeError):
        constraint.decorate(model_class)


@pytest.mark.parametrize(
    "count,model_class,factory",
    [
        (1, create_model("case11", foo=(int | None, None)), lambda x: x()),
        (
            1,
            create_model(
                "case12", foo=(int | None, None), __config__=ConfigDict(extra="allow")
            ),
            lambda x: x(),
        ),
        (
            2,
            create_model(
                "case21", foo=(int | None, None), __config__=ConfigDict(extra="allow")
            ),
            lambda x: x(foo=42),
        ),
        (
            2,
            create_model(
                "case22", foo=(int | None, None), __config__=ConfigDict(extra="allow")
            ),
            lambda x: x(bar=42),
        ),
        (
            2,
            create_model("case23", foo=(int | None, None), bar=(str | None, None)),
            lambda x: x(),
        ),
        (
            2,
            create_model("case23", foo=(int | None, None), bar=(str | None, None)),
            lambda x: x(foo=42),
        ),
        (
            2,
            create_model("case23", foo=(int | None, None), bar=(str | None, None)),
            lambda x: x(bar="baz"),
        ),
    ],
)
def test_error_invalid_model_instance(
    count: int,
    model_class: type[BaseModel],
    factory: Callable[[type[BaseModel]], BaseModel],
) -> None:
    constraint = MinFieldsSetConstraint(count)

    constraint.validate_class(model_class)

    model_instance = factory(model_class)

    with pytest.raises(
        ValueError,
        match=r"only \d+ fields are explicitly set, but a minimum of \d+ are required",
    ):
        constraint.validate_instance(model_instance)


@pytest.mark.parametrize(
    "count,model_class,factory",
    [
        (1, create_model("case11", foo=(int | None, None)), lambda x: x(foo=None)),
        (1, create_model("case12", foo=(int | None, None)), lambda x: x(foo=42)),
        (
            1,
            create_model(
                "case13", foo=(int | None, None), __config__=ConfigDict(extra="allow")
            ),
            lambda x: x(hello=None),
        ),
        (
            1,
            create_model(
                "case14", foo=(int | None, None), __config__=ConfigDict(extra="allow")
            ),
            lambda x: x(hello="world"),
        ),
        (
            1,
            create_model(
                "case15", foo=(int | None, None), __config__=ConfigDict(extra="allow")
            ),
            lambda x: x(foo=13, hello="world"),
        ),
        (
            2,
            create_model(
                "case21", foo=(int | None, None), __config__=ConfigDict(extra="allow")
            ),
            lambda x: x(foo=None, hello="world"),
        ),
        (
            2,
            create_model(
                "case22", foo=(int | None, None), __config__=ConfigDict(extra="allow")
            ),
            lambda x: x(foo=42, hello="world"),
        ),
        (
            2,
            create_model(
                "case23", foo=(int | None, None), __config__=ConfigDict(extra="allow")
            ),
            lambda x: x(foo=None, hello=None),
        ),
        (
            2,
            create_model("case24", foo=(int | None, None), bar=(str | None, None)),
            lambda x: x(foo=13, bar="baz"),
        ),
    ],
)
def test_valid_model_instance(
    count: int,
    model_class: type[BaseModel],
    factory: Callable[[type[BaseModel]], BaseModel],
) -> None:
    constraint = MinFieldsSetConstraint(count)
    constraint.validate_class(model_class)
    model_instance = factory(model_class)
    constraint.validate_instance(model_instance)


def test_model_json_schema_no_model_config() -> None:
    @min_fields_set(2)
    class TestModel(BaseModel):
        foo: bool | None = None
        baz: bool | None = None
        qux: bool | None = None

    actual = TestModel.model_json_schema()
    expect = {"minProperties": 2}
    assert expect == TestModel.model_config["json_schema_extra"]
    assert_subset(expect, actual, "expect", "actual")


def test_model_json_schema_already_set_same() -> None:
    expect = {"minProperties": 3, "hello": "world"}

    @min_fields_set(3)
    class TestModel(BaseModel):
        model_config = ConfigDict(json_schema_extra=expect, extra="allow")

        foo: bool | None = None
        baz: bool | None = None
        qux: bool | None = None

    actual = TestModel.model_json_schema()
    assert expect == TestModel.model_config["json_schema_extra"]
    assert_subset(expect, actual, "expect", "actual")


def test_model_json_schema_error_already_set_different() -> None:
    expect = {"minProperties": 1, "hello": "world"}

    with pytest.raises(
        RuntimeError,
        match='JSON schema for model class `TestModel` has conflicting "minProperties" value 1',
    ):

        @min_fields_set(3)
        class TestModel(BaseModel):
            model_config = ConfigDict(json_schema_extra=expect, extra="allow")

            foo: bool | None = None
            baz: bool | None = None
            qux: bool | None = None
