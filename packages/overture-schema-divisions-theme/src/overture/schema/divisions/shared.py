"""Common divisions theme structures and enums."""

from enum import Enum

from pydantic import Field

from overture.schema.core.base import StrictBaseModel


class PlaceType(str, Enum):
    """Administrative hierarchy levels for divisions."""

    COUNTRY = "country"
    DEPENDENCY = "dependency"
    MACROREGION = "macroregion"
    REGION = "region"
    MACROCOUNTY = "macrocounty"
    COUNTY = "county"
    LOCALADMIN = "localadmin"
    LOCALITY = "locality"
    BOROUGH = "borough"
    MACROHOOD = "macrohood"
    NEIGHBORHOOD = "neighborhood"
    MICROHOOD = "microhood"


class DivisionClass(str, Enum):
    """Division-specific class designations."""

    MEGACITY = "megacity"
    CITY = "city"
    TOWN = "town"
    VILLAGE = "village"
    HAMLET = "hamlet"


class AreaBoundaryClass(str, Enum):
    """Area and boundary class designations."""

    LAND = "land"
    MARITIME = "maritime"


class Side(str, Enum):
    """Driving side for norms."""

    LEFT = "left"
    RIGHT = "right"


class HierarchyItem(StrictBaseModel):
    """Single item in administrative hierarchy."""

    # Required

    division_id: str = Field(..., description="Division identifier")
    subtype: PlaceType = Field(..., description="Administrative level")
    name: str = Field(..., description="Division name")

    def __hash__(self) -> int:
        """Make HierarchyItem hashable for uniqueness constraints."""
        return hash((self.division_id, self.subtype, self.name))

    def __eq__(self, other: object) -> bool:
        """Equality comparison for HierarchyItem."""
        if not isinstance(other, HierarchyItem):
            return False
        return (
            self.division_id == other.division_id
            and self.subtype == other.subtype
            and self.name == other.name
        )


class CapitalOfDivisionItem(StrictBaseModel):
    """Division that has this division as capital."""

    # Required

    division_id: str = Field(..., description="Division identifier")
    subtype: PlaceType = Field(..., description="Administrative level")

    def __hash__(self) -> int:
        """Make CapitalOfDivisionItem hashable for uniqueness constraints."""
        return hash((self.division_id, self.subtype))

    def __eq__(self, other: object) -> bool:
        """Equality comparison for CapitalOfDivisionItem."""
        if not isinstance(other, CapitalOfDivisionItem):
            return False
        return self.division_id == other.division_id and self.subtype == other.subtype


class Norms(StrictBaseModel):
    """Local norms and standards."""

    # Optional

    driving_side: Side | None = Field(
        default=None, description="Driving side (inheritable from parent)"
    )
