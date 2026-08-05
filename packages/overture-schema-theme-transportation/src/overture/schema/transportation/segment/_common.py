"""Shared, mode-independent segment models for the Overture Maps transportation theme.

This private module holds the pieces of the segment feature that are common to every segment
subtype (road, rail, water): the subtype discriminator, the base `TransportationSegment`
feature class, and the rule/reference models and type aliases used across subtypes. It mirrors
the `_common.py` convention used by the other refactored themes, scoped to the segment package.

The `Segment` discriminated union is intentionally NOT defined here; it must be assembled in
`segment/__init__.py` after the subtype modules (`.road`/`.rail`/`.water`) are imported,
because those modules import their base class from here. Keeping the base in `_common` and the
union in `__init__` is what breaks the import cycle.
"""

import textwrap
from typing import Annotated, Literal, NewType

from pydantic import BaseModel, ConfigDict, Field

from overture.schema.common import OvertureFeature
from overture.schema.common.level import Level
from overture.schema.common.names import Named
from overture.schema.common.scoping import Heading, Scope, scoped
from overture.schema.common.unit import SpeedUnit
from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.geometric import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.numeric import float64, int32
from overture.schema.system.ref import Id, Reference, Relationship

# Import `Connector` from its sibling module (not the theme package root) so this import does
# not depend on the transportation package's `__init__` having finished executing.
from ..connector import Connector


class SegmentSubtype(str, DocumentedEnum):
    """Transportation segment subtype classification."""

    ROAD = (
        "road",
        "A segment of the road network, travelled by motor vehicles, cyclists, pedestrians, etc.",
    )
    RAIL = (
        "rail",
        "A segment of the railway network, travelled by trains, trams, and other rail vehicles.",
    )
    WATER = (
        "water",
        "A segment of the navigable water network, travelled by vessels such as ferries and boats.",
    )


class AccessType(str, DocumentedEnum):
    """Whether access is allowed, denied, or allowed as designated."""

    ALLOWED = (
        "allowed",
        "Access is permitted.",
    )
    DENIED = (
        "denied",
        "Access is prohibited.",
    )
    DESIGNATED = (
        "designated",
        "Access is positively designated, typically by signage or regulation, for the relevant travel mode(s).",
    )


@no_extra_fields
@scoped(
    Scope.GEOMETRIC_RANGE,
    Scope.HEADING,
    Scope.PURPOSE_OF_USE,
    Scope.RECOGNIZED_STATUS,
    Scope.TEMPORAL,
    Scope.TRAVEL_MODE,
    Scope.VEHICLE,
)
class AccessRule(BaseModel):
    """
    A single scoped rule about who or what can use a segment (or a sub-segment of a segment).

    This rule can be scoped to apply only to linearly-referenced subsegment, a travel mode such as
    motor vehicle, a heading such as forward or backward, and to various other scopes as well. See
    the fields for the full list of available scopes.
    """

    model_config = ConfigDict(frozen=True)

    # Required

    access_type: AccessType


AccessRules = NewType(
    "AccessRules",
    Annotated[
        list[AccessRule],
        Field(min_length=1, description="Rules governing access to this road segment"),
        UniqueItemsConstraint(),
    ],
)


@no_extra_fields
@scoped(Scope.GEOMETRIC_POSITION)
class ConnectorReference(BaseModel):
    """
    Contains the GERS ID and relative position between 0 and 1 of a connector feature along the
    segment.
    """

    model_config = ConfigDict(frozen=True)

    # Required

    connector_id: Annotated[
        Id, Reference(Relationship.ASSOCIATION, Connector, role="connects_to")
    ]


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class LevelRule(BaseModel):
    """
    A single level rule defining the Z-order, i.e. stacking order, applicable within a given scope
    on the road segment.
    """

    value: Level


LevelRules = NewType(
    "LevelRules",
    Annotated[
        list[LevelRule],
        Field(
            description="Defines the Z-order, i.e. stacking order, of the road segment."
        ),
    ],
)


class TransportationSegment(
    OvertureFeature[Literal["transportation"], Literal["segment"]], Named
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
        SegmentSubtype, Field(description="Broad category of transportation segment.")
    ]

    # Optional

    access_restrictions: AccessRules | None = None
    # Contains the GERS ID and relative position between 0 and 1 of a connector feature along the segment.
    connectors: Annotated[
        list[ConnectorReference] | None,
        Field(
            min_length=2,
            description=textwrap.dedent("""
                List of connectors which this segment is physically connected to and their
                relative location. Each connector is a possible routing decision point,
                meaning it defines a place along the segment in which there is possibility to
                transition to other segments which share the same connector.
            """).strip(),
        ),
        UniqueItemsConstraint(),
    ] = []
    level_rules: LevelRules | None = None


