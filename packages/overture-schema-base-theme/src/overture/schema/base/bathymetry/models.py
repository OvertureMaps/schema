"""Bathymetry feature models for Overture Maps base theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.base.types import Depth
from overture.schema.core import (
    Feature,
)
from overture.schema.core.geometry import Geometry, GeometryType, GeometryTypeConstraint
from overture.schema.core.models import CartographicallyHinted, Stacked


class Bathymetry(
    Feature[Literal["base"], Literal["bathymetry"]], Stacked, CartographicallyHinted
):
    """Topographic representation of an underwater area, such as a part of the ocean
    floor."""

    model_config = ConfigDict(title="bathymetry")

    # Core

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(description="Geometry (Polygon or MultiPolygon)"),
    ]

    # Required

    depth: Depth
