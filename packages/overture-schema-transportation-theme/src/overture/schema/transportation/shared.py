"""Common transportation theme structures and enums."""

from enum import Enum
from typing import Annotated

from pydantic import Field

from overture.schema.core.base import StrictBaseModel
from overture.schema.core.scoping import (
    GeometricRangeScope,
    HeadingScope,
    PurposeOfUseScope,
    RecognizedStatusScope,
    TemporalScope,
    TravelModeScope,
    VehicleScope,
)
from overture.schema.core.transportation import (
    Speed,
)
from overture.schema.validation import (
    CompositeUniqueConstraint,
    UniqueItemsConstraint,
    WhitespaceConstraint,
    at_least_one_of,
)
from overture.schema.validation.types import WikidataId


class SegmentSubtype(str, Enum):
    """Transportation segment subtype classification."""

    ROAD = "road"
    RAIL = "rail"
    WATER = "water"


class SegmentSubclass(str, Enum):
    """Transportation segment subclassification."""

    LINK = "link"  # Connecting stretch (sliproad or ramp) between two road types
    SIDEWALK = "sidewalk"  # Footway that lies along a road
    CROSSWALK = "crosswalk"  # Footway that intersects other roads
    PARKING_AISLE = "parking_aisle"  # Service road intended for parking
    DRIVEWAY = "driveway"  # Service road intended for deliveries
    ALLEY = "alley"  # Service road intended for rear entrances, fire exits
    CYCLE_CROSSING = "cycle_crossing"  # Cycleway that intersects with other roads


class RoadClass(str, Enum):
    """Road classification enum."""

    MOTORWAY = "motorway"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    RESIDENTIAL = "residential"
    LIVING_STREET = "living_street"
    TRUNK = "trunk"
    UNCLASSIFIED = "unclassified"
    SERVICE = "service"
    PEDESTRIAN = "pedestrian"
    FOOTWAY = "footway"
    STEPS = "steps"
    PATH = "path"
    TRACK = "track"
    CYCLEWAY = "cycleway"
    BRIDLEWAY = "bridleway"
    UNKNOWN = "unknown"


class RailClass(str, Enum):
    """Rail classification enum."""

    FUNICULAR = "funicular"
    LIGHT_RAIL = "light_rail"
    MONORAIL = "monorail"
    NARROW_GAUGE = "narrow_gauge"
    STANDARD_GAUGE = "standard_gauge"
    SUBWAY = "subway"
    TRAM = "tram"
    UNKNOWN = "unknown"


class ConnectorReference(StrictBaseModel):
    """Reference to a connector with position information."""

    # Required

    connector_id: str = Field(..., description="Connector identifier")
    at: float = Field(
        ..., ge=0.0, le=1.0, description="Position along segment (0.0-1.0)"
    )


class AccessType(str, Enum):
    """Access level enumeration."""

    ALLOWED = "allowed"
    DENIED = "denied"
    DESIGNATED = "designated"


class DestinationLabelType(str, Enum):
    """Destination label type classification."""

    UNKNOWN = "unknown"
    STREET = "street"
    ROUTE_REF = "route_ref"
    TOWARD_ROUTE_REF = "toward_route_ref"


class RoadFlagType(str, Enum):
    """Road-specific flag types."""

    IS_BRIDGE = "is_bridge"
    IS_LINK = "is_link"  # Deprecated - will be removed in favor of link subclass
    IS_TUNNEL = "is_tunnel"
    IS_UNDER_CONSTRUCTION = "is_under_construction"
    IS_ABANDONED = "is_abandoned"
    IS_COVERED = "is_covered"
    IS_INDOOR = "is_indoor"


class RailFlagType(str, Enum):
    """Rail-specific flag types."""

    IS_BRIDGE = "is_bridge"
    IS_TUNNEL = "is_tunnel"  # Also used for subway class (though subways are occasionally above-ground)
    IS_UNDER_CONSTRUCTION = "is_under_construction"
    IS_ABANDONED = "is_abandoned"
    IS_COVERED = "is_covered"
    IS_PASSENGER = "is_passenger"
    IS_FREIGHT = "is_freight"
    IS_DISUSED = "is_disused"


class RoadSurface(str, Enum):
    """Road surface material types."""

    UNKNOWN = "unknown"
    PAVED = "paved"
    UNPAVED = "unpaved"
    GRAVEL = "gravel"
    DIRT = "dirt"
    PAVING_STONES = "paving_stones"
    METAL = "metal"


# Scoping condition models for when clauses
class SpeedLimitWhenClause(
    TemporalScope,
    HeadingScope,
    PurposeOfUseScope,
    RecognizedStatusScope,
    TravelModeScope,
    VehicleScope,
):
    """When clause for speed limit rules."""

    pass


class AccessRestrictionWhenClause(
    TemporalScope,
    HeadingScope,
    PurposeOfUseScope,
    RecognizedStatusScope,
    TravelModeScope,
    VehicleScope,
):
    """When clause for access restriction rules."""

    def __hash__(self) -> int:
        """Make AccessRestrictionWhenClause hashable."""
        return hash(
            (
                TemporalScope.__hash__(self),
                HeadingScope.__hash__(self),
                PurposeOfUseScope.__hash__(self),
                RecognizedStatusScope.__hash__(self),
                TravelModeScope.__hash__(self),
                VehicleScope.__hash__(self),
            )
        )


