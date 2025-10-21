"""Infrastructure feature models for Overture Maps base theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.base.infrastructure.enums import (
    InfrastructureClass,
    InfrastructureSubtype,
)
from overture.schema.base.models import SourcedFromOpenStreetMap
from overture.schema.base.types import Height
from overture.schema.core import (
    OvertureFeature,
)
from overture.schema.core.models import Stacked
from overture.schema.core.names import Named
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)

from ..enums import SurfaceMaterial


class Infrastructure(
    OvertureFeature[Literal["base"], Literal["infrastructure"]],
    Named,
    Stacked,
    SourcedFromOpenStreetMap,
):
    """Various features from OpenStreetMap such as bridges, airport runways, aerialways,
    or communication towers and lines."""

    model_config = ConfigDict(title="Infrastructure Schema")

    # Core

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(
            GeometryType.POINT,
            GeometryType.LINE_STRING,
            GeometryType.POLYGON,
            GeometryType.MULTI_POLYGON,
        ),
        Field(description="Geometry (Point, LineString, Polygon, or MultiPolygon)"),
    ]

    # Required

    class_: Annotated[InfrastructureClass, Field(alias="class")]
    subtype: InfrastructureSubtype

    # Optional

    height: Height | None = None
    surface: SurfaceMaterial | None = None
