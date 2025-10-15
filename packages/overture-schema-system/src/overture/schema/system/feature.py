from typing import Any

from pydantic import (
    BaseModel,
    Field,
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
    """
    A feature is something you can point to on a map—like a building, road, lake, or park—with the
    facts about that thing.

    Every feature has a geometry that describes where it is and what it looks like. In addition, a
    feature may have an `id` field that uniquely identifies it. It may also have a bounding box,
    which is a simplified geometry that facilitates efficient spatial operations.

    Derive a subclass of `Feature` to add new fields with facts about your feature type.

    >>> from typing  import Annotated
    >>> from pydantic import Field
    >>> from overture.schema.system.primitive import Geometry, float32
    ...
    >>> class Mountain(Feature):
    ...     name: str
    ...     max_elevation: Annotated[
    ...         float32 ,
    ...         Field(description='Maximum elevation above sea level in meters')
    ...     ]
    ...
    >>> mount_everest = Mountain(
    ...     geometry=Geometry.from_wkt('POINT(86.9252 27.9888)'),
    ...     name='Mount Everest',
    ...     max_elevation=8_848.86
    ... )

    A feature has a special JSON representation that conforms to the `GeoJSON format`_
    specification.

    >>> print(mount_everest.model_dump_json(indent=2))
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [
          86.9252,
          27.9888
        ]
      },
      "properties": {
        "name": "Mount Everest",
        "max_elevation": 8848.86
      }
    }

    Use a geometry type constraint to limit the geometry types allowed on your feature subclass.
    This can help maximize validation and data integrity by preventing geometries that do not make
    sense from being stored.

    >>> from overture.schema.system.primitive import GeometryType, GeometryTypeConstraint
    ...
    >>> class River(Feature):
    ...     geometry: Annotated[
    ...         Geometry,
    ...         GeometryTypeConstraint(GeometryType.LINE_STRING)
    ...     ]

    .. _GeoJSON format: https://datatracker.ietf.org/doc/html/rfc7946
    """

    id: Omitable[Id] = Field(description="An optional unique ID for the feature")
    """An optional unique ID for the feature."""

    bbox: Omitable[BBox] = Field(description="An optional bounding box for the feature")
    """An optional bounding box for the feature."""

    geometry: Geometry = Field(description="The feature's geometry")
    """
    The feature's geometry.

    Subclasses of `Feature` may limit the geometry types allowed on `geometry` by repeating this
    field and annotating it with a `GeometryTypeConstraint`.
    """

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

            def validation_error(
                type: str, input: object, error: str, *loc: str
            ) -> ValidationError:
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
                    ],
                )

            def type_property_error(
                type: str, input: object, problem: str
            ) -> ValidationError:
                return validation_error(
                    type,
                    input,
                    f"{problem} feature JSON (it should have value 'Feature')",
                    "type",
                )

            def properties_property_type_error(
                type: str, input: object, prefix: str, suffix: str, *loc: str
            ) -> ValidationError:
                return validation_error(
                    type,
                    input,
                    f"{prefix} feature JSON (it must be a `dict` or an explicitly preset `None` value){suffix}",
                    "properties",
                )

            # GeoJSON features require `type=Feature` at the top level. Note that this validation
            # *could* be done as a `Literal["Feature"]` field, but that approach would have two
            # shortcomings. First (minor), it would force the non-JSON Python representation to
            # have the "type" field. Second (major) it would make it trickier for the perfectly
            # valid use case of a property under "properties" named "type", since our approach to
            # "properties" is to lift them up into the root level object before calling the
            # provided handler. Lifting up an inner "type" variable would overwrite the outer "type"
            # and cause a validation failure.
            try:
                t = data.pop("type")
            except KeyError:
                raise type_property_error(
                    "missing", None, "'type' property is missing from"
                ) from None
            if t != "Feature":
                raise type_property_error(
                    "value_error", t, f"'type' property has wrong value {repr(t)} in"
                )

            # Remove the properties sub-dictionary so we can flatten it.
            try:
                properties = data.pop("properties")
            except KeyError:
                raise properties_property_type_error(
                    "missing", None, "'properties' property is missing from", ""
                ) from None
            if not isinstance(properties, dict | None):
                raise properties_property_type_error(
                    "value_error",
                    None,
                    "'properties' property has wrong type in",
                    f", but {repr(properties)} is a `{type(properties).__name__}`",
                )

            # Ensure there's nothing in data root level that repeats a valid model field.
            conflicts = [
                f
                for f in data.keys()
                if f not in {"id", "bbox", "geometry", "properties"}
            ]
            if conflicts:
                raise validation_error(
                    "value_error",
                    properties,
                    f"illegal top-level properties in feature JSON: {repr(conflicts)} (these properties may only be children of the 'properties' object)",
                )

            if properties:
                # Check for field conflicts within the 'properties' sub-dictionary.
                conflicts = [
                    f for f in properties.keys() if f in {"id", "bbox", "geometry"}
                ]
                if conflicts:
                    raise validation_error(
                        "value_error",
                        properties,
                        f"illegal properties in feature JSON: {repr(conflicts)} (these properties may only appear at the top level, but they are in the 'properties' object)",
                        "properties",
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