class ProhibitedTransitionWhenClause(
    HeadingScope,
    TemporalScope,
    PurposeOfUseScope,
    RecognizedStatusScope,
    TravelModeScope,
    VehicleScope,
):
    """When clause for prohibited transition rules."""

    pass


class DestinationWhenClause(HeadingScope):
    """When clause for destination rules."""

    pass


# Core rule models using mix-in composition
@at_least_one_of("max_speed", "min_speed")
class SpeedLimitRule(GeometricRangeScope):
    """Speed limit rule with scoping via when clause."""

    # Optional

    max_speed: Speed | None = Field(default=None, description="Maximum speed limit")
    min_speed: Speed | None = Field(default=None, description="Minimum speed limit")
    is_max_speed_variable: bool = Field(
        default=False, description="Whether maximum speed is variable"
    )
    when: SpeedLimitWhenClause | None = Field(
        default=None, description="Scoping conditions"
    )


class AccessRestrictionRule(GeometricRangeScope):
    """Access restriction rule with scoping via when clause."""

    # Required

    access_type: AccessType = Field(..., description="Access type")

    # Optional

    when: AccessRestrictionWhenClause | None = Field(
        default=None, description="Scoping conditions"
    )

    def __hash__(self) -> int:
        """Make AccessRestrictionRule hashable."""
        return hash((super().__hash__(), self.access_type, self.when))


class DestinationLabel(StrictBaseModel):
    """Destination label with type classification."""

    # Required

    value: str = Field(..., min_length=1, description="Label text")
    type: DestinationLabelType = Field(..., description="Label type")


class DestinationSignSymbol(str, Enum):
    """Valid destination sign symbols."""

    MOTORWAY = "motorway"
    AIRPORT = "airport"
    HOSPITAL = "hospital"
    CENTER = "center"
    INDUSTRIAL = "industrial"
    PARKING = "parking"


class HeadingType(str, Enum):
    """Heading type classification."""

    FORWARD = "forward"
    BACKWARD = "backward"


class DestinationRule(StrictBaseModel):
    """Destination signage rule with scoping via when clause."""

    # Required

    from_connector_id: str = Field(..., description="Source connector identifier")
    to_connector_id: str = Field(..., description="Target connector identifier")
    to_segment_id: str = Field(..., description="Target segment identifier")
    final_heading: HeadingType = Field(
        ..., description="Final direction on target segment"
    )
    labels: Annotated[
        list[DestinationLabel], CompositeUniqueConstraint("value", "type")
    ] = Field(..., min_length=1, description="Destination labels")

    # Optional

    symbols: Annotated[list[DestinationSignSymbol], UniqueItemsConstraint()] | None = (
        Field(default=None, description="Route symbols")
    )
    when: DestinationWhenClause | None = Field(
        default=None, description="Scoping conditions"
    )


class ProhibitedTransitionSequence(StrictBaseModel):
    """Sequence entry with connector and segment identifiers."""

    # Required

    connector_id: str = Field(..., description="Connector identifier")
    segment_id: str = Field(..., description="Segment identifier")


class ProhibitedTransitionRule(GeometricRangeScope):
    """Prohibited transition (turn restriction) rule."""

    # Required

    sequence: Annotated[
        list[ProhibitedTransitionSequence],
        CompositeUniqueConstraint("connector_id", "segment_id"),
    ] = Field(
        ...,
        min_length=1,
        description="Sequence of connectors defining the prohibited path",
    )
    final_heading: HeadingType = Field(..., description="Required final heading")

    # Optional

    when: ProhibitedTransitionWhenClause | None = Field(
        default=None, description="Scoping conditions"
    )


class RoadFlagRule(GeometricRangeScope):
    """Road-specific flag rule with geometric scoping only."""

    # Required

    values: Annotated[list[RoadFlagType], UniqueItemsConstraint()] = Field(
        ..., min_length=1, description="Road flag values"
    )


class RailFlagRule(GeometricRangeScope):
    """Rail-specific flag rule with geometric scoping only."""

    # Required

    values: Annotated[list[RailFlagType], UniqueItemsConstraint()] = Field(
        ..., min_length=1, description="Rail flag values"
    )


class WidthRule(GeometricRangeScope):
    """Width rule with linear referencing."""

    # Required

    value: int | float = Field(..., description="Width value")


class SurfaceRule(GeometricRangeScope):
    """Surface material rule with linear referencing."""

    # Required

    value: RoadSurface = Field(..., description="Surface material")


class LevelRule(GeometricRangeScope):
    """Level/elevation rule with linear referencing."""

    # Required

    value: int = Field(..., description="Level/elevation value")


class SubclassRule(GeometricRangeScope):
    """Subclass rule with linear referencing."""

    # Required

    value: str = Field(..., description="Subclass value")


class RouteReference(GeometricRangeScope):
    """Route reference with linear referencing support."""

    # Optional

    name: Annotated[str, WhitespaceConstraint()] | None = Field(
        default=None, min_length=1, description="Route name"
    )
    network: Annotated[str, WhitespaceConstraint()] | None = Field(
        default=None, min_length=1, description="Route network"
    )
    ref: Annotated[str, WhitespaceConstraint()] | None = Field(
        default=None, min_length=1, description="Route reference number"
    )
    symbol: Annotated[str, WhitespaceConstraint()] | None = Field(
        default=None, min_length=1, description="Route symbol URL"
    )
    wikidata: WikidataId | None = Field(default=None, description="Wikidata identifier")
