"""Division area models for Overture Maps divisions theme."""

from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core.base import (
    OvertureFeature,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.names import (
    NamesContainer,
)
from overture.schema.validation import (
    CountryCode,
    RegionCode,
    exactly_one_of,
)

from ..shared import (
    AreaBoundaryClass,
    PlaceType,
)


@exactly_one_of("is_land", "is_territorial")
class DivisionArea(OvertureFeature):
    """Administrative division area model representing territorial boundaries.

    Models the geographic area covered by an administrative division using
    polygon geometries. Represents both land areas and maritime territorial
    boundaries, providing spatial extent information for political and
    administrative entities.

    Can distinguish between land-only boundaries and territorial boundaries
    that include maritime areas.
    """

    # Core

    theme: Literal["divisions"] = Field(..., description="Feature theme")
    type: Literal["division_area"] = Field(..., description="Feature type")
    geometry: Annotated[Geometry, GeometryTypeConstraint("Polygon", "MultiPolygon")] = (
        Field(..., description="Geometry (Polygon or MultiPolygon)")
    )

    # Required

    class_: AreaBoundaryClass = Field(
        ..., alias="class", description="Area class (land/maritime)"
    )
    country: CountryCode = Field(..., description="ISO 3166-1 alpha-2 country code")
    division_id: str = Field(
        ...,
        min_length=1,
        pattern=r"^(\S.*)?\S$",
        description="Referenced division ID (no leading/trailing whitespace)",
    )
    names: NamesContainer = Field(..., description="Multilingual names")
    subtype: PlaceType = Field(..., description="Administrative level")

    # Optional

    is_land: bool = Field(
        default=None, description="Land area designation", strict=True
    )
    is_territorial: bool = Field(
        default=None, description="Territorial area designation", strict=True
    )
    region: RegionCode = Field(default=None, description="ISO 3166-2 region code")
