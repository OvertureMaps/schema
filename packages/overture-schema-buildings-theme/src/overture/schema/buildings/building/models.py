"""Building feature models for Overture Maps buildings theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.core import Feature
from overture.schema.core.models import Named, Stacked
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)

from ..models import Shape
from .enums import (
    BuildingClass,
    Subtype,
)


class Building(
    Feature[Literal["buildings"], Literal["building"]], Named, Stacked, Shape
):
    """A building is a man-made structure with a roof that exists permanently in one
    place.

    Buildings are compatible with GeoJSON Polygon features.
    """

    model_config = ConfigDict(title="building")

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(
            description="""The building's footprint or roofprint (if traced from aerial/satellite imagery).""",
        ),
    ]

    # Optional

    subtype: Subtype | None = None
    class_: Annotated[BuildingClass | None, Field(alias="class")] = None
    has_parts: Annotated[
        bool | None,
        Field(
            description="Flag indicating whether the building has parts",
            strict=True,
        ),
    ] = None
