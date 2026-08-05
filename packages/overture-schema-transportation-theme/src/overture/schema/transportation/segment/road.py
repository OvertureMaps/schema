"""Road segment and its supporting types."""

import textwrap
from enum import Enum
from typing import Annotated, Literal, NewType

from pydantic import BaseModel, ConfigDict, Field

from overture.schema.common.scoping import Heading, Scope, scoped
from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields, require_any_of
from overture.schema.system.ref import Id, Reference, Relationship
from overture.schema.system.string import StrippedString, WikidataId

from ..connector import Connector
from ._common import (
    ProhibitedTransitions,
    SegmentSubtype,
    SpeedLimits,
    TransportationSegment,
    WidthRules,
)


class RoadClass(str, DocumentedEnum):
    """Captures the kind of road and its position in the road network hierarchy."""

    MOTORWAY = "motorway"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    RESIDENTIAL = "residential"
    LIVING_STREET = (
        "living_street",
        "Similar to residential but has implied legal restriction for motor vehicles (which can vary country by country)",
    )
    TRUNK = "trunk"
    UNCLASSIFIED = (
        "unclassified",
        "Known roads, paved, but subordinate to all of: motorway, trunk, primary, secondary, tertiary",
    )
    SERVICE = (
        "service",
        "Provides vehicle access to a feature (such as a building), typically not part of the public street network",
    )
    PEDESTRIAN = "pedestrian"
    FOOTWAY = ("footway", "Minor segments mainly used by pedestrians")
    STEPS = "steps"
    PATH = "path"
    TRACK = "track"
    CYCLEWAY = "cycleway"
    BRIDLEWAY = ("bridleway", "Similar to track but has implied access only for horses")
    UNKNOWN = "unknown"


class RoadSubclass(str, DocumentedEnum):
    """Refines expected usage of the segment, must not overlap."""

    LINK = ("link", "Connecting stretch (sliproad or ramp) between two road types")
    SIDEWALK = ("sidewalk", "Footway that lies along a road")
    CROSSWALK = ("crosswalk", "Footway that intersects other roads")
    PARKING_AISLE = ("parking_aisle", "Service road intended for parking")
    DRIVEWAY = ("driveway", "Service road intended for deliveries")
    ALLEY = ("alley", "Service road intended for rear entrances, fire exits")
    CYCLE_CROSSING = ("cycle_crossing", "Cycleway that intersects with other roads")


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class RoadSubclassRule(BaseModel):
    """Set of subclasses scoped along segment."""

    value: RoadSubclass


RoadSubclassRules = NewType(
    "RoadSubclassRules",
    Annotated[
        list[RoadSubclassRule],
        Field(description="Set of subclasses scoped along segment"),
    ],
)


class RoadFlag(str, DocumentedEnum):
    """Simple flags that can be on or off for a road segment.

    Specifies physical characteristics and can overlap.
    """

    IS_BRIDGE = "is_bridge"
    IS_LINK = (
        "is_link",
        "Deprecated: will be removed in a future release in favor of the `link` subclass",
    )
    IS_TUNNEL = "is_tunnel"
    IS_UNDER_CONSTRUCTION = "is_under_construction"
    IS_ABANDONED = "is_abandoned"
    IS_COVERED = "is_covered"
    IS_INDOOR = "is_indoor"


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class RoadFlagRule(BaseModel):
    """Road-specific flag rule with geometric scoping only."""

    values: Annotated[list[RoadFlag], Field(min_length=1), UniqueItemsConstraint()]


RoadFlags = NewType(
    "RoadFlags",
    Annotated[
        list[RoadFlagRule],
        Field(
            min_length=1,
            description=textwrap.dedent("""
                Set of boolean attributes applicable to roads. May be specified either as a
                single flag array of flag values, or as an array of flag rules.
            """).strip(),
        ),
        UniqueItemsConstraint(),
    ],
)


class RoadSurface(str, Enum):
    """Physical surface of the road."""

    UNKNOWN = "unknown"
    PAVED = "paved"
    UNPAVED = "unpaved"
    GRAVEL = "gravel"
    DIRT = "dirt"
    PAVING_STONES = "paving_stones"
    METAL = "metal"


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class RoadSurfaceRule(BaseModel):
    """
    Specifies the physical surface of a road segment or a linearly-referenced subsegment of the road
    segment.
    """

    value: RoadSurface


# We should likely restrict the available surface types to the subset of the common OSM surface=* tag values that are useful both for routing and for map tile rendering.
RoadSurfaces = NewType(
    "RoadSurfaces",
    Annotated[
        list[RoadSurfaceRule],
        Field(
            min_length=1,
            description=textwrap.dedent("""
                Physical surface of the road. May either be specified as a single global value
                for the segment, or as an array of surface rules.
            """).strip(),
        ),
        UniqueItemsConstraint(),
    ],
)


class DestinationLabelType(str, Enum):
    """
    Indicates what special symbol/icon is present on a signpost, visible as road marking or
    similar.
    """

    STREET = "street"
    COUNTRY = "country"
    ROUTE_REF = "route_ref"
    TOWARD_ROUTE_REF = "toward_route_ref"
    UNKNOWN = "unknown"


@no_extra_fields
class DestinationLabels(BaseModel):
    """The type of object of the destination label."""

    model_config = ConfigDict(frozen=True)

    # Required

    value: Annotated[
        StrippedString,
        Field(min_length=1, description="Names the object that is reached"),
    ]
    type: DestinationLabelType


