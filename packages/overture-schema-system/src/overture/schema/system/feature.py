from typing import Any, Literal

from pydantic import (
    BaseModel,
    GetJsonSchemaHandler,
    ModelWrapValidatorHandler,
    SerializerFunctionWrapHandler,
    ValidationError,
    ValidationInfo,
    model_serializer,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import InitErrorDetails, core_schema
from typing_extensions import Self

from overture.schema.system._json_schema import put_not
from overture.schema.system.optionality import Omitable
from overture.schema.system.primitive import BBox, Geometry
from overture.schema.system.ref import Id


class Feature(BaseModel):
    type: Literal["Feature"]
    id: Omitable[Id]
    bbox: Omitable[BBox]
    geometry: Geometry

    @model_serializer(mode="wrap")
    def serialize_model(
        self, serializer: SerializerFunctionWrapHandler, info: ValidationInfo
    ) -> dict[str, object]:
        """
        Serializes to GeoJSON when the mode is JSON, otherwise to Pydantic's standard Python mode.
        """
        data = serializer(self)

        if info.mode == "json":
            return {
                "type": "Feature",
                **({"id": data.pop("id")} if "id" in data else {}),
                **({"bbox": data.pop("bbox")} if "bbox" in data else {}),
                "geometry": data.pop("geometry"),
                "properties": data,
            }

        return data

    @model_validator(mode="wrap")
    @classmethod
    def validate_model(
        cls, data: Any, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo
    ) -> Self:
        """
        Validates the model as GeoJSON when the mode is JSON, otherwise applies Pydantic's standard
        validation.
        """
        if not isinstance(data, dict):
            raise TypeError(
                f"feature data must be a `dict`, but {repr(data)} is a `{type(data).__name__}`"
            )

        if info.mode == "json":
            def validation_error(type: str, input: object, error: str, *loc: str) -> ValidationError:
                context = info.context or {}
                loc = context.get("loc_prefix", ()) + loc
                return ValidationError.from_exception_data(
                    title=cls.__name__,
                    line_errors=[
                        InitErrorDetails(
                            type=type,
                            loc=loc,
                            input=input,
                            ctx={"error": error},
                        )
                    ]
                )

            def type_property_error(input: object, problem: str) -> ValidationError:
                return validation_error('geo_json_type', input, f"{problem} (it should have value 'Feature')", "type")

            def properties_property_error(input: object, problem: str) -> ValidationError:


            # GeoJSON features require `type=Feature` at the top level.
            try:
                t = data.pop("type")
            except KeyError:
                raise type_property_error(None, "'type' property is missing") from None
            if t != "Feature":
                raise type_property_error(t, f"'type' property has a wrong value, {repr(t)}")

            # Remove the properties sub-dictionary so we can flatten it.
            try:
                properties = data.pop("properties")
            except KeyError:
                properties = None
            if not isinstance(properties, dict | None):
                raise TypeError(
                    f"'properties' key in feature JSON must be a `dict`, but {repr(properties)} is a `{type(properties).__name__}"
                )

            # Ensure there's nothing in data root level that repeats a valid model field.
            conflicts = [
                f
                for f in data.keys()
                if f not in {"id", "bbox", "geometry", "properties"}
            ]
            if conflicts:
                raise ValueError(
                    "illegal root-level properties in feature JSON: these properties may only be children of the 'properties' object: {repr(conflicts)}"
                )

            if properties:
                # Check for field conflicts within the 'properties' sub-dictionary.
                conflicts = [
                    f for f in properties.keys() if f in {"id", "bbox", "geometry"}
                ]
                if conflicts:
                    raise ValueError(
                        "illegal properties in feature JSON: these properties may only appear in the root, but they are in the 'properties' object: {repr(conficts)}"
                    )

                # Spread the 'properties' sub-dictionary across the root-level data object.
                data |= properties

        return handler(data)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """
        Generates a JSON Schema that validates the feature as GeoJSON.
        """
        json_schema = super().__get_pydantic_json_schema__(core_schema, handler)

        # Move all non-GeoJSON properties down into the GeoJSON 'properties' object.
        try:
            json_schema_top_level_required = json_schema["required"]
        except KeyError:
            json_schema_top_level_required = []
            json_schema["required"] = json_schema_top_level_required
        json_schema_top_level_properties = json_schema["properties"]
        geo_json_properties = {}
        geo_json_required = []

        for name in json_schema_top_level_properties.keys():
            if name not in ["id", "bbox", "geometry"]:
                value = json_schema_top_level_properties[name]
                geo_json_properties[name] = value
                del json_schema_top_level_properties[name]
                if name in json_schema_top_level_required:
                    json_schema_top_level_required.remove(name)
                    geo_json_required.append(name)

        # Create the sub-schema for the GeoJSON 'properties' sub-object.
        geo_json_properties_schema = {
            "type": "object",
            "properties": geo_json_properties,
            **({"required": geo_json_required} if geo_json_required else {}),
        }

        # Preserve the relevant constraints from the original schema by migrating them into the
        # 'properties' sub-schema.
        for key in [
            "anyOf",
            "allOf",
            "oneOf",
            "not",
            "additionalProperteis",
            "unevaluatedProperties",
            "patternProperties",
        ]:
            try:
                geo_json_properties_schema[key] = json_schema.pop(key)
            except KeyError:
                pass

        # Prohibit the core top-level properties from being replicated in the 'properties'
        # sub-object.
        put_not(geo_json_properties_schema, {"required": ["id", "bbox", "geometry"]})

        # Insert the sub-schema for the 'properties' sub-object. If 'properties' has no required
        # members then we allow it to be `null` in conformance with the GeoJSON specification.
        # Otherwise, it must be an object.
        if geo_json_required:
            json_schema_top_level_properties["properties"] = geo_json_properties_schema
        else:
            json_schema_top_level_properties["properties"] = {
                "anyOf": {
                    geo_json_properties_schema,
                    {"type": "null"},
                }
            }
        json_schema_top_level_required.append("properties")

        # Add `type=Feature` at the top level.
        json_schema_top_level_properties["type"] = {
            "type": "string",
            "const": "Feature",
        }
        json_schema_top_level_required.append("type")

        # Do not allow any extra properties in the root JSON object: we want to restrict it only to
        # the core GeoJSON properties. Any extra fields, if they are allowed by the Pydantic model,
        # are allowed within the 'properties' sub-object.
        json_schema["additionalProperties"] = False

        # Return the completed GeoJSON-flavored JSON Schema.
        return json_schema
