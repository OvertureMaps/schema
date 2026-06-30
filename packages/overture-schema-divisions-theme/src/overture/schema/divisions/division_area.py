"""Division area models for Overture Maps divisions theme."""

import textwrap
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.common import (
    OvertureFeature,
)
from overture.schema.common.names import (
    Named,
    Names,
)
from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.model_constraint import (
    FieldEqCondition,
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

from ._common import AdminLevel, DivisionSubtype
from .division import Division


class AreaClass(str, DocumentedEnum):
    """
    Further classification of a division area that is more specific than its `subtype`.

    A division area's `class` adds detail to the broad classification found in `DivisionSubtype`.
    """

    LAND = ("land", "The area does not extend beyond the coastline.")
    MARITIME = (
        "maritime",
        textwrap.dedent("""
            The area extends beyond the coastline, in most cases to the extent of the division's
            territorial sea, if it has one.
        """).strip(),
    )


@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.COUNTRY))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.DEPENDENCY))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.MACROREGION))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.REGION))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.MACROCOUNTY))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.COUNTY))
@require_any_true(
    FieldEqCondition("is_land", True),
    FieldEqCondition("is_territorial", True),
)
class DivisionArea(
    OvertureFeature[Literal["divisions"], Literal["division_area"]], Named
):
    """
    Division areas are polygon features that represent the land or maritime area covered by a
    division.

    Each division area belongs to a division which it references by ID, and for which the division
    area provides an area polygon. For ease of use, every division area repeats the subtype, names,
    country, and region properties of the division it belongs to.
    """

    model_config = ConfigDict(title="division_area")

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(
            description=textwrap.dedent("""
                The area covered by the division with which this area feature is
                associated.
            """).strip(),
        ),
    ]

    # Required

    names: Annotated[
        Names,
        Field(description="All known names by which the owning division is called"),
    ]
    subtype: Annotated[
        DivisionSubtype,
        Field(
            description=textwrap.dedent("""
                A broad classification of the division this area belongs to (e.g., country, region,
                locality, etc.).

                This value is the same as the owning division's `subtype`.
            """).strip()
        ),
    ]
    class_: Annotated[
        AreaClass,
        Field(
            alias="class",
            description=textwrap.dedent("""
                A more specific classification of the division area than is provided by `subtype`.
            """).strip(),
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
    division_id: Annotated[
        Id,
        Field(
            description="Division ID of the parent division of this area.",
        ),
        Reference(Relationship.HIERARCHY, Division, role="child_of"),
    ]
    country: Annotated[
        CountryCodeAlpha2,
        Field(
            description="ISO 3166-1 alpha-2 country code of the division this area belongs to.",
        ),
    ]

    # Optional

    region: Annotated[
        RegionCode | None,
        Field(
            description=textwrap.dedent("""
                ISO 3166-2 principal subdivision code of the division this area belongs to.
            """).strip(),
        ),
    ] = None
    admin_level: AdminLevel | None = None
