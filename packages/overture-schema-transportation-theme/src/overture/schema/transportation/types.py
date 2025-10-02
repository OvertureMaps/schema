"""Transportation theme type aliases and annotated types."""

from typing import Annotated, NewType

from pydantic import Field

from overture.schema.system.constraint import UniqueItemsConstraint

from .models import (
    AccessRestrictionRule,
    DestinationRule,
    LevelRule,
    ProhibitedTransitionRule,
    RailFlagRule,
    RoadFlagRule,
    RouteReference,
    SpeedLimitRule,
    SubclassRule,
    SurfaceRule,
    WidthRule,
)

Destinations = NewType(
    "Destinations",
    Annotated[
        list[DestinationRule],
        Field(
            description="Describes objects that can be reached by following a transportation segment in the same way those objects are described on signposts or ground writing that a traveller following the segment would observe in the real world. This allows navigation systems to refer to signs and observable writing that a traveller actually sees."
        ),
    ],
)

Routes = NewType(
    "Routes",
    Annotated[
        list[RouteReference], Field(description="Routes this segment belongs to")
    ],
)

AccessRules = NewType(
    "AccessRules",
    Annotated[
        list[AccessRestrictionRule],
        Field(min_length=1, description="Rules governing access to this road segment"),
        UniqueItemsConstraint(),
    ],
)


SpeedLimits = NewType(
    "SpeedLimits",
    Annotated[
        list[SpeedLimitRule],
        Field(min_length=1, description="Rules governing speed on this road segment"),
        UniqueItemsConstraint(),
    ],
)

ProhibitedTransitions = NewType(
    "ProhibitedTransitions",
    Annotated[
        list[ProhibitedTransitionRule],
        Field(
            description="Rules preventing transitions from this segment to another segment."
        ),
    ],
)

RoadFlags = NewType(
    "RoadFlags",
    Annotated[
        list[RoadFlagRule],
        Field(
            min_length=1,
            description="Set of boolean attributes applicable to roads. May be specified either as a single flag array of flag values, or as an array of flag rules.",
        ),
        UniqueItemsConstraint(),
    ],
)

RailFlags = NewType(
    "RailFlags",
    Annotated[
        list[RailFlagRule],
        Field(
            min_length=1,
            description="Set of boolean attributes applicable to railways. May be specified either as a single flag array of flag values, or as an array of flag rules.",
        ),
        UniqueItemsConstraint(),
    ],
)

LevelRules = NewType(
    "LevelRules",
    Annotated[
        list[LevelRule],
        Field(
            description="Defines the Z-order, i.e. stacking order, of the road segment."
        ),
    ],
)

SubclassRules = NewType(
    "SubclassRules",
    Annotated[
        list[SubclassRule], Field(description="Set of subclasses scoped along segment")
    ],
)

# We should likely restrict the available surface types to the subset of the common OSM surface=* tag values that are useful both for routing and for map tile rendering.
Surfaces = NewType(
    "Surfaces",
    Annotated[
        list[SurfaceRule],
        Field(
            min_length=1,
            description="Physical surface of the road. May either be specified as a single global value for the segment, or as an array of surface rules.",
        ),
        UniqueItemsConstraint(),
    ],
)

WidthRules = NewType(
    "WidthRules",
    Annotated[
        list[WidthRule],
        Field(
            min_length=1,
            description="""Edge-to-edge width of the road modeled by this segment, in meters.

        Examples: (1) If this segment models a carriageway without sidewalk, this value represents the edge-to-edge width of the carriageway, inclusive of any shoulder. (2) If this segment models a sidewalk by itself, this value represents the edge-to-edge width of the sidewalk. (3) If this segment models a combined sidewalk and carriageway, this value represents the edge-to-edge width inclusive of sidewalk.""",
        ),
        UniqueItemsConstraint(),
    ],
)
