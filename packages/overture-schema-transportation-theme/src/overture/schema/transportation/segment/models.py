"""Segment feature models for Overture Maps transportation theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.core import (
    Feature,
)
from overture.schema.core.models import (
    Named,
)
from overture.schema.foundation.constraint import UniqueItemsConstraint
from overture.schema.foundation.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)

from ..enums import RailClass, RoadClass, Subclass, Subtype
from ..models import ConnectorReference
from ..types import (
    AccessRules,
    Destinations,
    LevelRules,
    ProhibitedTransitions,
    RailFlags,
    RoadFlags,
    Routes,
    SpeedLimits,
    SubclassRules,
    Surfaces,
    WidthRules,
)


class TransportationSegment(
    Feature[Literal["transportation"], Literal["segment"]], Named
):
    """Common Segment Properties."""

    model_config = ConfigDict(title="segment")

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.LINE_STRING),
        Field(description="Segment centerline"),
    ]

    # Required

    # Should not be confused with a transport mode. A segment kind has an (implied) set of default
    # transport modes.
    subtype: Annotated[
        Subtype, Field(description="Broad category of transportation segment.")
    ]

    # Optional

    access_restrictions: AccessRules | None = None
    # Contains the GERS ID and relative position between 0 and 1 of a connector feature along the segment.
    connectors: Annotated[
        list[ConnectorReference] | None,
        Field(
            default=[],
            min_length=2,
            description="List of connectors which this segment is physically connected to and their relative location. Each connector is a possible routing decision point, meaning it defines a place along the segment in which there is possibility to transition to other segments which share the same connector.",
        ),
        UniqueItemsConstraint(),
    ] = []
    level_rules: LevelRules | None = None
    routes: Routes | None = None
    subclass_rules: SubclassRules | None = None


class RoadSegment(TransportationSegment):
    """Road Segment Properties."""

    model_config = ConfigDict(title="Road-Specific Properties")

    # Discriminator

    subtype: Literal[Subtype.ROAD]

    # Required

    class_: Annotated[RoadClass, Field(alias="class")]

    # Optional

    destinations: Destinations | None = None
    prohibited_transitions: ProhibitedTransitions | None = None
    road_flags: RoadFlags | None = None
    road_surface: Surfaces | None = None
    speed_limits: SpeedLimits | None = None
    subclass: Subclass | None = None
    width_rules: WidthRules | None = None


class RailSegment(TransportationSegment):
    """Rail Segment Properties."""

    model_config = ConfigDict(title="Rail-Specific Properties")

    # Discriminator

    subtype: Literal[Subtype.RAIL]

    # Required

    class_: Annotated[RailClass, Field(alias="class")]

    # Optional

    rail_flags: RailFlags | None = None


class WaterSegment(TransportationSegment):
    """Water Segment Properties."""

    model_config = ConfigDict(title="Water-Specific Properties")

    # Discriminator

    subtype: Literal[Subtype.WATER]


Segment = Annotated[
    RoadSegment | RailSegment | WaterSegment, Field(discriminator="subtype")
]

# Explicitly assign docstring to the Segment type alias
Segment.__doc__ = """Transportation segment model representing linear travel infrastructure.

Encompasses road, rail, and water transportation segments. Models linear features that enable
movement of people, goods, and vehicles through structured networks. Each segment type provides
specialized attributes for its respective transportation mode.

Supports routing, mapping, navigation, and transportation network analysis through rich geometric
and attribute data.
"""
