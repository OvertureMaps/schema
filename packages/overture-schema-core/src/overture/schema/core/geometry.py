from enum import Enum
from typing import Any

from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    ValidationError,
    ValidationInfo,
)
from pydantic_core import InitErrorDetails, core_schema
from shapely import wkb, wkt
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry


class GeometryType(Enum):
    GEOMETRY_COLLECTION = 0, "GeometryCollection"
    LINE_STRING = 1, "LineString"
    POINT = 2, "Point"
    POLYGON = 3, "Polygon"
    MULTI_LINE_STRING = 4, "MultiLineString"
    MULTI_POINT = 5, "MultiPoint"
    MULTI_POLYGON = 6, "MultiPolygon"

    def __init__(self, value: int, geo_json_type: str) -> None:
        self._value = value
        self._geo_json_type = geo_json_type

    def __lt__(self, other: "GeometryType") -> bool:
        if not isinstance(other, GeometryType):
            return NotImplemented
        return self._value < other._value

    @property
    def geo_json_type(self) -> str:
        return self._geo_json_type


_GEOMETRY_GEO_JSON_TYPES = [item.geo_json_type for item in GeometryType]

_GEOMETRY_TYPE_REVERSE_LOOKUP = {item.geo_json_type: item for item in GeometryType}


class GeometryTypeConstraint:
    def __init__(self, *allowed_types: GeometryType) -> None:
        self.__allowed_types = self.__class__._validate_geometry_types(
            list(allowed_types)
        )

    @property
    def allowed_types(self) -> tuple[GeometryType, ...]:
        return self.__allowed_types

    def validate(self, value: "Geometry", info: ValidationInfo) -> "Geometry":
        try:
            geometry_type: GeometryType = _GEOMETRY_TYPE_REVERSE_LOOKUP[
                value.geom.geom_type
            ]
        except KeyError as e:
            raise RuntimeError(
                f"inter `geom` has unknown type: {repr(value.geom.geom_type)}"
            ) from e
        if geometry_type not in self.allowed_types:
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={
                            "error": f"geometry type not allowed: {repr(geometry_type)} (allowed values: {repr(self.allowed_types)})"
                        },
                    )
                ],
            )
        return value

    @classmethod
    def _validate_geometry_types(
        cls, a: list[GeometryType]
    ) -> tuple[GeometryType, ...]:
        if not a:
            raise ValueError(
                f"allowed_types is empty (it must contain at least one: {type(GeometryType).__name__})"
            )

        if not all(isinstance(item, GeometryType) for item in a):
            invalid = [item for item in a if not isinstance(item, GeometryType)]
            raise ValueError(
                f"allowed_types contains invalid value{'s' if len(invalid) > 1 else ''}: {invalid} (allowed: {list(GeometryType)})"
            )

        if len(set(a)) != len(a):
            raise ValueError("allowed_types contains duplicate(s)")

        return tuple(sorted(a))

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        if not issubclass(source, Geometry):
            raise TypeError(
                f"{GeometryTypeConstraint.__name__} can only be applied to {Geometry.__name__}; but it was applied to {source.__name__}"
            )
        schema = handler(source)
        return core_schema.with_info_after_validator_function(self.validate, schema)

    def __get_pydantic_json_schema__(
        self, source: type[Any], handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        if len(self.allowed_types) == 1:
            return _GEOMETRY_JSON_SCHEMA[self.allowed_types[0]]
        else:
            allowed_schemas = [_GEOMETRY_JSON_SCHEMA[x] for x in self.allowed_types]
            return {
                "oneOf": allowed_schemas,
            }


_ALL_GEOMETRY_ALLOWED = GeometryTypeConstraint(*GeometryType)


class Geometry:
    geom: BaseGeometry

    def __init__(self, geom: BaseGeometry) -> None:
        self.geom = geom

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Geometry) and self.geom == other.geom

    def __hash__(self) -> int:
        return hash(self.geom)

    def __repr__(self) -> str:
        return f"<{repr(self.geom)}>"

    def __str__(self) -> str:
        return self.wkt

    @property
    def wkt(self) -> str:
        return self.geom.wkt

    def to_geo_json(self) -> dict[str, Any]:
        return mapping(self.geom)

    @classmethod
    def from_geo_json(cls, value: dict[str, Any] | BaseGeometry) -> "Geometry":
        # If it's already a Shapely geometry, use it directly
        if isinstance(
            value, BaseGeometry
        ):  # FIXME: For consistency, this probably should move to a separate `from_shapely()` method.
            return cls(value)

        if not isinstance(value, dict):
            raise TypeError(
                f"value must be a dict; but {repr(value)} has type {type(value).__name__}"
            )

        type_ = value.get("type")

        if type_ not in _GEOMETRY_GEO_JSON_TYPES:
            raise ValueError(
                f"allowed_types contains invalid value {repr(type_)} (allowed: {_GEOMETRY_GEO_JSON_TYPES})"
            )

        return cls(shape(value))

    @classmethod
    def from_wkb(cls, value: bytes) -> "Geometry":
        """Create a Geometry from Well-Known Binary (WKB) bytes."""
        if not isinstance(value, bytes):
            raise TypeError(
                f"value must be bytes; but {repr(value)} has type {type(value).__name__}"
            )

        try:
            geom = wkb.loads(value)
            return cls(geom)
        except Exception as e:
            raise ValueError(f"invalid WKB data: {str(e)}") from e

    @classmethod
    def from_wkt(cls, value: str) -> "Geometry":
        """Create a Geometry from Well-Known Text (WKT) string."""
        if not isinstance(value, str):
            raise TypeError(
                f"value must be str; but {repr(value)} has type {type(value).__name__}"
            )

        try:
            geom = wkt.loads(value)
            return cls(geom)
        except Exception as e:
            raise ValueError(f"invalid WKT string: {str(e)}") from e

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: type[Any], _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validator(
            value: dict[str, Any] | BaseGeometry | bytes | str | Geometry,
            info: ValidationInfo,
        ) -> Geometry:
            try:
                # Handle Shapely geometry directly
                if isinstance(value, BaseGeometry):
                    return cls(value)
                # Handle GeoJSON dict
                elif isinstance(value, dict):
                    return cls.from_geo_json(value)
                # Handle WKB bytes
                elif isinstance(value, bytes):
                    return cls.from_wkb(value)
                # Handle WKT string
                elif isinstance(value, str):
                    return cls.from_wkt(value)
                else:
                    raise TypeError(
                        f"Expected dict, BaseGeometry, bytes, str, or Geometry, got {type(value).__name__}"
                    )
            except Exception as e:
                context = info.context or {}
                loc = context.get("loc_prefix", ()) + ("value",)
                raise ValidationError.from_exception_data(
                    title=cls.__name__,
                    line_errors=[
                        InitErrorDetails(
                            type="value_error",
                            loc=loc,
                            input=value,
                            ctx={"error": f"invalid geometry value: {str(e)}"},
                        )
                    ],
                ) from e

        def serialize_geometry(
            v: "Geometry", info: ValidationInfo | None
        ) -> "dict[str, Any] | 'Geometry'":
            if info and info.mode == "json":
                return v.to_geo_json()
            return v

        return core_schema.with_info_plain_validator_function(
            validator,
            serialization=core_schema.plain_serializer_function_ser_schema(
                serialize_geometry, info_arg=True
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        return _ALL_GEOMETRY_ALLOWED.__get_pydantic_json_schema__(cls, handler)


########################################################################
# JSON Schema primitives for GeoJSON geometry
########################################################################

_BBOX_JSON_SCHEMA = {
    "type": "array",
    "minItems": 4,
    "items": {
        "type": "number",
    },
}

_POINT_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 2,
    "items": {
        "type": "number",
    },
}

########################################################################
# JSON Schema for GeoJSON geometry `coordinates`
########################################################################

_LINE_STRING_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 2,
    "items": _POINT_COORDINATES_JSON_SCHEMA,
}

