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
from annotated_types import MinLen
from overture.schema.codegen.extraction.field import LiteralScalar, Primitive
from overture.schema.codegen.extraction.field_walk import terminal_of
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.extraction.pydantic_extraction import extract_pydantic_type
from overture.schema.codegen.extraction.specs import (
    AnnotatedField,
    EnumMemberSpec,
    EnumSpec,
    FieldSpec,
    MemberSpec,
    ModelSpec,
    RecordSpec,
    TypeIdentity,
    UnionSpec,
    is_model_class,
    is_union_alias,
)
from overture.schema.codegen.extraction.union_extraction import extract_union
from overture.schema.codegen.layout.module_layout import entry_point_class
from overture.schema.codegen.spec_discovery import extract_model_spec
from overture.schema.system.discovery import (
    TagSelector,
    discover_models,
    filter_models,
)
from overture.schema.system.discovery.tag import get_values_for_key
from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import radio_group, require_any_of
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

STR_TYPE = Primitive(base_type="str")

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
        Annotated[Id, Reference(Relationship.AGGREGATION, Instrument, role="part_of")]
        | None
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


class DatasetEntry(BaseModel):
    """A dataset with required URL fields."""

    name: str = Field(description="Dataset name")
    url: HttpUrl
    download_urls: list[HttpUrl] | None = None


class FeatureWithRequiredUrl(FeatureBase[Literal["test"], Literal["urlreq"]]):
    """A feature with required URL fields at multiple nesting levels."""

    datasets: list[DatasetEntry]


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


class ShortNamesSegment(SegmentBase):
    """Segment variant whose `aliases` requires at least one entry."""

    subtype: Literal["short"]
    aliases: Annotated[list[str], Field(min_length=1)] | None = None


class LongNamesSegment(SegmentBase):
    """Segment variant whose `aliases` requires at least five entries."""

    subtype: Literal["long"]
    aliases: Annotated[list[str], Field(min_length=5)] | None = None


TestSegmentDivergingConstraints = Annotated[
    ShortNamesSegment | LongNamesSegment,
    Field(description="Union whose members declare diverging field constraints"),
]


class VehicleKind(str, Enum):
    """Vehicle classification."""

    CAR = "car"
    BIKE = "bike"


class CarVariant(SegmentBase):
    subtype: Literal[VehicleKind.CAR]
    doors: int | None = None


class BikeVariant(SegmentBase):
    subtype: Literal[VehicleKind.BIKE]
    has_basket: bool | None = None


TestEnumDiscriminatorUnion = Annotated[
    CarVariant | BikeVariant,
    Field(description="Union with enum-valued discriminator", discriminator="subtype"),
]


class ContactInfo(BaseModel):
    """Contact information for a venue."""

    email: str = Field(description="Email address")
    phone: str | None = Field(None, description="Phone number")


class VenueWithContact(SegmentBase):
    """A segment variant with a nested sub-model field."""

    subtype: Literal["venue"]
    contact: ContactInfo


TestSegmentWithSubModel = Annotated[
    RoadSegment | VenueWithContact,
    Field(description="Test segment union with sub-model member"),
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
    """Build a UnionSpec with sensible defaults for tests.

    `member_specs` is derived from `members` via `extract_model`, matching
    what `extract_union` produces, so specs built here behave the same
    through `_model_checks_for_union` and the base-row generators.
    """
    members = members or []
    return UnionSpec(
        name=name,
        description=description,
        annotated_fields=annotated_fields or [],
        members=members,
        discriminator_field=None,
        discriminator_mapping=None,
        source_annotation=source_annotation,
        common_base=common_base or BaseModel,
        member_specs=[MemberSpec(m, extract_model(m)) for m in members],
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


def find_field(spec: RecordSpec, name: str) -> FieldSpec:
    """Find a field by name in a RecordSpec, raising if missing."""
    return next(f for f in spec.fields if f.name == name)


def find_member(spec: EnumSpec, name: str) -> EnumMemberSpec:
    """Find a member by name in an EnumSpec, raising if missing."""
    return next(m for m in spec.members if m.name == name)


def find_theme(tags: frozenset[str]) -> str | None:
    """Extract the theme from a set of tags, if present."""
    return next(iter(get_values_for_key(tags, "overture:theme")), None)


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
    spec: RecordSpec, field_name: str, expected_value: object
) -> None:
    """Assert a field is a single-value Literal with the expected value."""
    field = find_field(spec, field_name)
    terminal = terminal_of(field.shape)
    assert isinstance(terminal, LiteralScalar)
    assert terminal.values == (expected_value,)


def flat_specs_from_discovery(
    theme: str | None = None,
) -> list[RecordSpec]:
    """Build a flat list of RecordSpecs from discovery, with entry_point set."""
    models = discover_models()
    if theme:
        models = filter_models(
            models, TagSelector(include_any=(f"overture:theme={theme}",))
        )
    return [
        spec
        for key, cls in models.items()
        if isinstance(spec := extract_model_spec(key, cls), RecordSpec)
    ]


class TaggedVariantA(SegmentBase):
    """Segment variant with a unique-items tags field."""

    subtype: Literal["tagged_a"]
    tags: Annotated[list[str], UniqueItemsConstraint()] | None = None


class TaggedVariantB(SegmentBase):
    """Segment variant with a unique-items tags field (distinct instance, same constraint)."""

    subtype: Literal["tagged_b"]
    tags: Annotated[list[str], UniqueItemsConstraint()] | None = None


TestSegmentEqualConstraints = Annotated[
    TaggedVariantA | TaggedVariantB,
    Field(
        description="Union whose members share a field with equal-but-distinct constraint instances"
    ),
]


class LiteralSubtypeModel(BaseModel):
    """Model with a required Literal field and an optional string."""

    subtype: Literal["a", "b", "c"]
    name: str | None = None


class TripleInnerModel(BaseModel):
    tag: Annotated[str, MinLen(1)]


class TripleNestedArrayModel(BaseModel):
    deep: list[list[list[TripleInnerModel]]]


@radio_group("a", "b")
class RadioModel(BaseModel):
    a: bool = False
    b: bool = False


@require_any_of("x", "y")
class RequireAnyModel(BaseModel):
    x: str | None = None
    y: str | None = None


def discover_feature(class_name: str) -> ModelSpec:
    """Discover and extract a model spec by class name."""
    models = discover_models()
    for key, entry in models.items():
        if (is_model_class(entry) and entry.__name__ == class_name) or (
            is_union_alias(entry) and entry_point_class(key.entry_point) == class_name
        ):
            spec = extract_model_spec(key, entry)
            if spec is not None:
                return spec
    raise LookupError(f"{class_name} not found in discovered models")


def spec_for_model(
    cls: type[BaseModel],
    *,
    entry_point: str | None = None,
    partitions: Mapping[str, str] | None = None,
) -> RecordSpec:
    """Extract a model class for tests; sub-specs are populated by extract_model."""
    return extract_model(cls, entry_point=entry_point, partitions=partitions)


def union_spec_for(name: str, union_type: object) -> UnionSpec:
    """Extract a discriminated-union annotation for tests."""
    return extract_union(name, union_type)


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
