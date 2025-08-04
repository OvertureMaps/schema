"""Land use feature models for Overture Maps base theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.base.land_use.enums import LandUseClass, LandUseSubtype
from overture.schema.base.models import SourcedFromOpenStreetMap
from overture.schema.base.types import Elevation
from overture.schema.core import (
    OvertureFeature,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.models import Named, Stacked

from ..enums import SurfaceMaterial


class LandUse(OvertureFeature, Named, Stacked, SourcedFromOpenStreetMap):
    """Land use features from OpenStreetMap"""

    model_config = ConfigDict(title="land_use")

    # Core

    theme: Literal["base"]
    type: Literal["land_use"]
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Point", "LineString", "Polygon", "MultiPolygon"),
        Field(
            description="Classifications of the human use of a section of land. Translates `landuse` from OpenStreetMap tag from OpenStreetMap.",
        ),
    ]

    # Required

    class_: Annotated[LandUseClass, Field(alias="class")]
    subtype: LandUseSubtype

    # Optional

    elevation: Elevation | None = None
    surface: SurfaceMaterial | None = None
