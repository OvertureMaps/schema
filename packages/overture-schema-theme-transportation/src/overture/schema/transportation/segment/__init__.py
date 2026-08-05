"""Transportation segment feature."""

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import Annotated

from pydantic import Field, Tag

from overture.schema.system.feature import Feature

from ._common import (
    AccessRule,
    AccessType,
    ConnectorReference,
    LevelRule,
    ProhibitedTransitionRule,
    ProhibitedTransitionSequenceEntry,
    SegmentSubtype,
    Speed,
    SpeedLimitRule,
    TransportationSegment,
    WidthRule,
)
from .rail import RailClass, RailFlag, RailFlagRule, RailSegment
from .road import (
    DestinationLabels,
    DestinationLabelType,
    DestinationRule,
    DestinationSignSymbol,
    RoadClass,
    RoadFlag,
    RoadFlagRule,
    RoadSegment,
    RoadSubclass,
    RoadSubclassRule,
    RoadSurface,
    RoadSurfaceRule,
    RouteReference,
)
from .water import WaterSegment

# The public `Segment` type: a discriminated union over the three subtype models, keyed on the
# `subtype` field. Assembled here because it depends on the subtype classes imported above.
Segment = Annotated[
    Annotated[RoadSegment, Tag(SegmentSubtype.ROAD)]
    | Annotated[RailSegment, Tag(SegmentSubtype.RAIL)]
    | Annotated[WaterSegment, Tag(SegmentSubtype.WATER)],
    Field(
        discriminator=Feature.field_discriminator(
            "subtype", RoadSegment, RailSegment, WaterSegment
        )
    ),
]

# Explicitly assign docstring to the Segment type alias
Segment.__doc__ = """Transportation segment model representing linear travel infrastructure.

Encompasses road, rail, and water transportation segments. Models linear features that enable
movement of people, goods, and vehicles through structured networks. Each segment type provides
specialized attributes for its respective transportation mode.

Supports routing, mapping, navigation, and transportation network analysis through rich geometric
and attribute data.
"""

__all__ = [
    "AccessRule",
    "AccessType",
    "ConnectorReference",
    "DestinationLabelType",
    "DestinationLabels",
    "DestinationRule",
    "DestinationSignSymbol",
    "LevelRule",
    "ProhibitedTransitionRule",
    "ProhibitedTransitionSequenceEntry",
    "RailClass",
    "RailFlag",
    "RailFlagRule",
    "RailSegment",
    "RoadClass",
    "RoadFlag",
    "RoadFlagRule",
    "RoadSegment",
    "RoadSubclass",
    "RoadSubclassRule",
    "RoadSurface",
    "RoadSurfaceRule",
    "RouteReference",
    "Segment",
    "SegmentSubtype",
    "Speed",
    "SpeedLimitRule",
    "TransportationSegment",
    "WaterSegment",
    "WidthRule",
]