class DestinationSignSymbol(str, DocumentedEnum):
    """
    Indicates what special symbol/icon is present on a signpost, visible as road marking or
    similar.
    """

    MOTORWAY = "motorway"
    AIRPORT = "airport"
    HOSPITAL = "hospital"
    CENTER = (
        "center",
        "Center of a locality, city center or downtown, from centre in raw OSM value",
    )
    INDUSTRIAL = "industrial"
    PARKING = "parking"
    BUS = "bus"
    TRAIN_STATION = "train_station"
    REST_AREA = "rest_area"
    FERRY = "ferry"
    MOTORROAD = "motorroad"
    FUEL = "fuel"
    VIEWPOINT = "viewpoint"
    FUEL_DIESEL = "fuel_diesel"
    FOOD = ("food", "'food', 'restaurant' in OSM")
    LODGING = "lodging"
    INFO = "info"
    CAMP_SITE = "camp_site"
    INTERCHANGE = "interchange"
    RESTROOMS = ("restrooms", "'toilets' in OSM")


@require_any_of("labels", "symbols")
@no_extra_fields
@scoped(Scope.HEADING)
class DestinationRule(BaseModel):
    """
    A single scoped rule describing the destinations reachable by following a transition from the
    current segment onto the segment `to_segment_id` via the connector `to_connector_id` in
    the `final_heading` direction.

    The destination is described as it appears in real-world signage through text `labels` and/or
    pictographic `symbols`. Heading-scoped to the approach direction on the current segment.
    """

    # Required

    from_connector_id: Annotated[
        Id,
        Reference(Relationship.ASSOCIATION, Connector, role="signposted_from"),
        Field(
            description=textwrap.dedent("""
                Identifies the point of physical connection on this segment before which the
                destination sign or marking is visible.
            """).strip(),
        ),
    ]
    to_connector_id: Annotated[
        Id,
        Reference(Relationship.ASSOCIATION, Connector, role="transitions_through"),
        Field(
            description=textwrap.dedent("""
                Identifies the point of physical connection on the segment identified by
                'to_segment_id' to transition to for reaching the destination(s).
            """).strip(),
        ),
    ]
    to_segment_id: Annotated[
        Id,
        Reference(
            Relationship.ASSOCIATION, TransportationSegment, role="transitions_to"
        ),
        Field(
            description=textwrap.dedent("""
                Identifies the segment to transition to reach the destination(s) labeled on the
                sign or marking.
            """).strip(),
        ),
    ]
    final_heading: Annotated[
        Heading,
        Field(
            description=textwrap.dedent("""
                Direction of travel on the segment identified by 'to_segment_id' that leads to
                the destination.
            """).strip(),
        ),
    ]

    # Optional

    labels: Annotated[
        list[DestinationLabels] | None,
        Field(
            min_length=1,
            description="Labeled destinations that can be reached by following the segment.",
        ),
        UniqueItemsConstraint(),
    ] = None
    symbols: Annotated[
        list[DestinationSignSymbol] | None,
        Field(
            description=textwrap.dedent("""
                A collection of symbols or icons present on the sign next to current destination
                label.
            """).strip()
        ),
        UniqueItemsConstraint(),
    ] = None


Destinations = NewType(
    "Destinations",
    Annotated[
        list[DestinationRule],
        Field(
            description=textwrap.dedent("""
                Describes objects that can be reached by following a transportation segment in the
                same way those objects are described on signposts or ground writing that a
                traveller following the segment would observe in the real world. This allows
                navigation systems to refer to signs and observable writing that a traveller
                actually sees.
            """).strip()
        ),
    ],
)


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class RouteReference(BaseModel):
    """Route reference with linear referencing support."""

    # Optional

    name: Annotated[
        StrippedString | None, Field(min_length=1, description="Full name of the route")
    ] = None
    network: Annotated[
        StrippedString | None,
        Field(
            min_length=1,
            description="Name of the highway system this route belongs to",
        ),
    ] = None
    ref: Annotated[
        StrippedString | None,
        Field(min_length=1, description="Code or number used to reference the route"),
    ] = None
    symbol: Annotated[
        StrippedString | None,
        Field(min_length=1, description="URL or description of route signage"),
    ] = None
    wikidata: WikidataId | None = None


Routes = NewType(
    "Routes",
    Annotated[
        list[RouteReference], Field(description="Routes this segment belongs to")
    ],
)


class RoadSegment(TransportationSegment):
    """Road segment properties."""

    model_config = ConfigDict(title="segment (road)")

    # Discriminator

    subtype: Literal[SegmentSubtype.ROAD]

    # Required

    class_: Annotated[RoadClass, Field(alias="class")]

    # Optional

    destinations: Destinations | None = None
    prohibited_transitions: Annotated[
        ProhibitedTransitions | None,
        Field(
            description=textwrap.dedent("""
            Rules for when transition to a connected segment is not allowed (commonly known as turn
            restrictions).
        """).strip()
        ),
    ] = None
    road_flags: RoadFlags | None = None
    road_surface: Annotated[
        RoadSurfaces | None,
        Field(
            description=textwrap.dedent("""
            Rules describing the physical surface of the road.
        """).strip()
        ),
    ] = None
    routes: Routes | None = None
    speed_limits: SpeedLimits | None = None
    subclass: RoadSubclass | None = None
    subclass_rules: RoadSubclassRules | None = None
    width_rules: WidthRules | None = None
