"""Division boundary models for Overture Maps divisions theme."""

import textwrap
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.common import (
    OvertureFeature,
)
from overture.schema.common.models import Perspectives
from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import (
    FieldEqCondition,
    forbid_if,
    require_any_true,
    require_if,
)
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.ref import Id, Reference, Relationship
from overture.schema.system.string import CountryCodeAlpha2, RegionCode

from ._common import IS_COUNTRY, AdminLevel, DivisionSubtype
from .division import Division


class BoundaryClass(str, DocumentedEnum):
    """
    The kind of boundary: land or maritime.
    """

    LAND = (
        "land",
        textwrap.dedent("""
            None of the boundary geometry extends beyond the coastline of either associated
            division.
        """).strip(),
    )
    MARITIME = (
        "maritime",
        textwrap.dedent("""
            All the boundary geometry extends beyond the coastline of both associated divisions.
        """).strip(),
    )


@forbid_if(["country"], IS_COUNTRY)
@require_if(["country"], ~IS_COUNTRY)
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.COUNTRY))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.DEPENDENCY))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.MACROREGION))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.REGION))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.MACROCOUNTY))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.COUNTY))
@require_any_true("is_land", "is_territorial")
class DivisionBoundary(
    OvertureFeature[Literal["divisions"], Literal["division_boundary"]]
):
    """
    Boundaries represent borders between divisions of the same subtype.

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

    subtype: Annotated[
        DivisionSubtype,
        Field(
            description=textwrap.dedent("""
                A broad classification of the divisions this boundary separates (e.g., country,
                region, locality, etc.).
            """).strip()
        ),
    ]
    class_: Annotated[
        BoundaryClass,
        Field(
            alias="class",
            description="The kind of boundary: land or maritime.",
        ),
    ]
    is_land: Annotated[
        bool | None,
        Field(
            description=textwrap.dedent("""
                Flag indicating whether or not the feature geometry represents the land-clipped,
                non-maritime boundary. The geometry can be used for map rendering, cartographic
                display, and similar purposes.
            """).strip(),
            strict=True,
        ),
    ] = None
    is_territorial: Annotated[
        bool | None,
        Field(
            description=textwrap.dedent("""
                Flag indicating whether or not the feature geometry represents Overture's best
                approximation of the division's territorial boundary. For coastal places, this will
                tend to include the water area. The geometry can be used for data processing,
                reverse-geocoding, and similar purposes.
            """).strip(),
            strict=True,
        ),
    ] = None
    division_ids: Annotated[
        list[
            Annotated[
                Id,
                Reference(Relationship.COMPOSITION, Division, role="boundary_of"),
            ]
        ],
        Field(
            min_length=2,
            max_length=2,
            description=textwrap.dedent("""
                Identifies the two divisions to the left and right, respectively, of the
                boundary line. The left- and right-hand sides of the boundary are considered
                from the perspective of a person standing on the line facing in the direction
                in which the geometry is oriented, i.e. facing toward the end of the line.

                The first array element is the Overture ID of the left division. The second
                element is the Overture ID of the right division.
            """).strip(),
        ),
        UniqueItemsConstraint(),
    ]
    country: Annotated[
        CountryCodeAlpha2 | None,
        Field(
            description=textwrap.dedent("""
                ISO 3166-1 alpha-2 country code of the country or country-like entity that
                both sides of the boundary share.

                This property will be present on boundaries between two regions, counties,
                or similar entities within the same country, but will not be present on
                boundaries between two countries or country-like entities.
            """).strip(),
        ),
    ] = None

    # Optional

    region: Annotated[
        RegionCode | None,
        Field(
            description=textwrap.dedent("""
                ISO 3166-2 principal subdivision code of the subdivision-like entity that
                both sides of the boundary share.

                This property will be present on boundaries between two counties, localadmins
                or similar entities within the same principal subdivision, but will not be
                present on boundaries between different principal subdivisions or countries.
            """).strip(),
        ),
    ] = None
    admin_level: AdminLevel | None = None
    is_disputed: Annotated[
        bool | None,
        Field(
            description=textwrap.dedent("""
                Flag indicating whether this boundary is either disputed outright or is a "best
                guess" in a case where the boundary between two divisions is unclear.

                If the boundary is disputed outright, this flag is true and the entities disputing
                it are listed in the `perspectives` property. If the boundary is simply a "best
                guess", this flag is true but no disputing entities are listed in `perspectives`.
            """).strip(),
            strict=True,
        ),
    ] = None
    perspectives: Annotated[
        Perspectives | None,
        Field(
            description=textwrap.dedent("""
                Political perspectives from which this division boundary is considered to be
                an accurate representation.

                If this property is absent, then this boundary is not known to be disputed
                from any political perspective. Consequently, there is only one boundary
                feature representing the entire real world entity.

                If this property is present, it means the boundary represents one of several
                alternative perspectives on the same real-world entity.

                There are two modes of perspective:

                1. `accepted_by` means the representation of the boundary is accepted by the
                   listed entities and would be included on a map drawn from their perspective.

                2. `disputed_by` means the representation of the boundary is disputed by the
                   listed entities and would be excluded from a map drawn from their
                   perspective.

                When drawing a map from the perspective of a given country, one would start by
                gathering all the undisputed boundaries (those with no `perspectives` value); and
                then adding to that: first, all boundaries explicitly accepted by the country, and
                second, all boundaries not explicitly disputed by the country.
            """).strip(),
        ),
    ] = None
