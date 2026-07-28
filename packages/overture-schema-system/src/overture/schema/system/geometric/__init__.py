"""
Geometric types.

This module provides geometric types that can be used as fields in Pydantic models but are
not themselves models: `Geometry` for GeoJSON-compatible vector geometry, and `BBox` for bounding
boxes.

These types have representations that can differ significantly between different serialization
targets, so they do not derive from the Pydantic `BaseModel` although they can participate in a
`BaseModel` as a field.
"""

from .bbox import BBox
from .geom import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)

__all__ = [
    "BBox",
    "Geometry",
    "GeometryType",
    "GeometryTypeConstraint",
]
