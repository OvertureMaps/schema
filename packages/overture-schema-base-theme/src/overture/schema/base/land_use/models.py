"""Land use feature models for Overture Maps base theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.base.land_use.enums import LandUseClass, LandUseSubtype
from overture.schema.base.models import SourcedFromOpenStreetMap
from overture.schema.base.types import Elevation
from overture.schema.core import (
    Feature,
)
from overture.schema.core.models import Named, Stacked
from overture.schema.foundation.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)

from ..enums import SurfaceMaterial


class LandUse(
    Feature[Literal["base"], Literal["land_use"]],
    Named,
    Stacked,
    SourcedFromOpenStreetMap,
):
    """Land use features from OpenStreetMap."""

    model_config = ConfigDict(title="land_use")

    # Core

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(
            GeometryType.POINT,
            GeometryType.LINE_STRING,
            GeometryType.POLYGON,
            GeometryType.MULTI_POLYGON,
        ),
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
