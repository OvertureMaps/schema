"""Division area models for Overture Maps divisions theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.core import (
    Feature,
)
from overture.schema.core.geometry import Geometry, GeometryType, GeometryTypeConstraint
from overture.schema.core.models import (
    Named,
    Names,
)
from overture.schema.core.ref import Reference, Relationship
from overture.schema.core.types import CountryCode, Id, RegionCode
from overture.schema.core.validation import (
    exactly_one_of,
)

from ..division.models import Division
from ..enums import PlaceType
from .enums import AreaClass


@exactly_one_of("is_land", "is_territorial")
class DivisionArea(Feature[Literal["divisions"], Literal["division_area"]], Named):
    """Division areas are polygons that represent the land or maritime area covered by a
    division.

    Each division area belongs to a division which it references by ID, and for which
    the division area provides an area polygon. For ease of use, every division area
    repeats the subtype, names, country, and region properties of the division it
    belongs to.
    """

    model_config = ConfigDict(title="division_area")

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(
            description="The area covered by the division with which this area feature is associated",
        ),
    ]

    # Required

    names: Names
    subtype: PlaceType
    class_: Annotated[
        AreaClass,
        Field(alias="class"),
    ]
    is_land: Annotated[
        bool | None,
        Field(
            description="""A boolean to indicate whether or not the feature geometry represents the land-clipped, non-maritime boundary. The geometry can be used for map rendering, cartographic display, and similar purposes.""",
            strict=True,
        ),
    ] = None
    is_territorial: Annotated[
        bool | None,
        Field(
            description="""A boolean to indicate whether or not the feature geometry represents Overture's best approximation of this place's maritime boundary. For coastal places, this would tend to include the water area. The geometry can be used for data processing, reverse-geocoding, and similar purposes.""",
            strict=True,
        ),
    ] = None
    division_id: Annotated[
        Id,
        Field(
            description="Division ID of the division this area belongs to.",
        ),
        Reference(Relationship.BELONGS_TO, Division)
    ]
    country: Annotated[
        CountryCode,
        Field(
            description="ISO 3166-1 alpha-2 country code of the division this area belongs to.",
        ),
    ]

    # Optional

    region: Annotated[
        RegionCode | None,
        Field(
            description="ISO 3166-2 principal subdivision code of the division this area belongs to.",
        ),
    ] = None
