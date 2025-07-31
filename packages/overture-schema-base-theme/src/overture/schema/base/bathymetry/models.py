"""Bathymetry feature models for Overture Maps base theme."""

from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core.base import (
    OvertureFeature,
)
from overture.schema.core.cartography import CartographyContainer
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint


class Bathymetry(OvertureFeature):
    """Bathymetry feature model representing underwater depth measurements.

    Polygonal features that represent areas of consistent water depth
    for marine navigation and oceanographic mapping purposes.
    """

    # Core

    theme: Literal["base"] = Field(..., description="Feature theme")
    type: Literal["bathymetry"] = Field(..., description="Feature type")
    geometry: Annotated[Geometry, GeometryTypeConstraint("Polygon", "MultiPolygon")] = (
        Field(..., description="Geometry (Polygon or MultiPolygon)")
    )

    # Required

    depth: int = Field(..., ge=0, description="Water depth in meters (>= 0)")

    # Optional

    cartography: CartographyContainer = Field(
        default=None, description="Cartographic display hints"
    )
