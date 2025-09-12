"""Division boundary models for Overture Maps divisions theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.core import (
    Feature,
)
from overture.schema.core.geometry import Geometry, GeometryType, GeometryTypeConstraint
from overture.schema.core.models import Perspectives
from overture.schema.core.ref import Reference, Relationship
from overture.schema.core.types import (
    CountryCode,
    Id,
    RegionCode,
)
from overture.schema.core.validation import (
    UniqueItemsConstraint,
    exactly_one_of,
    not_required_if,
)

from ..division import Division
from ..enums import PlaceType
from .enums import BoundaryClass


@exactly_one_of("is_land", "is_territorial")
@not_required_if("subtype", PlaceType.COUNTRY, ["country"])
class DivisionBoundary(Feature[Literal["divisions"], Literal["division_boundary"]]):
    """Boundaries represent borders between divisions of the same subtype.

    Some boundaries may be disputed by the divisions on one or both sides.
    """

    model_config = ConfigDict(title="boundary")

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(
            GeometryType.LINE_STRING, GeometryType.MULTI_LINE_STRING
        ),
        Field(
            description="Boundary line or lines",
        ),
    ]

    # Required

    subtype: PlaceType
    class_: Annotated[BoundaryClass, Field(alias="class")]
    is_land: Annotated[
        bool | None,
        Field(
            description="""A boolean to indicate whether or not the feature geometry represents the
land-clipped, non-maritime boundary. The geometry can be used for map
rendering, cartographic display, and similar purposes.""",
            strict=True,
        ),
    ] = None
    is_territorial: Annotated[
        bool | None,
        Field(
            description="""A boolean to indicate whether or not the feature geometry represents
Overture's best approximation of this place's maritime boundary. For
coastal places, this would tend to include the water area. The geometry
can be used for data processing, reverse-geocoding, and similar purposes.""",
            strict=True,
        ),
    ] = None
    division_ids: Annotated[
        list[
            Annotated[
                Id,
                Reference(Relationship.BOUNDARY_OF, Division),
            ]
        ],
        Field(
            min_length=2,
            max_length=2,
            description="""Identifies the two divisions to the left and right, respectively, of the boundary line. The left- and right-hand sides of the boundary are considered from the perspective of a person standing on the line facing in the direction in which the geometry is oriented, i.e. facing toward the end of the line.

The first array element is the Overture ID of the left division. The second element is the Overture ID of the right division.""",
        ),
        UniqueItemsConstraint(),
    ]
    country: Annotated[
        CountryCode | None,
        Field(
            description="""ISO 3166-1 alpha-2 country code of the country or country-like
entity that both sides of the boundary share.

This property will be present on boundaries between two regions, counties,
or similar entities within the same country, but will not be present on boundaries
between two countries or country-like entities.""",
        ),
    ] = None

    # Optional

    region: Annotated[
        RegionCode | None,
        Field(
            description="""ISO 3166-2 principal subdivision code of the subdivision-like
entity that both sides of the boundary share.

This property will be present on boundaries between two counties, localadmins
or similar entities within the same principal subdivision, but will not be
present on boundaries between different principal subdivisions or countries.""",
        ),
    ] = None
    is_disputed: Annotated[
        bool | None,
        Field(
            description="""Indicator if there are entities disputing this division boundary.
Information about entities disputing this boundary should be included in perspectives
property.

This property should also be true if boundary between two entities is unclear
and this is "best guess". So having it true and no perspectives gives map creators
reason not to fully trust the boundary, but use it if they have no other.""",
            strict=True,
        ),
    ] = None
    perspectives: Annotated[
        Perspectives | None,
        Field(
            description="""Political perspectives from which this division boundary is considered to be an accurate representation.

If this property is absent, then this boundary is not known to be disputed from any political perspective. Consequently, there is only one boundary feature representing the entire real world entity.

If this property is present, it means the boundary represents one of several alternative perspectives on the same real-world entity.

There are two modes of perspective:

  1. `accepted_by` means the representation of the boundary is accepted by the listed entities and would be included on a map drawn from their perspective.

  2. `disputed_by` means the representation of the boundary is disputed by the listed entities and would be excluded from a map drawn from their perspective.

When drawing a map from the perspective of a given country, one would start by gathering all the undisputed boundary (with no `perspectives` property), and then adding to that first all boundary explicitly accepted by the country, and second all boundary not explicitly disputed by the country.""",
        ),
    ] = None
