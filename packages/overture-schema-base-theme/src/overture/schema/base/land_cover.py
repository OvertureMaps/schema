"""
The `LandCover` feature type model and supporting types.
"""

from enum import Enum
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.core import (
    OvertureFeature,
)
from overture.schema.core.cartography import CartographicallyHinted
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)


class LandCoverSubtype(str, Enum):
    """Primary or dominant material covering the land."""

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


class LandCover(
    OvertureFeature[Literal["base"], Literal["land_cover"]], CartographicallyHinted
):
    """
    Land cover features indicate the primary natural or artificial surface material covering a land
    area on the earth, including vegetation types like forests and crops, built environments like
    cities, and natural surfaces like wetlands or barren ground.

    Land cover features relate to `LandUse` features in the following way: land cover is the
    physical thing covering the land, while land use is the human use to which the land is being
    put.

    TODO: Explain relationship to `Land` features.
    """

    model_config = ConfigDict(title="land_cover")

    # Overture Feature

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(
            description="Shape of the covered land area, which may be a polygon or multi-polygon."
        ),
    ]

    # Required

    subtype: LandCoverSubtype
