"""Transportation theme models."""

from typing import Annotated, NewType

from pydantic import BaseModel, ConfigDict, Field

from overture.schema.core import OvertureFeature
from overture.schema.core.scoping import Heading, Scope, scoped
from overture.schema.core.types import (
    Level,
)
from overture.schema.core.unit import SpeedUnit
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import (
    no_extra_fields,
    require_any_of,
)
from overture.schema.system.primitive import float64, int32
from overture.schema.system.ref import Id, Reference, Relationship
from overture.schema.system.string import StrippedString, WikidataId

from .enums import (
    AccessType,
    DestinationLabelType,
    DestinationSignSymbol,
    RailFlag,
    RoadFlag,
    RoadSurface,
    Subclass,
)

SpeedValue = NewType(
    "SpeedValue", Annotated[int32, Field(ge=1, le=350, description="Speed value")]
)

Width = NewType("Width", Annotated[float64, Field(gt=0)])


def _connector_type() -> type[OvertureFeature]:
    from .connector import Connector

    return Connector


@no_extra_fields
@scoped(Scope.GEOMETRIC_POSITION)
class ConnectorReference(BaseModel):
    """Contains the GERS ID and relative position between 0 and 1 of a connector feature
    along the segment."""

    model_config = ConfigDict(frozen=True)

    # Required

    connector_id: Annotated[Id, Reference(Relationship.CONNECTS_TO, _connector_type())]


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


@require_any_of("labels", "symbols")
@no_extra_fields
@scoped(Scope.HEADING)
class DestinationRule(BaseModel):
    # Required

    from_connector_id: Annotated[
        Id,
        Field(
            description="Identifies the point of physical connection on this segment before which the destination sign or marking is visible.",
        ),
    ]
    to_connector_id: Annotated[
        Id,
        Field(
            description="Identifies the point of physical connection on the segment identified by 'to_segment_id' to transition to for reaching the destination(s).",
        ),
    ]
    to_segment_id: Annotated[
        Id,
        Field(
            description="Identifies the segment to transition to reach the destination(s) labeled on the sign or marking.",
        ),
    ]
    final_heading: Annotated[
        Heading,
        Field(
            description="Direction of travel on the segment identified by 'to_segment_id' that leads to the destination.",
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
            description="A collection of symbols or icons present on the sign next to current destination label."
        ),
        UniqueItemsConstraint(),
    ] = None


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


@no_extra_fields
class Speed(BaseModel):
    """A speed value, i.e. a certain number of distance units travelled per unit
    time."""

    model_config = ConfigDict(frozen=True)

    # Required

    value: SpeedValue
    unit: SpeedUnit


@no_extra_fields
class SequenceEntry(BaseModel):
    """A segment/connector pair in a prohibited transition sequence."""

    model_config = ConfigDict(frozen=True)

    # Required

    connector_id: Annotated[
        Id,
        Field(
            description="Identifies the point of physical connection between the previous segment in the sequence and the segment in this sequence entry.",
        ),
    ]
    segment_id: Annotated[
        Id,
        Field(
            description="Identifies the segment that the previous segment in the sequence is physically connected to via the sequence entry's connector.",
        ),
    ]


@no_extra_fields
@require_any_of("max_speed", "min_speed")
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

    # Optional

    max_speed: Speed | None = None
    min_speed: Speed | None = None
    is_max_speed_variable: Annotated[
        bool | None,
        Field(
            default=False,
            description="Indicates a variable speed corridor",
            strict=True,
        ),
    ] = False


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
class AccessRestrictionRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Required

    access_type: AccessType


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
    # Required

    sequence: Annotated[
        list[SequenceEntry],
        Field(
            min_length=1,
            description="Ordered sequence of connector/segment pairs that it is prohibited to follow from this segment.",
        ),
        UniqueItemsConstraint(),
    ]
    final_heading: Annotated[
        Heading,
        Field(
            description="Direction of travel that is prohibited on the destination segment of the sequence.",
        ),
    ]


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class RoadFlagRule(BaseModel):
    """Road-specific flag rule with geometric scoping only."""

    # Required

    values: Annotated[list[RoadFlag], Field(min_length=1), UniqueItemsConstraint()]


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class RailFlagRule(BaseModel):
    """Rail-specific flag rule with geometric scoping only."""

    # Required

    values: Annotated[list[RailFlag], Field(min_length=1), UniqueItemsConstraint()]


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class LevelRule(BaseModel):
    """A single level rule defining the Z-order, i.e. stacking order, applicable within
    a given scope on the road segment."""

    # Required

    value: Level


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class SubclassRule(BaseModel):
    """Set of subclasses scoped along segment."""

    # Required

    value: Subclass


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class SurfaceRule(BaseModel):
    # Required

    value: RoadSurface


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class WidthRule(BaseModel):
    # Required

    value: Width
