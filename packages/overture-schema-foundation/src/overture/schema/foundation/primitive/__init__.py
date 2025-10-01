"""
primitive
=========
Primitive data types.

This module provides a set of primitive types that can be used as fields in Pydantic models but are
not themselves models. The primitive types include specific numeric types such as int32 and
geometric types including `Geometry` and `BBox`.

Primitives are intended to provide specific, well-defined behavior for a wide range of serialization
targets including not just Pydantic models and JSON, but also a range of other serialization
targets, for example, the Parquet format or Spark dataframes. They come with built-in Pydantic
constraints, but also specific documented behavior expectations so they can be supported by other
serialization targets.

Modules
-------
bbox : module
   Bounding box type.
geom : module
   Geometry type.
num : module
   Numeric primitives such as int32 and float64.

"""

from .bbox import BBox
from .geom import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from .num import (
    float32,
    float64,
    int8,
    int16,
    int32,
    int64,
    pct,
    uint8,
    uint16,
    uint32,
)

__all__ = [
    "BBox",
    "Geometry",
    "GeometryType",
    "GeometryTypeConstraint",
    "int8",
    "int16",
    "int32",
    "int64",
    "float32",
    "float64",
    "pct",
    "uint8",
    "uint16",
    "uint32",
]
