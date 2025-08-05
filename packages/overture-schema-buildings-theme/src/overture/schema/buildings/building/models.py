"""Building feature models for Overture Maps buildings theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.core import Feature
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.models import Named, Stacked

from ..models import Shape
from .enums import (
    BuildingClass,
    Subtype,
)


class Building(
    Feature[Literal["buildings"], Literal["building"]], Named, Stacked, Shape
):
    """A building is a man-made structure with a roof that exists permanently in one place. Buildings are compatible with GeoJSON Polygon features."""

    model_config = ConfigDict(title="building")

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Polygon", "MultiPolygon"),
        Field(
            description="""A regular building's geometry is defined as its footprint or roofprint (if traced from aerial/satellite imagery). It MUST be a Polygon or MultiPolygon as defined by the GeoJSON schema.""",
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
