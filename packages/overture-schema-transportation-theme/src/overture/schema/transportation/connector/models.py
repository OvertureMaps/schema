"""Connector feature models for Overture Maps transportation theme."""

from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core.base import (
    OvertureFeature,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint


class Connector(OvertureFeature):
    """Connector feature model."""

    # Core

    theme: Literal["transportation"] = Field(..., description="Feature theme")
    type: Literal["connector"] = Field(..., description="Feature type")
    geometry: Annotated[Geometry, GeometryTypeConstraint("Point")] = Field(
        ..., description="Geometry (Point)"
    )