@no_extra_fields
class ProhibitedTransitionSequenceEntry(BaseModel):
    """A segment/connector pair in a prohibited transition sequence."""

    model_config = ConfigDict(frozen=True)

    # Required

    connector_id: Annotated[
        Id,
        Reference(Relationship.ASSOCIATION, Connector, role="transitions_through"),
        Field(
            description=textwrap.dedent("""
                Identifies the point of physical connection between the previous segment in the
                sequence and the segment in this sequence entry.
            """).strip(),
        ),
    ]
    segment_id: Annotated[
        Id,
        Reference(
            Relationship.ASSOCIATION, TransportationSegment, role="transitions_to"
        ),
        Field(
            description=textwrap.dedent("""
                Identifies the segment that the previous segment in the sequence is physically
                connected to via the sequence entry's connector.
            """).strip(),
        ),
    ]


@no_extra_fields
@scoped(
    Scope.GEOMETRIC_RANGE,
    Scope.HEADING,
    Scope.PURPOSE_OF_USE,
    Scope.RECOGNIZED_STATUS,
    Scope.TEMPORAL,
    Scope.TRAVEL_MODE,
    Scope.VEHICLE,
)
class ProhibitedTransitionRule(BaseModel):
    """
    A single scoped rule identifying a transition from the current segment (or a sub-segment of it)
    to a connected segment that is not allowed.

    This rule can be scoped to apply only to linearly-referenced subsegment, a travel mode such as
    motor vehicle, a heading such as forward or backward, and to various other scopes as well. See
    the fields for the full list of available scopes.

    Terminology note: Prohibited transitions are more commonly referred to as turn restrictions.
    While the term turn restriction is simpler and more relatable, it is less precise because
    transitions between segments don't always require maneuvers that a human would describe as being
    a turn. For this reason, the Overture schema has opted for the more general and precise term
    prohibited transitions.
    """

    # Required

    sequence: Annotated[
        list[ProhibitedTransitionSequenceEntry],
        Field(
            min_length=1,
            description=textwrap.dedent("""
                Ordered sequence of connector/segment pairs that it is prohibited to follow
                from this segment.
            """).strip(),
        ),
        UniqueItemsConstraint(),
    ]
    final_heading: Annotated[
        Heading,
        Field(
            description=textwrap.dedent("""
                Direction of travel that is prohibited on the destination segment of the sequence.
            """).strip(),
        ),
    ]


ProhibitedTransitions = NewType(
    "ProhibitedTransitions",
    Annotated[
        list[ProhibitedTransitionRule],
        Field(
            description="Rules preventing transitions from this segment to another segment."
        ),
    ],
)


SpeedValue = NewType(
    "SpeedValue", Annotated[int32, Field(ge=1, le=350, description="Speed value")]
)


@no_extra_fields
class Speed(BaseModel):
    """A speed value, i.e. a certain number of distance units travelled per unit time."""

    model_config = ConfigDict(frozen=True)

    # Required

    value: SpeedValue
    unit: SpeedUnit


class SpeedLimitType(str, DocumentedEnum):
    """The kind of speed limit."""

    ADVISORY = (
        "advisory",
        "A recommended safe speed (e.g. before sharp curves or on ramps)",
    )
    MAXIMUM = "maximum"
    MINIMUM = "minimum"


@no_extra_fields
@scoped(
    Scope.GEOMETRIC_RANGE,
    Scope.HEADING,
    Scope.PURPOSE_OF_USE,
    Scope.RECOGNIZED_STATUS,
    Scope.TEMPORAL,
    Scope.TRAVEL_MODE,
    Scope.VEHICLE,
)
class SpeedLimitRule(BaseModel):
    """An individual speed limit rule."""

    # Required

    type: SpeedLimitType
    speed: Speed


SpeedLimits = NewType(
    "SpeedLimits",
    Annotated[
        list[SpeedLimitRule],
        Field(min_length=1, description="Rules governing speed on this road segment"),
        UniqueItemsConstraint(),
    ],
)


Width = NewType("Width", Annotated[float64, Field(gt=0)])


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class WidthRule(BaseModel):
    """
    Specifies the width of a segment or a linearly-referenced subsegment of a segment.
    """

    value: Annotated[
        Width,
        Field(
            description="Edge-to-edge width of the feature modeled by this segment, in meters."
        ),
    ]


WidthRules = NewType(
    "WidthRules",
    Annotated[
        list[WidthRule],
        Field(
            min_length=1,
            description=textwrap.dedent("""
                Edge-to-edge width of the feature modeled by this segment, in meters.

                Examples: (1) If this segment models a carriageway without sidewalk, this value
                represents the edge-to-edge width of the carriageway, inclusive of any shoulder.
                (2) If this segment models a sidewalk by itself, this value represents the
                edge-to-edge width of the sidewalk. (3) If this segment models a combined sidewalk
                and carriageway, this value represents the edge-to-edge width inclusive of sidewalk.
            """).strip(),
        ),
        UniqueItemsConstraint(),
    ],
)
