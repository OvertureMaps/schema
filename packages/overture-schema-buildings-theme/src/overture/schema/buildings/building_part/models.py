"""Building part feature models for Overture Maps buildings theme."""

from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core import OvertureFeature
from overture.schema.core.models import Stacked
from overture.schema.core.names import Named
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.ref import Id, Reference, Relationship

from ..building.models import Building
from ..models import Shape


class BuildingPart(
    OvertureFeature[Literal["buildings"], Literal["building_part"]],
    Named,
    Stacked,
    Shape,
):
    """A single building part.

    Parts describe their shape and color and other properties. Each building part must
    refer to the building to which it belongs.
    """

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(
            description="The part's geometry.",
        ),
    ]

    # Required

    building_id: Annotated[
        Id,
        Field(description="The building ID to which this part belongs"),
        Reference(Relationship.BELONGS_TO, Building),
    ]
