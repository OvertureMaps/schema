"""Land cover feature models for Overture Maps base theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.base.land_cover.enums import LandCoverSubtype
from overture.schema.core import (
    Feature,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.models import CartographicallyHinted, Stacked


class LandCover(Feature, Stacked, CartographicallyHinted):
    """Representation of the Earth's natural surfaces"""

    model_config = ConfigDict(title="land_cover")

    # Core

    theme: Literal["base"]
    type: Literal["land_cover"]
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Polygon", "MultiPolygon"),
        Field(description="Geometry (Polygon or MultiPolygon)"),
    ]

    # Required

    subtype: LandCoverSubtype
