"""Building part feature models for Overture Maps buildings theme."""

from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core.addresses import (
    AddressContainer,
)
from overture.schema.core.base import OvertureFeature
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.names import (
    NamesContainer,
)

from ..shared import (
    BuildingClass,
    BuildingShape,
    BuildingSubtype,
)


class BuildingPart(OvertureFeature, BuildingShape):
    """Building part feature model."""

    # Core

    theme: Literal["buildings"] = Field(..., description="Feature theme")
    type: Literal["building_part"] = Field(..., description="Feature type")
    geometry: Annotated[Geometry, GeometryTypeConstraint("Polygon", "MultiPolygon")] = (
        Field(..., description="Geometry (Polygon or MultiPolygon)")
    )

    # Required

    building_id: str = Field(..., min_length=1, description="Parent building ID")

    # Optional

    building_class: BuildingClass = Field(
        default=None, alias="class", description="Building class"
    )
    names: NamesContainer = Field(default=None, description="Multilingual names")
    address: AddressContainer = Field(default=None, description="Address information")
    has_parts: bool = Field(default=None, description="Building has parts")
    level: int = Field(default=None, description="Z-order level")
    subtype: BuildingSubtype = Field(default=None, description="Building subtype")
