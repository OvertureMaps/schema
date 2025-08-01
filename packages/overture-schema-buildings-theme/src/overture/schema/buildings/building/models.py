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
    """Building model with footprint geometry and structural attributes.

    Represents building footprints or roofprints with polygon geometry and
    attributes for classification, physical properties, and appearance.
    """

    # Core

    theme: Literal["buildings"] = Field(..., description="Feature theme")
    type: Literal["building"] = Field(..., description="Feature type")
    geometry: Annotated[Geometry, GeometryTypeConstraint("Polygon", "MultiPolygon")] = (
        Field(..., description="Geometry (Polygon or MultiPolygon)")
    )

    # Optional

    address: AddressContainer | None = Field(
        default=None, description="Address information"
    )
    building_class: BuildingClass | None = Field(
        default=None, alias="class", description="Building class"
    )
    has_parts: bool | None = Field(default=None, description="Building has parts")
    level: int | None = Field(default=None, description="Z-order level")
    names: NamesContainer | None = Field(default=None, description="Multilingual names")
    subtype: BuildingSubtype | None = Field(
        default=None, description="Building subtype"
    )
