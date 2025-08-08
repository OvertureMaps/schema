"""Land cover feature models for Overture Maps base theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.base.land_cover.enums import LandCoverSubtype
from overture.schema.core import (
    Feature,
)
from overture.schema.core.geometry import Geometry, GeometryType, GeometryTypeConstraint
from overture.schema.core.models import CartographicallyHinted, Stacked


class LandCover(
    Feature[Literal["base"], Literal["land_cover"]], Stacked, CartographicallyHinted
):
    """Representation of the Earth's natural surfaces."""

    model_config = ConfigDict(title="land_cover")

    # Core

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(description="Geometry (Polygon or MultiPolygon)"),
    ]

    # Required

    subtype: LandCoverSubtype