_MULTI_LINE_STRING_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": _LINE_STRING_COORDINATES_JSON_SCHEMA,
}

_MULTI_POINT_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": _POINT_COORDINATES_JSON_SCHEMA,
}

_LINEAR_RING_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 4,
    "items": _POINT_COORDINATES_JSON_SCHEMA,
}

_POLYGON_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": _LINEAR_RING_COORDINATES_JSON_SCHEMA,
}

_MULTI_POLYGON_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": _POLYGON_COORDINATES_JSON_SCHEMA,
}

########################################################################
# JSON Schema for GeoJSON geometry types
########################################################################


def geometry_json_schema(
    geometry_type: str,
    coordinates: dict[str, Any] | None = None,
    geometries: dict[str, Any] | None = None,
) -> dict[str, Any]:
    properties = {
        "type": {
            "type": "string",
            "const": geometry_type,
        },
        "bbox": _BBOX_JSON_SCHEMA,
    }
    required = ["type"]
    if coordinates:
        required.append("coordinates")
        properties["coordinates"] = coordinates
    if geometries:
        required.append("geometries")
        properties["geometries"] = geometries
    return {
        "type": "object",
        "required": required,
        "properties": properties,
    }


_LINE_STRING_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "LineString", coordinates=_LINE_STRING_COORDINATES_JSON_SCHEMA
)

_POINT_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "Point", coordinates=_POINT_COORDINATES_JSON_SCHEMA
)

_POLYGON_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "Polygon", coordinates=_POLYGON_COORDINATES_JSON_SCHEMA
)

_MULTI_LINE_STRING_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "MultiLineString", coordinates=_MULTI_LINE_STRING_COORDINATES_JSON_SCHEMA
)

_MULTI_POINT_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "MultiPoint", coordinates=_MULTI_POINT_COORDINATES_JSON_SCHEMA
)

_MULTI_POLYGON_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "MultiPolygon", coordinates=_MULTI_POLYGON_COORDINATES_JSON_SCHEMA
)

_GEOMETRY_COLLECTION_JSON_SCHEMA = geometry_json_schema(
    "GeometryCollection",
    geometries={
        "oneOf": [
            _LINE_STRING_GEOMETRY_JSON_SCHEMA,
            _POINT_GEOMETRY_JSON_SCHEMA,
            _POLYGON_GEOMETRY_JSON_SCHEMA,
            _MULTI_LINE_STRING_GEOMETRY_JSON_SCHEMA,
            _MULTI_POINT_GEOMETRY_JSON_SCHEMA,
            _MULTI_POLYGON_GEOMETRY_JSON_SCHEMA,
        ]
    },
)

########################################################################
# Lookup table for all the JSON Schema
########################################################################

_GEOMETRY_JSON_SCHEMA = {
    GeometryType.GEOMETRY_COLLECTION: _GEOMETRY_COLLECTION_JSON_SCHEMA,
    GeometryType.LINE_STRING: _LINE_STRING_GEOMETRY_JSON_SCHEMA,
    GeometryType.POINT: _POINT_GEOMETRY_JSON_SCHEMA,
    GeometryType.POLYGON: _POLYGON_GEOMETRY_JSON_SCHEMA,
    GeometryType.MULTI_LINE_STRING: _MULTI_LINE_STRING_GEOMETRY_JSON_SCHEMA,
    GeometryType.MULTI_POINT: _MULTI_POINT_GEOMETRY_JSON_SCHEMA,
    GeometryType.MULTI_POLYGON: _MULTI_POLYGON_GEOMETRY_JSON_SCHEMA,
}
