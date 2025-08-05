from abc import ABC
from collections.abc import Callable
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    ValidationInfo,
    model_serializer,
)
from pydantic_core import core_schema

from overture.schema.validation import (
    allow_extension_fields,
)

from .enums import NameVariant, PerspectiveMode, Side
from .geometry import Geometry
from .types import (
    CommonNames,
    ConfidenceScore,
    CountryCode,
    FeatureUpdateTime,
    FeatureVersion,
    Id,
    JSONPointer,
    LanguageTag,
    Level,
    LinearlyReferencedRange,
    MaxZoom,
    MinZoom,
    Prominence,
    RegionCode,
    SortKey,
    Theme,
    TrimmedString,
    Type,
)
from .validation import ConstraintValidatedModel, UniqueItemsConstraint


class StrictBaseModel(BaseModel):
    """Base model that forbids additional properties in JSON Schema."""

    model_config = ConfigDict(extra="forbid")


@allow_extension_fields()
class ExtensibleBaseModel(ConstraintValidatedModel, BaseModel):
    """Base model that allows ext_* prefixed fields only."""

    model_config = ConfigDict(
        extra="allow",
    )  # Allow extra fields, which will be constrained by `@allow_extension_fields`


class GeometricRangeScope(StrictBaseModel):
    """Geometric scoping properties defining the range of positions on the segment where something is physically located or where a rule is active."""

    model_config = ConfigDict(frozen=True)

    # Optional

    between: LinearlyReferencedRange | None = None

    def __hash__(self) -> int:
        """Make GeometricRangeScope hashable."""
        return hash((tuple(self.between) if self.between is not None else None,))


class SideScope(StrictBaseModel):
    """Geometric scoping properties defining the side of a road modeled when moving along the line from beginning to end"""

    # Optional

    side: Side | None = None


class SourcePropertyItem(GeometricRangeScope):
    """An object storing the source for a specificed property. The property is a reference to the property element within this Feature, and will be referenced using JSON Pointer Notation RFC 6901 (https://datatracker.ietf.org/doc/rfc6901/). The source dataset for that referenced property will be specified in the overture list of approved sources from the Overture Data Working Group that contains the relevant metadata for that dataset including license source organization."""

    # Required

    property: JSONPointer
    dataset: str

    # Optional

    record_id: Annotated[
        str | None,
        Field(
            description="Refers to the specific record within the dataset that was used.",
        ),
    ] = None
    update_time: FeatureUpdateTime | None = None
    confidence: ConfidenceScore | None = None


Sources = Annotated[
    list[SourcePropertyItem],
    Field(
        min_length=1,
        description="""The array of source information for the properties of a given feature, with each entry being a source object which lists the property in JSON Pointer notation and the dataset approved sources from the Overture Data Working Group that contains the relevant metadata for that dataset including license source organization.""",
    ),
    UniqueItemsConstraint(),
]


