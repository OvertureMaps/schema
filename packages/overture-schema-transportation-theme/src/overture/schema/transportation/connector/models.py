"""Connector feature models for Overture Maps transportation theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.core import (
    Feature,
)
from overture.schema.foundation.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)


class Connector(Feature[Literal["transportation"], Literal["connector"]]):
    """Connectors create physical connections between segments.

    Connectors are compatible with GeoJSON Point features.
    """

    model_config = ConfigDict(title="connector")

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POINT),
        Field(
            description="Position of the connector",
        ),
    ]
