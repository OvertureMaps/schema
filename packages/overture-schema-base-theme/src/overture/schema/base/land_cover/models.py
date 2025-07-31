"""LandCover feature models for Overture Maps base theme."""

from enum import Enum
from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core.base import (
    OvertureFeature,
)
from overture.schema.core.cartography import CartographyContainer
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.names import (
    NamesContainer,
)


class LandCoverSubtype(str, Enum):
    """Subtypes for land_cover features representing Earth's natural surfaces."""

    BARREN = "barren"
    CROP = "crop"
    FOREST = "forest"
    GRASS = "grass"
    MANGROVE = "mangrove"
    MOSS = "moss"
    SHRUB = "shrub"
    SNOW = "snow"
    URBAN = "urban"
    WETLAND = "wetland"


class LandCover(OvertureFeature):
    """Earth's natural surface cover classification model.

    Represents broad categorization of natural surface types including forests,
    grasslands, croplands, urban areas, wetlands, and other surface cover types.
    Provides structured classification of Earth's physical surface characteristics.
    """

    # Core

    theme: Literal["base"] = Field(..., description="Feature theme")
    type: Literal["land_cover"] = Field(..., description="Feature type")
    geometry: Annotated[Geometry, GeometryTypeConstraint("Polygon", "MultiPolygon")] = (
        Field(..., description="Geometry (Polygon or MultiPolygon)")
    )

    # Required

    subtype: LandCoverSubtype = Field(..., description="Type of surface represented")

    # Optional

    cartography: CartographyContainer = Field(
        default=None, description="Cartographic display hints"
    )
    level: int = Field(default=None, description="Z-order level")
    names: NamesContainer = Field(default=None, description="Multilingual names")
