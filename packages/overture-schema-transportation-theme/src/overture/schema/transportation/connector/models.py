"""Connector feature models for Overture Maps transportation theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.core import (
    Feature,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint


class Connector(Feature):
    """Connectors create physical connections between segments. Connectors are compatible with GeoJSON Point features."""

    model_config = ConfigDict(title="connector")

    # Core

    theme: Literal["transportation"]
    type: Literal["connector"]
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Point"),
        Field(
            description="Connector's geometry which MUST be a Point as defined by GeoJSON schema.",
        ),
    ]
