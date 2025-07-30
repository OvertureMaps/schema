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

    when: ScopingConditions = Field(default=None, description="Scoping conditions")


class RailFlags(StrictBaseModel):
    """Rail-specific boolean flags."""

    # Optional

    is_bridge: bool = Field(default=None, description="Is bridge")
    is_tunnel: bool = Field(default=None, description="Is tunnel")
    is_seasonal: bool = Field(default=None, description="Is seasonal")
    is_construction: bool = Field(default=None, description="Under construction")
    service: Literal["yard", "siding", "spur", "crossover"] = Field(
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

    level: int = Field(
        default=0, description="Z-order of the feature where 0 is visual level"
    )
    level_rules: list[StrictLevelRule] = Field(
        default=[],
        description="Defines the Z-order, i.e. stacking order, of the road segment.",
    )
    subclass_rules: list[StrictSubclassRule] = Field(
        default=[], description="Set of subclasses scoped along segment"
    )
    # Should not be confused with a transport mode. A segment kind has an (implied) set of default
    # transport modes.
    subtype: SegmentSubtype = Field(
        ..., description="Broad category of transportation segment."
    )

    # Optional

    access_restrictions: Annotated[
        list[StrictAccessRestrictionRule],
        UniqueItemsConstraint(),
    ] = Field(default=[], min_length=1, description="Access restriction rules")
    connectors: Annotated[
        list[ConnectorReference], CompositeUniqueConstraint("connector_id", "at")
    ] = Field(default=[], description="Connector references")
    names: NamesContainer = Field(
        default=None, description="Properties defining the names of a feature."
    )
    routes: list[StrictRouteReference] = Field(
        default=[], description="Routes this segment belongs to"
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

    destinations: list[StrictDestinationRule] = Field(
        default=None, description="Destination labels"
    )
    prohibited_transitions: list[StrictProhibitedTransitionRule] = Field(
        default=None, description="Turn restrictions"
    )
    road_flags: list[StrictRoadFlagRule] = Field(
        default=None, description="Road-specific flags"
    )
    road_surface: list[StrictSurfaceRule] = Field(
        default=None, description="Road surface rules"
    )
    speed_limits: list[StrictSpeedLimitRule] = Field(
        default=None, description="Speed limit rules"
    )
    subclass: SegmentSubclass = Field(
        default=None,
        description="Refines expected usage of the segment, must not overlap.",
    )
    width_rules: list[StrictWidthRule] = Field(
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

    rail_flags: list[StrictRailFlagRule] = Field(
        default=None, description="Rail-specific flags"
    )


class WaterSegment(TransportationSegment):
    """Water segment feature model."""

    # Discriminator

    subtype: Literal[SegmentSubtype.WATER]


Segment = Annotated[
    RoadSegment | RailSegment | WaterSegment, Field(discriminator="subtype")
]
