"""
Geospatial feature model with GeoJSON-compatible JSON Schema.
"""

import inspect
from enum import Enum
from functools import reduce
from typing import Any

from pydantic import (
    BaseModel,
    Discriminator,
    Field,
    GetJsonSchemaHandler,
    ModelWrapValidatorHandler,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    ValidationError,
    ValidationInfo,
    model_serializer,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue, JsonValue
from pydantic_core import InitErrorDetails, core_schema
from typing_extensions import Self

from overture.schema.system import _json_schema
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

    To add new fields with facts about your own feature type, derive a subclass of `Feature`:

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

    To limit the geometry types allowed on your feature subclass, use a geometry type constraint.
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

    Because the GeoJSON format moves feature fields to a place Pydantic does not expect them (the
    `"properties"` block of the JSON object), a naive use of Pydantic discriminated unions will not
    work when deserializing from JSON with `model_validate_json`. To create a robust discriminated
    union, use the `field_discriminator` method:

    >>> from typing import Annotated, Literal
    >>> from overture.schema.system.primitive import float32
    >>> import pydantic
    >>>
    >>> class Field(Feature):
    ...     geometry: Annotated[
    ...         Geometry,
    ...         GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON)
    ...     ]
    ...     type: Literal['field']
    ...
    >>> class Fence(Feature):
    ...     geometry: Annotated[
    ...         Geometry,
    ...         GeometryTypeConstraint(GeometryType.LINE_STRING)
    ...     ]
    ...     type: Literal['fence']
    ...     subtype: Literal[
    ...         'chain_link', 'barb_wire_3', 'barb_wire_4', 'barb_wire_5', 'electric_1',
    ...         'electric_2', 'electric_3', 'electric_4', 'split_rail', 'woven_wire'
    ...     ]
    ...     height: float32 | None = pydantic.Field(
    ...         default=None,
    ...         description='Optional fence height in meters'
    ...     )
    ...
    >>> FarmFeature = pydantic.TypeAdapter(
    ...     Annotated[
    ...         Annotated[Field, pydantic.Tag('field')]
    ...             | Annotated[Fence, pydantic.Tag('fence')],
    ...         pydantic.Field(
    ...            discriminator=Feature.field_discriminator('type', Field, Fence)
    ...         ),
    ...    ]
    ... )
    >>>
    >>> FarmFeature.validate_json('''{
    ...     "type": "Feature",
    ...     "geometry": {
    ...         "type": "LineString",
    ...         "coordinates": [[0, 0], [0, 0.01]]
    ...     },
    ...     "properties": {
    ...         "type": "fence",
    ...         "subtype": "barb_wire_4"
    ...     }
    ... }''')
    Fence(id=<MISSING>, bbox=<MISSING>, geometry=<<LINESTRING (0 0, 0 0.01)>>, type='fence', subtype='barb_wire_4', height=None)

    You can model classes that are not `Feature` subclasses in `field_discriminator` to enable
    discriminated unions between features and non-features, as long as at least one model class is
    a `Feature`:

    >>> class Farmer(BaseModel):
    ...     type: Literal['farmer']
    ...     name: str
    ...
    >>> FarmModel = pydantic.TypeAdapter(
    ...     Annotated[
    ...         Annotated[Farmer, pydantic.Tag('farmer')]
    ...             | Annotated[Field, pydantic.Tag('field')]
    ...             | Annotated[Fence, pydantic.Tag('fence')],
    ...         pydantic.Field(
    ...             discriminator=Feature.field_discriminator('type', Field, Fence)
    ...         ),
    ...    ]
    ... )
    >>>
    >>> FarmModel.validate_json('{"type":"farmer","name":"John Deere"}')
    Farmer(type='farmer', name='John Deere')
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

    @staticmethod
    def field_discriminator(
        field: str, *model_classes: type[BaseModel]
    ) -> Discriminator:
        """
        Return a discriminator that can be used in a Pydantic `Field` to support tagged unions of
        features.

        Use this method to generate a Pydantic discriminator that works *both* with Python-style
        flat data *and* GeoJSON. Note that at least one member of `model_classes` must be a
        `Feature` (if no feature models are involved, you don't need this method and should build
        your discriminated union using Pydantic's standard discriminator facilities).

        Parameters
        ----------
        field : str
            Field name, which must be present in all models
        *model_classes : type[BaseModel]
            One or more Pydantic model classes, at least one of which must be a subclass of the
            `Feature` class

        Returns
        -------
        Discriminator
            Discriminator that enables discriminated unions that include features

        Raises
        ------
        TypeError
            If any member of `model_classes` is not a subclass of `BaseModel`.
        TypeError
            If no member of `model_classes` is a subclass of `Feature`.
        TypeError
            If any member of `model_classes` does not have a field named `field`.
        ValueError
            If `field` names one of the core GeoJSON feature fields that cannot be discriminated:
            `"bbox"`, `"geometry`", or `"id"`.
        ValueError
            If `model_classes` has length less than 2.
        """
        if not isinstance(field, str):
            raise TypeError(
                f"`field` must be a `str`, but {repr(field)} has type `{type(field).__name__}`"
            )
        elif field in ["bbox", "geometry", "id"]:
            raise ValueError(
                f"`field` value {repr(field)} is not allowed because it is one of the core GeoJSON "
                "feature properties: 'bbox', 'geometry', and 'id' - use a different discriminator "
                "field!"
            )
        elif len(model_classes) < 2:
            raise ValueError(
                f"`model_classes` must have at least two items, but {repr(model_classes)} has length {len(model_classes)}"
            )

        non_models = [
            x
            for x in model_classes
            if not isinstance(x, type) or not issubclass(x, BaseModel)
        ]
        if non_models:
            raise TypeError(
                "`model_classes` contains at least one non-model class: the value(s) "
                f"{repr(non_models)} should be subclasses of {BaseModel.__name__} but the type(s) "
                f"are {', '.join([f'`{x.__name__ if isinstance(x, type) else type(x).__name__}`' for x in non_models])}, "
                f"respectively, which are not subclasses of `{BaseModel.__name__}`..."
            )

        missing_field = [
            f"`{t.__name__}`" for t in model_classes if field not in t.model_fields
        ]
        if missing_field:
            raise TypeError(
                "`model_classes` contains at least one model class that does not have a field "
                f"named {repr(field)}: {', '.join(missing_field)}"
            )

        if not any(t for t in model_classes if issubclass(t, Feature)):
            frame = inspect.currentframe()
            method_name = (
                f"{Feature.__name__}.{frame.f_code.co_name if frame else '???'}"
            )
            raise TypeError(
                f"`model_classes` does not contain any subclasses of `{Feature.__name__}` - "
                f"you don't need `{method_name}(...)` unless you have at least one "
                f"`{Feature.__name__}` model - use standard Pydantic discriminators instead"
            )

        def get_discriminator_value(data: object) -> Any:
            # Pydantic doesn't have a facility to tell the dynamic discriminator function whether
            # the context is 'python' or 'json', so we just have to use heuristics. If the input is
            # a `dict` with the mandatory attributes `"type": "Feature"`, `"geometry"`, and
            # `"properties"`, we assume we're in GeoJSON-land, otherwise not.
            #
            # If the data doesn't contain the discriminator field at all, we return `None` to tell
            # Pydantic proceed to try the next variant in the union, if there is one. This is
            # equivalent to how Pydantic behaves with static unions.
            if (
                isinstance(data, dict)
                and all(f in data for f in ["geometry", "properties", "type"])
                and data["type"] == "Feature"
            ):
                properties: Any = data["properties"]
                if not isinstance(properties, dict):
                    return None
                else:
                    return properties.get(field, None)
            else:
                return (
                    data.get(field, None)
                    if isinstance(data, dict)
                    else getattr(data, field, None)
                )

        return Discriminator(get_discriminator_value)

    @model_serializer(mode="wrap")
    def __serialize_with_geo_json_support__(
        self, serializer: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> Any:
        """
        Serialize to GeoJSON when the mode is JSON, otherwise to Pydantic's standard Python mode.
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
    def __validate_with_geo_json_support__(
        cls, data: Any, handler: ModelWrapValidatorHandler[Self], info: ValidationInfo
    ) -> Self:
        """
        Validate the model as GeoJSON when the mode is JSON, otherwise applies Pydantic's standard
        validation.
        """
        if info.mode == "json":
            if not isinstance(data, dict):
                raise TypeError(
                    f"feature data must be a `dict` when validating JSON, but {repr(data)} is a `{type(data).__name__}`"
                )

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
        cls: type["Feature"],
        schema: core_schema.CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """
        Generate a JSON Schema that validates the feature as GeoJSON.
        """
        json_schema = handler(schema)

        top_level_required = json_schema.get("required", [])
        top_level_properties = json_schema["properties"]

        # Determine if the schema allows any additional properties apart from the three basic ones,
        # "id", "bbox", and "geometry".
        may_have_properties = (
            any(
                f
                for f in cls.model_fields.keys()
                if f not in ["id", "bbox", "geometry"]
            )
            or cls.model_config.get("extra", None) != "forbid"
        )

        # Migrate any top-level properties that aren't part of the three basic ones, "id", "bbox",
        # and "geometry", down into the GeoJSON feature's "properties" object.
        if may_have_properties:
            properties_object_properties = {}
            properties_object_required = []
            for name in list(top_level_properties.keys()):
                if name not in ["id", "bbox", "geometry"]:
                    properties_object_properties[name] = top_level_properties.pop(name)
                    if name in top_level_required:
                        top_level_required.remove(name)
                        properties_object_required.append(name)

        # Add `type=Feature` at the top level.
        top_level_properties["type"] = {
            "type": "string",
            "const": "Feature",
        }
        top_level_required.insert(0, "type")

        # If additional properties may be allowed, we have to factor the schema to ensure that all
        # properties apart from the basic ones are homed in the Feature object's "properties"
        # sub-object.
        if may_have_properties:
            # Start the schema for the properties sub-object. Ensure the three basic properties,
            # "id", "bbox", and "geometry", cannot appear in the properties sub-object.
            properties_object_schema = {
                "type": "object",
                **(
                    {"required": properties_object_required}
                    if properties_object_required
                    else {}
                ),
                "not": {"required": ["id", "bbox", "geometry"]},
                **(
                    {"properties": properties_object_properties}
                    if properties_object_properties
                    else {}
                ),
            }

            # Preserve simple constraints from the original schema by migrating them down into the
            # 'properties' sub-schema.
            for key in [
                "additionalProperties",
                "unevaluatedProperties",
                "patternProperties",
            ]:
                if key in json_schema:
                    properties_object_schema[key] = json_schema.pop(key)

            # Migrate the remaining sub-schemas into the properties sub-object.
            #
            # More complex constraints may require factoring the constraint using "JSON Schema
            # algebra" if the constraint mixes he three top-level fields ("id", etc.) with fields
            # that belong in the properties sub-object.
            for key in [
                "allOf",
                "anyOf",
                "oneOf",
                "not",
                "minProperties",
                "maxProperties",
            ]:
                if key in json_schema:
                    _maybe_refactor_schema(
                        cls,
                        {key: json_schema.pop(key)},
                        json_schema,
                        properties_object_schema,
                    )
            if_then_else: JsonSchemaValue = {}
            _json_schema.try_move("if", json_schema, if_then_else)
            _json_schema.try_move("then", json_schema, if_then_else)
            _json_schema.try_move("else", json_schema, if_then_else)
            if if_then_else:
                _maybe_refactor_schema(
                    cls, if_then_else, json_schema, properties_object_schema
                )

            # Determine if the properties object is allowed to be null or not. We only allow null
            # if there are no explicitly required fields. Note that even if we allow null here, it
            # might be blocked by conditional schemas, for example if a field is conditionally
            # required.
            may_null_properties = len(properties_object_schema.get("required", [])) == 0
            if may_null_properties:
                properties_object_schema = {
                    "anyOf": [
                        properties_object_schema,
                        {"type": "null"},
                    ]
                }
        else:
            properties_object_schema = {
                "anyOf": [
                    {
                        "type": "object",
                        "maxProperties": 0,
                    },
                    {"type": "null"},
                ]
            }

        # Insert the Feature's properties sub-object schema into the top-level object properties.
        top_level_properties["properties"] = properties_object_schema

        # Make the properties sub-object required, consistent with the GeoJSON format spec.
        top_level_required.append("properties")

        # Store the top-level required schema. This may be empty, because subclasses of Feature can
        # technically eliminate the mandatoriness of the basic fields by redefining them.
        if top_level_required:
            json_schema["required"] = top_level_required

        # Do not allow any extra properties in the root JSON object: we want to restrict it only to
        # the core GeoJSON properties. Any extra fields, if they are allowed by the Pydantic model,
        # are allowed within the 'properties' sub-object.
        json_schema["additionalProperties"] = False

        # Return the completed GeoJSON-flavored JSON Schema.
        return json_schema


class _FieldLevel(str, Enum):
    UNKNOWN = "unknown"
    MIXED = "mixed"
    PROPERTIES_OBJECT = "properties"
    TOP_LEVEL_OBJECT = "top_level"

    @staticmethod
    def classify(
        cls: type[Feature],
        value: JsonValue,
        in_object_properties: bool = False,
        *loc: int | str,
    ) -> "_FieldLevel":
        if isinstance(value, list | tuple):
            return reduce(
                lambda acc, x: _FieldLevel.combine(acc, x),
                [
                    _FieldLevel.classify(cls, v, in_object_properties, *loc, i)
                    for i, v in enumerate(value)
                ],
                _FieldLevel.UNKNOWN,
            )
        elif isinstance(value, str):
            return (
                _FieldLevel.TOP_LEVEL_OBJECT
                if value in ["id", "bbox", "geometry"]
                else _FieldLevel.PROPERTIES_OBJECT
            )
        elif not isinstance(value, dict):
            return _FieldLevel.UNKNOWN
        else:
            field_level = _FieldLevel.UNKNOWN
            for k, v in value.items():
                if k.startswith("$") or k in {
                    "default",
                    "deprecated",
                    "description",
                    "examples",
                    "readOnly",
                    "writeOnly",
                    "title",
                }:
                    continue
                elif in_object_properties:
                    new_level = _FieldLevel.classify(cls, k, True, *loc, k)
                elif k in ["minProperties", "maxProperties"]:
                    raise ValueError(
                        f"unsupported JSON Schema keyword {repr(k)} at path {repr(loc)}: the keyword cannot be used at the top level of the `{cls.__name__}` schema"
                    )
                elif k in {
                    "allOf",
                    "anyOf",
                    "oneOf",
                    "not",
                    "if",
                    "then",
                    "else",
                    "required",
                }:
                    new_level = _FieldLevel.classify(
                        cls, v, in_object_properties, *loc, k
                    )
                elif k == "properties":
                    new_level = _FieldLevel.classify(cls, v, True, *loc, "properties")
                else:
                    new_level = _FieldLevel.UNKNOWN
                field_level = _FieldLevel.combine(field_level, new_level)
                if field_level == _FieldLevel.MIXED:
                    break
            return field_level

    @staticmethod
    def combine(a: "_FieldLevel", b: "_FieldLevel") -> "_FieldLevel":
        if a == b:
            return a
        elif a == _FieldLevel.UNKNOWN:
            return b
        elif b == _FieldLevel.UNKNOWN:
            return a
        else:
            return _FieldLevel.MIXED


def _maybe_refactor_schema(
    cls: type[Feature],
    sub_schema: JsonSchemaValue,
    top_level_schema: JsonSchemaValue,
    properties_object_schema: JsonSchemaValue,
) -> None:
    field_level = _FieldLevel.classify(cls, sub_schema)

    if field_level == _FieldLevel.PROPERTIES_OBJECT:
        _merge_schemas(properties_object_schema, sub_schema)
    elif field_level != _FieldLevel.MIXED:
        # This is safe because it was taken out of the top level and we are just putting it back now.
        top_level_schema |= sub_schema
    else:
        _refactor_schema(sub_schema)
        _merge_schemas(top_level_schema, sub_schema)


def _refactor_schema(schema: JsonSchemaValue) -> None:
    for k, v in list(schema.items()):
        if k == "properties":
            _refactor_properties(schema)
        elif k == "required":
            _refactor_required(schema)
        elif isinstance(v, dict):
            _refactor_schema(v)
        elif isinstance(v, list):
            for item in v:
                _refactor_schema(item)


def _refactor_properties(schema: JsonSchemaValue) -> None:
    properties = schema["properties"]

    lower_properties = {}
    for k, v in list(properties.items()):
        if k not in ["id", "bbox", "geometry"]:
            lower_properties[k] = v
            del properties[k]

    if len(lower_properties) > 0:
        try:
            properties_object_schema = properties["properties"]
        except KeyError:
            properties_object_schema = {"type": "object"}
            properties["properties"] = properties_object_schema
        _json_schema.put_properties(properties_object_schema, lower_properties)


def _refactor_required(schema: JsonSchemaValue) -> None:
    required = schema.pop("required")

    upper_required = [p for p in required if p in ["id", "bbox", "geometry"]]
    if len(upper_required) > 0:
        schema["required"] = upper_required

    if len(upper_required) < len(required):
        schema_properties = schema.get("properties", {})
        properties_schema = schema_properties.get(
            "properties",
            {
                "type": "object",
            },
        )
        properties_schema["required"] = [
            p for p in required if p not in {"id", "bbox", "geometry"}
        ]
        schema_properties["properties"] = properties_schema
        schema["properties"] = schema_properties


def _merge_schemas(
    target_schema: JsonSchemaValue, source_schema: JsonSchemaValue
) -> None:
    if_then_else: JsonSchemaValue = {}
    _json_schema.try_move("if", source_schema, if_then_else)
    _json_schema.try_move("then", source_schema, if_then_else)
    _json_schema.try_move("else", source_schema, if_then_else)
    if if_then_else:
        _json_schema.put_if(
            target_schema,
            if_then_else.get("if", None),
            if_then_else.get("then", None),
            if_then_else.get("else", None),
        )

    table = {
        "allOf": lambda json_schema, operand: _json_schema.put_all_of(
            json_schema, operand
        ),
        "anyOf": lambda json_schema, operand: _json_schema.put_any_of(
            json_schema, operand
        ),
        "oneOf": lambda json_schema, operand: _json_schema.put_one_of(
            json_schema, operand
        ),
        "not": lambda json_schema, operand: _json_schema.put_not(json_schema, operand),
        "required": lambda json_schema, operand: _json_schema.put_required(
            json_schema, operand
        ),
        "properties": lambda json_schema, operand: _json_schema.put_properties(
            json_schema, operand
        ),
    }

    for k, v in source_schema.items():
        try:
            f = table[k]
        except KeyError as e:
            raise RuntimeError(f"no schema merge mapping for key {repr(k)}") from e
        f(target_schema, v)
