"""Shared test support for overture-schema-codegen tests.

Provides reusable model fixtures and helpers. Pytest fixtures are in conftest.py.
"""

from __future__ import annotations

from collections.abc import Mapping
from difflib import unified_diff
from enum import Enum
from pathlib import Path
from typing import Annotated, Generic, Literal, NewType, TypeVar

import pytest
from overture.schema.codegen.model_extraction import extract_model
from overture.schema.codegen.pydantic_extraction import extract_pydantic_type
from overture.schema.codegen.specs import (
    AnnotatedField,
    EnumMemberSpec,
    EnumSpec,
    FieldSpec,
    ModelSpec,
    TypeIdentity,
    UnionSpec,
    is_model_class,
)
from overture.schema.codegen.type_analyzer import TypeInfo, TypeKind
from overture.schema.core.discovery import discover_models
from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import require_any_of
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
    float64,
    int32,
)
from overture.schema.system.ref import Id, Identified, Reference, Relationship
from overture.schema.system.string import HexColor, LanguageTag, StrippedString
from pydantic import BaseModel, EmailStr, Field, HttpUrl

STR_TYPE = TypeInfo(base_type="str", kind=TypeKind.PRIMITIVE)

ThemeT = TypeVar("ThemeT")
TypeT = TypeVar("TypeT")


class SimpleModel(BaseModel):
    """A simple model."""

    name: str


class FeatureBase(BaseModel, Generic[ThemeT, TypeT]):
    """Base class mimicking OvertureFeature pattern for tests."""

    theme: ThemeT
    type: TypeT


# Separate TypeVars from ThemeT/TypeT: IdentifiedFeature models a
# non-Overture user building on Identified with their own nomenclature.
CategoryT = TypeVar("CategoryT")
KindT = TypeVar("KindT")


class IdentifiedFeature(Identified, Generic[CategoryT, KindT]):
    """Feature with identity and typed category/kind."""

    category: CategoryT
    kind: KindT


class InstrumentFamily(str, DocumentedEnum):
    """Classification by sound production method."""

    STRING = "string", "Sound from vibrating strings"
    WIND = "wind", "Sound from vibrating air column"
    PERCUSSION = "percussion"


class SimpleKind(str, Enum):
    SMALL = "small"
    LARGE = "large"


class Instrument(
    IdentifiedFeature[Literal["music"], Literal["instrument"]],
):
    """A musical instrument.

    Instruments produce sound through vibration. They are classified
    by how sound is produced.
    """

    name: str = Field(description="Common name")
    tuning: float64 | None = Field(
        None,
        description=("Concert pitch in Hz.\n\nStandard tuning is 440 Hz."),
    )
    num_strings: int32 | None = Field(None)
    family: InstrumentFamily | None = None
    color: HexColor | None = Field(None, description="Body color")
    tags: Annotated[list[str], UniqueItemsConstraint()] | None = None


@require_any_of("name", "description")
class Venue(
    IdentifiedFeature[Literal["music"], Literal["venue"]],
):
    """A concert venue.

    A location where musical performances take place.
    """

    name: str | None = Field(None, description="Venue name")
    description: str | None = None
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POINT, GeometryType.POLYGON),
    ]
    capacity: Annotated[int, Field(ge=1)] | None = None
    resident_ensemble: (
        Annotated[Id, Reference(Relationship.BELONGS_TO, Instrument)] | None
    ) = None


class SourceItem(BaseModel):
    """A source data reference."""

    dataset: str = Field(description="Source dataset name")


Sources = NewType(
    "Sources",
    Annotated[
        list[SourceItem],
        Field(min_length=1, description="Source data references"),
        UniqueItemsConstraint(),
    ],
)


class FeatureWithSources(
    FeatureBase[Literal["test"], Literal["sourced"]],
):
    """A feature with a Sources field."""

    name: str = Field(description="Feature name")
    sources: Sources | None = None


class Address(BaseModel):
    """A mailing address."""

    street: str = Field(description="Street name")
    city: str = Field(description="City name")
    zip_code: str | None = Field(None, description="Postal code")


class FeatureWithAddress(
    FeatureBase[Literal["test"], Literal["addressed"]],
):
    """A feature with an address field."""

    title: str = Field(description="Feature title")
    address: Address


class TreeNode(BaseModel):
    """A recursive tree node."""

    label: str = Field(description="Node label")
    parent: TreeNode | None = None


class Widget(BaseModel):
    active: bool
    label: str = Field(description="Display label")


CommonNames = NewType("CommonNames", dict[LanguageTag, StrippedString])


