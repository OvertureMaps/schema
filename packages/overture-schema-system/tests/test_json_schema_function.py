"""Unit tests for `json_schema()` model-expression validation and generation."""

from typing import Annotated, Literal, NewType

import pytest
from pydantic import BaseModel, Field

from overture.schema.system.json_schema import json_schema


class Foo(BaseModel):
    name: str


class Bar(BaseModel):
    label: str


class RoadKind(BaseModel):
    kind: Literal["road"]


class WaterKind(BaseModel):
    kind: Literal["water"]


def test_json_schema_for_bare_model() -> None:
    schema = json_schema(Foo)
    assert schema["title"] == "Foo"
    assert "name" in schema["properties"]


def test_json_schema_for_union_of_models() -> None:
    schema = json_schema(Foo | Bar)
    assert "anyOf" in schema or "oneOf" in schema


def test_json_schema_for_annotated_model() -> None:
    schema = json_schema(
        Annotated[Foo, Field(title="AnnotatedFoo", description="Annotated model")]
    )
    assert schema["title"] == "AnnotatedFoo"
    assert schema["description"] == "Annotated model"


def test_json_schema_for_newtype_over_model() -> None:
    Aliased = NewType("Aliased", Foo)
    assert json_schema(Aliased) == json_schema(Foo)


def test_json_schema_for_discriminated_union_preserves_discriminator() -> None:
    """A discriminated union's `Annotated[..., Field(discriminator=...)]` wrapper must survive.

    Regression test: `json_schema()` must not unwrap `Annotated` before handing a union expression
    to `TypeAdapter`, or the discriminator metadata (and the resulting `oneOf` schema) is lost.
    """
    Kind = Annotated[RoadKind | WaterKind, Field(discriminator="kind")]

    schema = json_schema(Kind)

    assert "oneOf" in schema
    assert "discriminator" in schema


def test_json_schema_rejects_non_model() -> None:
    with pytest.raises(TypeError):
        json_schema(int)


def test_json_schema_rejects_partial_model_union() -> None:
    with pytest.raises(TypeError):
        json_schema(Foo | int)
