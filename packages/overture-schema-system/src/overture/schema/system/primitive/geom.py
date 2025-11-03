"""
Geometry primitive and geometry type constraint.

Use `Geometry` as the type for fields containing geometry values. Use `GeometryTypeConstraint` if
you need to constrain allowed types of geometries.

Example
-------
Create a Pydantic model with a geometry field that is constrained to only allow point geometries.

>>> from typing import Annotated
>>> from pydantic import BaseModel
>>> from overture.schema.system.primitive import float32
>>> class Peak(BaseModel):
...     position: Annotated[
...                  Geometry,
...                  GeometryTypeConstraint(GeometryType.POINT)
...               ]
...     elevation: float32
...
>>> fuji = Peak(position=Geometry.from_wkt('POINT(138.7274 35.3606)'), elevation=3_776)

Non-point geometries will be rejected with a validation error.

>>> from pydantic import ValidationError
>>> try:
...     Peak(position=Geometry.from_wkt('LINESTRING(0 0, 1 1)'), elevation=0)
... except ValidationError as e:
...    assert "geometry type not allowed" in str(e)
...    print("Validation failed")
Validation failed
"""

from dataclasses import dataclass
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


class GeometryType(str, Enum):
    """
    Vector geometry type.
    """

    _geo_json_type: str

    GEOMETRY_COLLECTION = (
        "geometry_collection",
        "GeometryCollection",
        "A mixed type collection of geometries treated as a single geometry.",
    )
    LINE_STRING = (
        "line_string",
        "LineString",
        "A sequence of positions connected by straight line segments.",
    )
    MULTI_LINE_STRING = (
        "multi_line_string",
        "MultiLineString",
        "A collection of line strings treated as a single geometry.",
    )
    MULTI_POINT = (
        "multi_point",
        "MultiPoint",
        "A collection of points treated as a single geometry.",
    )
    MULTI_POLYGON = (
        "multi_polygon",
        "MultiPolygon",
        "A collection of polygons treated as a single geometry.",
    )
    POINT = "point", "Point", "A single position defined by one coordinate tuple."
    POLYGON = (
        "polygon",
        "Polygon",
        "A planar surface bounded by one outer ring and zero or more inner rings (holes).",
    )

    def __new__(cls, value: str, geo_json_type: str, doc: str) -> "GeometryType":
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._geo_json_type = geo_json_type
        obj.__doc__ = doc
        return obj

    @property
    def geo_json_type(self) -> str:
        return self._geo_json_type


_GEOMETRY_GEO_JSON_TYPES = [item.geo_json_type for item in GeometryType]

_GEOMETRY_TYPE_REVERSE_LOOKUP = {item.geo_json_type: item for item in GeometryType}


