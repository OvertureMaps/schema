"""Water feature models for Overture Maps base theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.base.models import SourcedFromOpenStreetMap
from overture.schema.base.water.enums import WaterClass, WaterSubtype
from overture.schema.core import (
    Feature,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.models import Named, Stacked


class Water(
    Feature[Literal["base"], Literal["water"]], Stacked, Named, SourcedFromOpenStreetMap
):
    """Physical representations of inland and ocean marine surfaces.

    Translates `natural` and `waterway` tags from OpenStreetMap.
    """

    model_config = ConfigDict(title="water")

    # Core

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Point", "LineString", "Polygon", "MultiPolygon"),
        Field(
            description="Geometry (Point, LineString, Polygon, or MultiPolygon)",
        ),
    ]

    # Required

    class_: Annotated[
        WaterClass,
        Field(
            default=WaterClass.WATER,
            alias="class",
        ),
    ] = WaterClass.WATER
    subtype: Annotated[
        WaterSubtype,
        Field(
            default=WaterSubtype.WATER,
        ),
    ] = WaterSubtype.WATER

    # Optional

    is_intermittent: Annotated[
        bool | None, Field(description="Is it intermittent water or not", strict=True)
    ] = None
    is_salt: Annotated[
        bool | None, Field(description="Is it salt water or not", strict=True)
    ] = None