class FeatureWithDict(
    FeatureBase[Literal["test"], Literal["dictfeat"]],
):
    """A feature with dict fields."""

    name: str = Field(description="Feature name")
    names: CommonNames | None = Field(None, description="Localized names")
    alt_names: dict[LanguageTag, StrippedString] | None = Field(
        None, description="Alternate localized names"
    )
    tags: dict[str, str] | None = Field(None, description="Arbitrary tags")
    metadata: dict[str, int] = Field(description="Numeric metadata")


class FeatureWithUrl(FeatureBase[Literal["test"], Literal["linked"]]):
    """A feature with Pydantic URL and email fields."""

    website: HttpUrl | None = None
    emails: list[EmailStr] | None = None


HTTP_URL_SPEC = extract_pydantic_type(HttpUrl)
EMAIL_STR_SPEC = extract_pydantic_type(EmailStr)


class SegmentBase(BaseModel):
    """Common base for test segments."""

    geometry: str
    subtype: str


class RoadSegment(SegmentBase):
    subtype: Literal["road"]
    class_: Annotated[str, Field(alias="class")]
    speed_limit: int | None = None


class RailSegment(SegmentBase):
    subtype: Literal["rail"]
    class_: Annotated[int, Field(alias="class")]
    rail_gauge: float | None = None


class WaterSegment(SegmentBase):
    subtype: Literal["water"]


TestSegment = Annotated[
    RoadSegment | RailSegment | WaterSegment,
    Field(description="Test segment union"),
]


def make_union_spec(
    name: str = "TestUnion",
    *,
    description: str | None = None,
    annotated_fields: list[AnnotatedField] | None = None,
    members: list[type[BaseModel]] | None = None,
    source_annotation: object = None,
    common_base: type[BaseModel] | None = None,
    entry_point: str | None = None,
) -> UnionSpec:
    """Build a UnionSpec with sensible defaults for tests."""
    return UnionSpec(
        name=name,
        description=description,
        annotated_fields=annotated_fields or [],
        members=members or [],
        discriminator_field=None,
        discriminator_mapping=None,
        source_annotation=source_annotation,
        common_base=common_base or BaseModel,
        entry_point=entry_point,
    )


def find_model_class(name: str, models: dict[object, object]) -> type[BaseModel]:
    """Find a discovered model class by name."""
    matches = [v for v in models.values() if getattr(v, "__name__", None) == name]
    assert matches, f"{name} model not found"
    match = matches[0]
    assert isinstance(match, type)
    assert issubclass(match, BaseModel)
    return match


def find_field(spec: ModelSpec, name: str) -> FieldSpec:
    """Find a field by name in a ModelSpec, raising if missing."""
    return next(f for f in spec.fields if f.name == name)


def find_member(spec: EnumSpec, name: str) -> EnumMemberSpec:
    """Find a member by name in an EnumSpec, raising if missing."""
    return next(m for m in spec.members if m.name == name)


T = TypeVar("T")


def lookup_by_name(mapping: dict[TypeIdentity, T], name: str) -> T:
    """Look up a value in a TypeIdentity-keyed dict by name, raising KeyError if absent."""
    for tid, value in mapping.items():
        if tid.name == name:
            return value
    raise KeyError(name)


def has_name(mapping: Mapping[TypeIdentity, object], name: str) -> bool:
    """Check whether a TypeIdentity-keyed mapping contains a key with the given name."""
    return any(tid.name == name for tid in mapping)


def assert_literal_field(
    spec: ModelSpec, field_name: str, expected_value: object
) -> None:
    """Assert a field is a single-value Literal with the expected value."""
    field = find_field(spec, field_name)
    assert field.type_info.kind == TypeKind.LITERAL
    assert field.type_info.literal_values == (expected_value,)


def flat_specs_from_discovery(
    theme: str | None = None,
) -> list[ModelSpec]:
    """Build a flat list of ModelSpecs from discovery, with entry_point set."""
    models = discover_models()
    if theme:
        models = {k: v for k, v in models.items() if k.theme == theme}
    result = []
    for key, cls in models.items():
        if not is_model_class(cls):
            continue
        result.append(extract_model(cls, entry_point=key.entry_point))
    return result


def assert_golden(actual: str, golden_path: Path, *, update: bool) -> None:
    """Compare rendered output against a golden file.

    When update is True, writes actual content to the golden file
    instead of comparing.
    """
    if update:
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(actual)
        return
    expected = golden_path.read_text()
    if actual != expected:
        diff = "\n".join(
            unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile=str(golden_path),
                tofile="actual",
                lineterm="",
            )
        )
        pytest.fail(f"Golden file mismatch:\n{diff}")