@dataclass(frozen=True, slots=True)
class GeometryTypeConstraint:
    """
    Limits the geometry types allowed on a `Geometry` field.

    Parameters
    ----------
    *allowed_types: GeometryType
        The geometry types that the constrained geometry is allowed to have. (May not be empty or
        contain duplicates.)

    Attributes
    ----------
    allowed_types: tuple[GeometryType, ...]
        The geometry types that the constrained geometry is allowed to have, sorted in alphabetical
        order.

    Examples
    --------
    Limit allowed geometry of a feature type to line string and multi line string.

    >>> from typing import Annotated
    >>> from pydantic import BaseModel;
    >>> class MyModel(BaseModel):
    ...     geometry: Annotated[
    ...                  Geometry,
    ...                  GeometryTypeConstraint(GeometryType.LINE_STRING, GeometryType.MULTI_LINE_STRING)
    ...               ]
    """

    allowed_types: tuple[GeometryType, ...]

    def __init__(self, *allowed_types: GeometryType) -> None:
        object.__setattr__(
            self,
            "allowed_types",
            GeometryTypeConstraint._validate_geometry_types(allowed_types),
        )

    def _validate(self, value: "Geometry", info: ValidationInfo) -> "Geometry":
        geom_type = value.geom_type

        if geom_type not in self.allowed_types:
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
                            "error": f"geometry type not allowed: {repr(geom_type)} (allowed values: {repr(self.allowed_types)})"
                        },
                    )
                ],
            )
        return value

    @classmethod
    def _validate_geometry_types(
        cls, a: tuple[GeometryType, ...]
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
        return core_schema.with_info_after_validator_function(self._validate, schema)

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
    """
    Immutable vector geometry primitive.

    This type is a geometric primitive with representations that can differ significantly between
    different data formats. Consequently, does not derive from the Pydantic `BaseModel` although it
    can participate in a `BaseModel` as a field.

    Parameters
    ----------
    geom: BaseGeometry
        The wrapped Shapely geometry.

    Examples
    --------
    Create a new geometry value by wrapping a Shapely geometry:

    >>> from shapely.geometry import Point
    >>> geom = Geometry(Point(1, 2))
    >>> assert geom.wkt == "POINT (1 2)"

    Create a new geometry value from a GeoJSON dict:

    >>> geom = Geometry.from_geo_json({ "type": "Point", "coordinates": [1, 2]})
    >>> assert geom.wkt == "POINT (1 2)"

    Create a new geometry value from its well-known text (WKT) representation:

    >>> geom = Geometry.from_wkt("POINT (1 2)")
    >>> assert geom.wkt == "POINT (1 2)"
    """

    __slots__ = ("_geom",)

    _geom: BaseGeometry

    def __init__(self, geom: BaseGeometry) -> None:
        if not isinstance(geom, BaseGeometry):
            raise TypeError(
                f"`geom` must be a `BaseGeometry` (Shapely) but {geom} is a `{type(geom).__name__}`"
            )
        if geom.is_empty:
            raise ValueError(f"`geom` must not be empty, but {geom} is empty")
        object.__setattr__(self, "_geom", geom)

    def __setattr__(self, _: str, __: object) -> None:
        raise AttributeError(f"`{self.__class__.__name__} is immutable")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Geometry) and self.geom == other.geom

    def __hash__(self) -> int:
        return hash(self.geom)  # Shapely `BaseGometry` is immutable.

    def __repr__(self) -> str:
        return f"<{repr(self.geom)}>"

    def __str__(self) -> str:
        return self.wkt

    @property
    def geom(self) -> BaseGeometry:
        """
        BaseGeometry: The wrapped Shapely geometry.
        """
        return self._geom

    @property
    def geom_type(self) -> GeometryType:
        """
        GeometryType: The geometry type.
        """
        try:
            return _GEOMETRY_TYPE_REVERSE_LOOKUP[self.geom.geom_type]
        except KeyError as e:
            raise RuntimeError(
                f"internal `geom` has unknown type: {repr(self.geom.geom_type)}"
            ) from e

    @property
    def wkt(self) -> str:
        """
        str: Well-known text (WKT) representation of the geometry.
        """
        return self.geom.wkt

    def to_geo_json(self) -> dict[str, Any]:
        """Get a GeoJSON-compatible representation of the geometry."""
        return mapping(self.geom)

    @classmethod
    def from_geo_json(cls, value: dict[str, Any]) -> "Geometry":
        """Create a Geometry from a dict containing GeoJSON-compatible geometry."""
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
            value: Geometry | dict[str, Any] | BaseGeometry | bytes | str,
            info: ValidationInfo,
        ) -> Geometry:
            try:
                if isinstance(value, Geometry):
                    return value
                # Handle GeoJSON dict
                elif isinstance(value, dict):
                    return cls.from_geo_json(value)
                # Handle Shapely geometry directly
                elif isinstance(value, BaseGeometry):
                    return cls(value)
                # Handle WKB bytes
                elif isinstance(value, bytes):
                    return cls.from_wkb(value)
                # Handle WKT string
                elif isinstance(value, str):
                    return cls.from_wkt(value)
                else:
                    raise TypeError(
                        f"expected `Geometry`, `dict` (GeoJSON), `BaseGeometry`, `bytes` (WKB), or `str` (WKT); got `{type(value).__name__}` with value {value}"
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

# This is the `bbox` schema for a GeoJSON *geometry* object, not for a
# *feature*. We include it to maximize GeoJSON interop, but we ignore it
# and do not support roundtripping it from GeoJSON into the Overture
# Pydantic model and back to GeoJSON.
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
    "maxItems": 3,  # Shapely only supports up to 3D
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


def _geometry_json_schema(
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


_LINE_STRING_GEOMETRY_JSON_SCHEMA = _geometry_json_schema(
    "LineString", coordinates=_LINE_STRING_COORDINATES_JSON_SCHEMA
)

_POINT_GEOMETRY_JSON_SCHEMA = _geometry_json_schema(
    "Point", coordinates=_POINT_COORDINATES_JSON_SCHEMA
)

_POLYGON_GEOMETRY_JSON_SCHEMA = _geometry_json_schema(
    "Polygon", coordinates=_POLYGON_COORDINATES_JSON_SCHEMA
)

_MULTI_LINE_STRING_GEOMETRY_JSON_SCHEMA = _geometry_json_schema(
    "MultiLineString", coordinates=_MULTI_LINE_STRING_COORDINATES_JSON_SCHEMA
)

_MULTI_POINT_GEOMETRY_JSON_SCHEMA = _geometry_json_schema(
    "MultiPoint", coordinates=_MULTI_POINT_COORDINATES_JSON_SCHEMA
)

_MULTI_POLYGON_GEOMETRY_JSON_SCHEMA = _geometry_json_schema(
    "MultiPolygon", coordinates=_MULTI_POLYGON_COORDINATES_JSON_SCHEMA
)

_GEOMETRY_COLLECTION_JSON_SCHEMA = _geometry_json_schema(
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
