"""Connector feature models for Overture Maps transportation theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.core import (
    OvertureFeature,
)
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)


class Connector(OvertureFeature[Literal["transportation"], Literal["connector"]]):
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
