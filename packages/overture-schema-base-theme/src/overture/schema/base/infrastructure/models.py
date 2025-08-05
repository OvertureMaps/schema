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
    Feature,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.models import Named, Stacked

from ..enums import SurfaceMaterial


class Infrastructure(
    Feature[Literal["base"], Literal["infrastructure"]],
    Named,
    Stacked,
    SourcedFromOpenStreetMap,
):
    """Various features from OpenStreetMap such as bridges, airport runways, aerialways, or communication towers and lines."""

    model_config = ConfigDict(title="Infrastructure Schema")

    # Core

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Point", "LineString", "Polygon", "MultiPolygon"),
        Field(description="Geometry (Point, LineString, Polygon, or MultiPolygon)"),
    ]

    # Required

    class_: Annotated[InfrastructureClass, Field(alias="class")]
    subtype: InfrastructureSubtype

    # Optional

    height: Height | None = None
    surface: SurfaceMaterial | None = None
