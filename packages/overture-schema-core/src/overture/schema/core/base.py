"""Base schema classes for Overture Maps features."""

from abc import ABC
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    model_serializer,
    model_validator,
)
from pydantic_core import core_schema

from .geometry import Geometry

# Type aliases
ISO8601DateTime = str
JSONPointer = str
LinearReferenceRange = tuple[float, float]


class StrictBaseModel(BaseModel):
    """Base model that forbids additional properties in JSON Schema."""

    model_config = ConfigDict(extra="forbid")


class SourceItem(StrictBaseModel):
    """Source information for a specific property."""

    property: JSONPointer = Field(..., description="JSON Pointer to the property")
    dataset: str = Field(..., description="Source dataset identifier")
    record_id: str = Field(default=None, description="Specific record within dataset")
    update_time: ISO8601DateTime = Field(
        default=None, description="When this property was last updated"
    )
    confidence: float = Field(
        default=None, ge=0, le=1, description="Confidence value for ML-derived data"
    )
    between: LinearReferenceRange = Field(
        default=None, description="Linear referencing range"
    )


class ExtensibleBaseModel(BaseModel):
    """Base model that allows ext_* prefixed fields only."""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow extra fields, which will be constrained by `@allow_extension_fields`

    @model_validator(mode="after")
    def validate_extension_prefixes(self):
        """Validate that extra fields use allowed prefixes."""
        if hasattr(self, "__pydantic_extra__") and self.__pydantic_extra__:
            for field_name in self.__pydantic_extra__.keys():
                if not field_name.startswith("ext_"):
                    raise ValueError(
                        f"Unrecognized field '{field_name}' must use ext_ prefix"
                    )
        return self


class OvertureFeature(ExtensibleBaseModel, ABC):
    """Base class for all Overture features."""

    id: str = Field(..., min_length=1, description="Feature identifier")
    theme: str = Field(..., description="Top-level Overture theme")
    type: str = Field(..., description="Specific feature type within theme")
    geometry: Geometry = Field(..., description="Geometry")
    sources: list[SourceItem] = Field(default=None, description="Source information")
    version: int = Field(..., ge=0, description="Feature version number")

    @model_serializer(mode="wrap")
    def serialize_model(self, serializer, info):
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
