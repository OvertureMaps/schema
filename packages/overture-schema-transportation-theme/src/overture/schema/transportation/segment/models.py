"""Segment feature models for Overture Maps transportation theme."""

from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core.base import (
    OvertureFeature,
    StrictBaseModel,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.names import (
    NamesContainer,
)
from overture.schema.core.scoping import (
    GeometricRangeScope,
    ScopingConditions,
)
from overture.schema.validation import (
    CompositeUniqueConstraint,
)
from overture.schema.validation.constraints import UniqueItemsConstraint

from ..shared import (
    AccessRestrictionRule as StrictAccessRestrictionRule,
)
from ..shared import (
    ConnectorReference,
    RailClass,
    RoadClass,
    SegmentSubclass,
    SegmentSubtype,
)
from ..shared import (
    DestinationRule as StrictDestinationRule,
)
from ..shared import (
    LevelRule as StrictLevelRule,
)
from ..shared import (
    ProhibitedTransitionRule as StrictProhibitedTransitionRule,
)
from ..shared import (
    RailFlagRule as StrictRailFlagRule,
)
from ..shared import (
    RoadFlagRule as StrictRoadFlagRule,
)
from ..shared import (
    RouteReference as StrictRouteReference,
)
from ..shared import (
    SpeedLimitRule as StrictSpeedLimitRule,
)
from ..shared import (
    SubclassRule as StrictSubclassRule,
)
from ..shared import (
    SurfaceRule as StrictSurfaceRule,
)
from ..shared import (
    WidthRule as StrictWidthRule,
)


class LevelRule(GeometricRangeScope):
    """Level/elevation rule with scoping."""

    # Required

    value: int = Field(
        ..., description="Level value (0=ground, positive=above, negative=below)"
    )

    # Optional

    when: ScopingConditions | None = Field(
        default=None, description="Scoping conditions"
    )


class RailFlags(StrictBaseModel):
    """Rail-specific boolean flags."""

    # Optional

    is_bridge: bool | None = Field(default=None, description="Is bridge")
    is_tunnel: bool | None = Field(default=None, description="Is tunnel")
    is_seasonal: bool | None = Field(default=None, description="Is seasonal")
    is_construction: bool | None = Field(default=None, description="Under construction")
    service: Literal["yard", "siding", "spur", "crossover"] | None = Field(
        default=None, description="Rail service type"
    )


class TransportationSegment(OvertureFeature):
    """Common segment properties."""

    # Core

    theme: Literal["transportation"] = Field(..., description="Feature theme")
    type: Literal["segment"] = Field(..., description="Feature type")
    geometry: Annotated[Geometry, GeometryTypeConstraint("LineString")] = Field(
        ..., description="Geometry (LineString)"
    )

    # Required

    # Should not be confused with a transport mode. A segment kind has an (implied) set of default
    # transport modes.
    subtype: SegmentSubtype = Field(
        ..., description="Broad category of transportation segment."
    )

    # Optional

    access_restrictions: (
        Annotated[
            list[StrictAccessRestrictionRule],
            UniqueItemsConstraint(),
        ]
        | None
    ) = Field(default=None, min_length=1, description="Access restriction rules")
    connectors: (
        Annotated[
            list[ConnectorReference], CompositeUniqueConstraint("connector_id", "at")
        ]
        | None
    ) = Field(default=[], description="Connector references")
    level: int = Field(
        default=0, description="Z-order of the feature where 0 is visual level"
    )
    level_rules: list[StrictLevelRule] | None = Field(
        default=None,
        description="Defines the Z-order, i.e. stacking order, of the road segment.",
    )
    names: NamesContainer | None = Field(
        default=None, description="Properties defining the names of a feature."
    )
    routes: list[StrictRouteReference] | None = Field(
        default=None, description="Routes this segment belongs to"
    )
    subclass_rules: list[StrictSubclassRule] | None = Field(
        default=None, description="Set of subclasses scoped along segment"
    )


class RoadSegment(TransportationSegment):
    """Road segment feature model."""

    # Discriminator

    subtype: Literal[SegmentSubtype.ROAD]

    # Required

    class_: RoadClass = Field(
        ...,
        alias="class",
        description="Captures the kind of road and its position in the road network hierarchy.",
    )

    # Optional

    destinations: list[StrictDestinationRule] | None = Field(
        default=None, description="Destination labels"
    )
    prohibited_transitions: list[StrictProhibitedTransitionRule] | None = Field(
        default=None, description="Turn restrictions"
    )
    road_flags: list[StrictRoadFlagRule] | None = Field(
        default=None, description="Road-specific flags"
    )
    road_surface: list[StrictSurfaceRule] | None = Field(
        default=None, description="Road surface rules"
    )
    speed_limits: list[StrictSpeedLimitRule] | None = Field(
        default=None, description="Speed limit rules"
    )
    subclass: SegmentSubclass | None = Field(
        default=None,
        description="Refines expected usage of the segment, must not overlap.",
    )
    width_rules: list[StrictWidthRule] | None = Field(
        default=None, min_length=1, description="Width rules"
    )


class RailSegment(TransportationSegment):
    """Rail segment feature model."""

    # Discriminator

    subtype: Literal[SegmentSubtype.RAIL]

    # Required

    class_: RailClass = Field(
        ..., alias="class", description="Captures the kind of rail segment"
    )

    # Optional

    rail_flags: list[StrictRailFlagRule] | None = Field(
        default=None, description="Rail-specific flags"
    )


class WaterSegment(TransportationSegment):
    """Water segment feature model."""

    # Discriminator

    subtype: Literal[SegmentSubtype.WATER]


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
