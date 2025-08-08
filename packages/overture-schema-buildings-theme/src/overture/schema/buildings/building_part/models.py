"""Building part feature models for Overture Maps buildings theme."""

from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core import Feature
from overture.schema.core.geometry import Geometry, GeometryType, GeometryTypeConstraint
from overture.schema.core.models import Named, Stacked
from overture.schema.core.types import Id

from ..models import Shape


class BuildingPart(
    Feature[Literal["buildings"], Literal["building_part"]], Named, Stacked, Shape
):
    """A single building part.

    Parts describe their shape and color and other properties. Each building part must
    contain the building with which it is associated.
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
        Id, Field(description="The building ID to which this part belongs")
    ]
