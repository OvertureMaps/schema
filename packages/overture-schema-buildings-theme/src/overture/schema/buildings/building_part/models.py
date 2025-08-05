"""Building part feature models for Overture Maps buildings theme."""

from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core import Feature
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.models import Named, Stacked
from overture.schema.core.types import Id

from ..models import Shape


class BuildingPart(Feature, Named, Stacked, Shape):
    """A single building part. Parts describe their shape and color and other properties. Each building part must contain the building with which it is associated."""

    # Core

    theme: Literal["buildings"]
    type: Literal["building_part"]
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Polygon", "MultiPolygon"),
        Field(
            description="The part's geometry. It must be a polygon or multipolygon.",
        ),
    ]

    # Required

    building_id: Annotated[
        Id, Field(description="The building ID to which this part belongs")
    ]
