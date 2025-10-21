import textwrap
from typing import Annotated, Generic, NewType, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from typing_extensions import Self

from overture.schema.system.feature import Feature
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.primitive import (
    Geometry,
)
from overture.schema.system.ref import Id, Identified
from overture.schema.system.string import (
    CountryCodeAlpha2,
    JsonPointer,
    LanguageTag,
    StrippedString,
)

from .enums import NameVariant, PerspectiveMode
from .scoping.lr import LinearlyReferencedRange
from .scoping.side import Side
from .types import (
    CommonNames,
    ConfidenceScore,
    FeatureUpdateTime,
    FeatureVersion,
    Level,
    MaxZoom,
    MinZoom,
    Prominence,
    SortKey,
)


@no_extra_fields
class GeometricRangeScope(BaseModel):
    """Geometric scoping properties defining the range of positions on the segment where
    something is physically located or where a rule is active."""

    model_config = ConfigDict(frozen=True)

    # Optional

    between: LinearlyReferencedRange | None = None

    def __hash__(self) -> int:
        """Make GeometricRangeScope hashable."""
        return hash((tuple(self.between) if self.between is not None else None,))


@no_extra_fields
class SideScope(BaseModel):
    """Geometric scoping properties defining the side of a road modeled when moving
    along the line from beginning to end."""

    # Optional

    side: Side | None = None


@no_extra_fields
class SourcePropertyItem(GeometricRangeScope):
    """An object storing the source for a specified property.

    The property is a reference to the property element within this Feature, and will be
    referenced using JSON Pointer Notation RFC 6901 (
    https://datatracker.ietf.org/doc/rfc6901/).
    The source dataset for that referenced property will be specified in the overture list of approved sources from the Overture Data Working Group that contains the relevant metadata for that dataset including license source organization.
    """

    # Required

    property: JsonPointer
    dataset: str

    # Optional

    license: Annotated[
        StrippedString | None,
        Field(
            description="License name. This should be a valid SPDX license identifier when available. If the license is NULL, contact the data provider for more license information.",
        ),
    ] = None
    record_id: Annotated[
        str | None,
        Field(
            description="Refers to the specific record within the dataset that was used.",
        ),
    ] = None
    update_time: FeatureUpdateTime | None = None
    confidence: ConfidenceScore | None = None


Sources = NewType(
    "Sources",
    Annotated[
        list[SourcePropertyItem],
        Field(
            min_length=1,
            description="""The array of source information for the properties of a given feature, with each entry being a source object which lists the property in JSON Pointer notation and the dataset approved sources from the Overture Data Working Group that contains the relevant metadata for that dataset including license source organization.""",
        ),
        UniqueItemsConstraint(),
    ],
)

ThemeT = TypeVar("ThemeT", bound=str)
TypeT = TypeVar("TypeT", bound=str)


class OvertureFeature(Identified, Feature, Generic[ThemeT, TypeT]):
    """Base class for all Overture features."""

    # Only used to suport `ext_*` fields, which are on a deprecation path.
    model_config = ConfigDict(extra="allow")

    # Required

    id: Id = Field(
        description="A feature ID. This may be an ID associated with the Global Entity Reference System (GERS) if—and-only-if the feature represents an entity that is part of GERS."
    )  # type: ignore[assignment]
    theme: ThemeT
    # this is an enum in the JSON Schema, but that prevents Feature from being extended
    type: TypeT
    geometry: Geometry
    version: FeatureVersion

    # Optional

    sources: Sources | None = None

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        extra = self.model_extra
        invalid_extra_fields = (
            [f for f in extra.keys() if not f.startswith("ext_")] if extra else ()
        )
        if invalid_extra_fields:
            maybe_plural = "s" if len(invalid_extra_fields) > 1 else ""
            raise ValueError(
                f"invalid extra field name{maybe_plural}: {', '.join(invalid_extra_fields)} "
                "(extra fields are temporarily allowed, but only if their names start with 'ext_', "
                "but all extra field name support in {self.__class__.name} is on a deprecation path "
                "and will be removed)"
            )
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        schema: core_schema.CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        # Get the main Feature JSON schema.
        json_schema = super().__get_pydantic_json_schema__(schema, handler)

        # Explicitly allow `ext_*` properties, but no other properties, in the properties object.
        # This feature only exists to get to initial parity between the hand-written JSON Schema and
        # the Pydantic port. Once Pydantic is the primary, it will be deprecated.
        properties_object_schema = json_schema["properties"]["properties"]
        properties_object_schema["patternProperties"] = {
            "^ext_.*$": {
                "description": textwrap.dedent("""
                    Additional top-level properties are allowed if prefixed by `ext_`.

                    This feature is a on a deprecation path and will be removed once the schema is
                    fully migrated to Pydantic.
                """).strip(),
            }
        }
        properties_object_schema["additionalProperties"] = False

        return json_schema


@no_extra_fields
class Perspectives(BaseModel):
    """Political perspectives container."""

    # Required

    mode: Annotated[
        PerspectiveMode,
        Field(
            description="Whether the perspective holder accepts or disputes this name."
        ),
    ]
    countries: Annotated[
        list[CountryCodeAlpha2],
        Field(
            min_length=1, description="Countries holding the given mode of perspective."
        ),
        UniqueItemsConstraint(),
    ]


@no_extra_fields
class NameRule(GeometricRangeScope, SideScope):
    """Name rule with variant and language specification."""

    # Required

    value: Annotated[StrippedString, Field(min_length=1)]
    variant: NameVariant

    # Optional

    language: LanguageTag | None = None
    perspectives: (
        Annotated[
            Perspectives,
            Field(
                description="Political perspectives from which a named feature is viewed."
            ),
        ]
        | None
    ) = None


@no_extra_fields
class Names(BaseModel):
    """Multilingual names container."""

    # Required

    primary: Annotated[
        StrippedString, Field(min_length=1, description="The most commonly used name.")
    ]

    # Optional

    common: CommonNames | None = None
    rules: Annotated[
        list[NameRule] | None,
        Field(
            description="Rules for names that cannot be specified in the simple common names property. These rules can cover other name variants such as official, alternate, and short; and they can optionally include geometric scoping (linear referencing) and side-of-road scoping for complex cases.",
        ),
    ] = None


class Named(BaseModel):
    """Properties defining the names of a feature."""

    names: Names | None = None


class Stacked(BaseModel):
    """Properties defining feature Z-order, i.e., stacking order."""

    level: Level | None = None


@no_extra_fields
class CartographicHints(BaseModel):
    """Defines cartographic hints for optimal use of Overture features in map-making."""

    # Optional

    prominence: Prominence | None = None
    min_zoom: MinZoom | None = None
    max_zoom: MaxZoom | None = None
    sort_key: SortKey | None = None


class CartographicallyHinted(BaseModel):
    cartography: Annotated[CartographicHints | None, Field(title="cartography")] = None
