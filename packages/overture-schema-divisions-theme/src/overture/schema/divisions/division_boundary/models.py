"""Division boundary models for Overture Maps divisions theme."""

from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core.base import (
    OvertureFeature,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.perspectives import Perspectives
from overture.schema.validation import (
    CountryCode,
    RegionCode,
    UniqueItemsConstraint,
    not_required_if,
)
from overture.schema.validation.mixin import exactly_one_of

from ..shared import (
    AreaBoundaryClass,
    PlaceType,
)


@exactly_one_of("is_land", "is_territorial")
@not_required_if("subtype", PlaceType.COUNTRY, ["country"])
class DivisionBoundary(OvertureFeature):
    """Administrative division boundary model representing borders between territories.

    Models linear boundaries between adjacent administrative divisions using
    line string geometries. Represents shared borders at various administrative
    levels, from international boundaries to local district borders.

    Supports both land and maritime boundaries, disputed boundary indicators,
    and multiple political perspectives on contested borders.
    """

    # Core

    theme: Literal["divisions"] = Field(..., description="Feature theme")
    type: Literal["division_boundary"] = Field(..., description="Feature type")
    geometry: Annotated[
        Geometry, GeometryTypeConstraint("LineString", "MultiLineString")
    ] = Field(..., description="Geometry (LineString or MultiLineString)")

    # Required

    subtype: PlaceType = Field(..., description="Administrative level")
    class_: AreaBoundaryClass = Field(
        ..., alias="class", description="Boundary class (land/maritime)"
    )
    division_ids: Annotated[list[str], UniqueItemsConstraint()] = Field(
        ..., min_length=2, max_length=2, description="Two division IDs (left/right)"
    )

    # Optional

    country: CountryCode | None = Field(
        default=None,
        description="ISO 3166-1 alpha-2 country code (not for country boundaries)",
    )
    is_disputed: bool | None = Field(
        default=None,
        description="Boundary is disputed",
    )
    is_land: bool | None = Field(
        default=None, description="Land boundary designation", strict=True
    )
    is_territorial: bool | None = Field(
        default=None, description="Territorial boundary designation", strict=True
    )
    perspectives: Perspectives | None = Field(
        default=None, description="Political perspectives"
    )
    region: RegionCode | None = Field(
        default=None, description="ISO 3166-2 region code"
    )