class OvertureFeature(ExtensibleBaseModel, ABC):
    """Base class for all Overture features."""

    # Required

    id: Id
    theme: Theme
    # this is an enum in the JSON Schema, but that prevents OvertureFeature from being extended
    type: Type
    geometry: Geometry
    version: FeatureVersion

    # Optional

    sources: Sources | None = None

    @model_serializer(mode="wrap")  # type: ignore[type-var]
    def serialize_model(
        self,
        serializer: Callable[[Any], dict[str, Any]],
        info: ValidationInfo,
    ) -> dict[str, Any]:
        """Serialize to flattened structure for Python, GeoJSON for JSON."""
        # Get the default serialization
        data = serializer(self)

        # Check the serialization mode/context
        if info.mode == "json":
            # Transform to GeoJSON when outputting JSON
            return {
                "type": "Feature",
                "id": data.pop("id"),
                "geometry": data.pop("geometry"),
                "properties": data,  # All remaining fields go into properties
            }
        else:
            # Return flattened structure for Python output (info.mode == "python")
            return data

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: "core_schema.CoreSchema", handler: "GetJsonSchemaHandler"
    ) -> dict[str, Any]:
        """Generate JSON Schema that follows GeoJSON conventions."""
        # Get the base JSON schema with extension constraints from parent class
        json_schema = super().__get_pydantic_json_schema__(core_schema, handler)

        # Move all non-GeoJSON properties down into the GeoJSON `properties` object
        json_schema_top_level_required = json_schema.get("required", [])
        json_schema_top_level_properties = json_schema["properties"]
        geo_json_properties = {}
        geo_json_required = []

        for name in list(json_schema_top_level_properties.keys()):
            if name not in ["id", "geometry"]:
                value = json_schema_top_level_properties[name]
                geo_json_properties[name] = value
                del json_schema_top_level_properties[name]
                if name in json_schema_top_level_required:
                    json_schema_top_level_required.remove(name)
                    geo_json_required.append(name)

        # Create the properties schema
        geo_json_properties_schema = {
            "type": "object",
            "properties": geo_json_properties,
            # always reject properties that aren't defined in the schema
            "unevaluatedProperties": False,
        }

        if geo_json_required:
            geo_json_properties_schema["required"] = geo_json_required

        # Preserve extension constraints from the original schema
        if "patternProperties" in json_schema:
            geo_json_properties_schema["patternProperties"] = json_schema[
                "patternProperties"
            ]

        if "additionalProperties" in json_schema:
            geo_json_properties_schema["additionalProperties"] = json_schema[
                "additionalProperties"
            ]

        # Move constraint metadata from root to GeoJSON properties
        for constraint_key in ["anyOf", "allOf", "oneOf", "not"]:
            if constraint_key in json_schema:
                geo_json_properties_schema[constraint_key] = json_schema[constraint_key]
                del json_schema[constraint_key]

        json_schema_top_level_properties["properties"] = geo_json_properties_schema
        if "properties" not in json_schema_top_level_required:
            json_schema_top_level_required.append("properties")

        # Add the `"type": "Feature"` GeoJSON property at the top level
        json_schema_top_level_properties["type"] = {
            "type": "string",
            "const": "Feature",
        }
        if "type" not in json_schema_top_level_required:
            json_schema_top_level_required.append("type")

        # Update the required fields
        json_schema["required"] = json_schema_top_level_required

        return json_schema


class Perspectives(StrictBaseModel):
    """Political perspectives container."""

    # Required

    mode: Annotated[
        PerspectiveMode,
        Field(
            description="Whether the perspective holder accepts or disputes this name."
        ),
    ]
    countries: Annotated[
        list[CountryCode],
        Field(
            min_length=1, description="Countries holding the given mode of perspective."
        ),
        UniqueItemsConstraint(),
    ]


class NameRule(GeometricRangeScope, SideScope):
    """Name rule with variant and language specification."""

    # Required

    value: Annotated[TrimmedString, Field(min_length=1)]
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


class Names(StrictBaseModel):
    """Multilingual names container."""

    # Required

    primary: Annotated[
        TrimmedString, Field(min_length=1, description="The most commonly used name.")
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
    """Properties defining feature Z-order, i.e., stacking order"""

    level: Level | None = None


class CartographicHints(StrictBaseModel):
    """Defines cartographic hints for optimal use of Overture features in map-making."""

    # Optional

    prominence: Prominence | None = None
    min_zoom: MinZoom | None = None
    max_zoom: MaxZoom | None = None
    sort_key: SortKey | None = None


class CartographicallyHinted(BaseModel):
    cartography: Annotated[CartographicHints | None, Field(title="cartography")] = None


class Address(StrictBaseModel):
    # Optional

    freeform: Annotated[
        str | None,
        Field(
            description="Free-form address that contains street name, house number and other address info",
        ),
    ] = None
    locality: Annotated[
        str | None,
        Field(
            description="Name of the city or neighborhood where the address is located",
        ),
    ] = None
    postcode: Annotated[
        str | None, Field(description="Postal code where the address is located")
    ] = None
    region: RegionCode | None = None
    country: CountryCode | None = None
