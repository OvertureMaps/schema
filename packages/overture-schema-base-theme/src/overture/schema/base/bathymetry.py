"""Bathymetry feature models for Overture Maps base theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.core import (
    OvertureFeature,
)
from overture.schema.core.models import CartographicallyHinted
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)

from ._common import Depth


class Bathymetry(
    OvertureFeature[Literal["base"], Literal["bathymetry"]], CartographicallyHinted
):
    """
    Bathymetry features provide topographic representations of underwater areas, such as parts of
    lake beds or ocean floors.
    """

    model_config = ConfigDict(title="bathymetry")

    # Overture Feature

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(
            description="Shape of the underwater area, which may be a polygon or multi-polygon."
        ),
    ]

    # Required

    depth: Depth
