"""Land feature models for Overture Maps base theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.base.land.enums import LandClass, LandSubtype
from overture.schema.base.models import SourcedFromOpenStreetMap
from overture.schema.base.types import Elevation
from overture.schema.core import (
    Feature,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.models import Named, Stacked

from ..enums import SurfaceMaterial


class Land(Feature, Named, Stacked, SourcedFromOpenStreetMap):
    """Physical representations of land surfaces. Global land derived from the inverse of OSM Coastlines. Translates `natural` tags from OpenStreetMap."""

    model_config = ConfigDict(title="land")

    # Core

    theme: Literal["base"]
    type: Literal["land"]
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Point", "LineString", "Polygon", "MultiPolygon"),
        Field(description="Geometry (Point, LineString, Polygon, or MultiPolygon)"),
    ]

    # Required

    class_: Annotated[LandClass, Field(default=LandClass.LAND, alias="class")] = (
        LandClass.LAND
    )
    subtype: Annotated[LandSubtype, Field(default=LandSubtype.LAND)] = LandSubtype.LAND

    # Optional

    elevation: Elevation | None = None
    surface: SurfaceMaterial | None = None
