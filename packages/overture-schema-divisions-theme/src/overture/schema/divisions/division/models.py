"""Division models for Overture Maps divisions theme."""

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
from overture.schema.core.perspectives import Perspectives
from overture.schema.validation import (
    CountryCode,
    MinItemsConstraint,
    NoWhitespaceString,
    RegionCode,
    UniqueItemsConstraint,
)

from ..shared import (
    CapitalOfDivisionItem,
    DivisionClass,
    HierarchyItem,
    Norms,
    PlaceType,
)
from ..validation import parent_division_required_unless


@parent_division_required_unless("subtype", PlaceType.COUNTRY)
class Division(OvertureFeature):
    """Administrative and political division model representing organized territories.

    Models administrative and political entities at various hierarchical levels,
    from countries and provinces to cities, towns, and neighborhoods. Represents
    both official governmental divisions and recognized informal territorial
    organizations.

    Each division has a point geometry indicating its representative location,
    hierarchical relationships with parent/child divisions, and support for
    multiple political perspectives in disputed territories.
    """

    # Core

    theme: Literal["divisions"] = Field(..., description="Feature theme")
    type: Literal["division"] = Field(..., description="Feature type")
    geometry: Annotated[Geometry, GeometryTypeConstraint("Point")] = Field(
        ..., description="Point geometry for division location"
    )

    # Required

    country: CountryCode = Field(..., description="ISO 3166-1 alpha-2 country code")
    # NOTE: this is the only remaining use of MinItemsConstraint because there's no way to validate
    # a list of lists otherwise
    hierarchies: list[
        Annotated[list[HierarchyItem], MinItemsConstraint(1), UniqueItemsConstraint()]
    ] = Field(..., min_length=1, description="Administrative hierarchy chains")
    names: NamesContainer = Field(..., description="Multilingual names")
    subtype: PlaceType = Field(..., description="Administrative level")

    # Optional

    capital_division_ids: Annotated[
        list[NoWhitespaceString], UniqueItemsConstraint()
    ] = Field(default=None, min_length=1, description="Capital division identifiers")
    capital_of_divisions: Annotated[
        list[CapitalOfDivisionItem], UniqueItemsConstraint()
    ] = Field(default=None, min_length=1, description="Divisions this is capital of")
    cartography: CartographyContainer = Field(
        default=None, description="Cartographic display hints"
    )
    class_: DivisionClass = Field(
        default=None, alias="class", description="Division class designation"
    )
    local_type: dict[str, str] = Field(
        default=None, description="Localized subtype name"
    )
    norms: Norms = Field(default=None, description="Local norms")
    parent_division_id: NoWhitespaceString = Field(
        default=None, min_length=1, description="Parent division identifier"
    )
    perspectives: Perspectives = Field(
        default=None, description="Political perspectives"
    )
    population: int = Field(default=None, ge=0, description="Population count")
    prominence: float = Field(
        default=None, ge=0.0, le=1.0, description="Prominence score (0.0-1.0)"
    )
    region: RegionCode = Field(default=None, description="ISO 3166-2 region code")
