"""Building feature models for Overture Maps buildings theme."""

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


class Building(OvertureFeature, BuildingShape):
    """Building feature model."""

    # Core

    theme: Literal["buildings"] = Field(..., description="Feature theme")
    type: Literal["building"] = Field(..., description="Feature type")
    geometry: Annotated[Geometry, GeometryTypeConstraint("Polygon", "MultiPolygon")] = (
        Field(..., description="Geometry (Polygon or MultiPolygon)")
    )

    # Optional

    address: AddressContainer = Field(default=None, description="Address information")
    building_class: BuildingClass = Field(
        default=None, alias="class", description="Building class"
    )
    has_parts: bool = Field(default=None, description="Building has parts")
    level: int = Field(default=None, description="Z-order level")
    names: NamesContainer = Field(default=None, description="Multilingual names")
    subtype: BuildingSubtype = Field(default=None, description="Building subtype")
