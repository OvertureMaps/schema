"""Transportation theme models."""

from typing import Annotated

from pydantic import ConfigDict, Field

from overture.schema.core import (
    StrictBaseModel,
)
from overture.schema.core.models import GeometricRangeScope
from overture.schema.core.types import (
    Id,
    Level,
    LinearlyReferencedPosition,
    OpeningHours,
    TrimmedString,
    WikidataId,
)
from overture.schema.core.validation import (
    ConstraintValidatedModel,
    UniqueItemsConstraint,
    any_of,
)

from .enums import (
    AccessType,
    DestinationLabelType,
    DestinationSignSymbol,
    Heading,
    LengthUnit,
    PurposeOfUse,
    RailFlag,
    RecognizedStatus,
    RoadFlag,
    RoadSurface,
    SpeedUnit,
    Subclass,
    TravelMode,
    VehicleComparison,
    VehicleDimension,
    VehicleScopeUnit,
    WeightUnit,
)

SpeedValue = Annotated[int, Field(ge=1, le=350, description="Speed value")]

Width = Annotated[float, Field(gt=0)]


class ConnectorReference(StrictBaseModel):
    """Contains the GERS ID and relative position between 0 and 1 of a connector feature
    along the segment."""

    model_config = ConfigDict(frozen=True)

    # Required

    connector_id: Id
    at: LinearlyReferencedPosition


class HeadingScope(StrictBaseModel):
    """Properties defining travel headings that match a rule."""

    model_config = ConfigDict(frozen=True)

    # Optional

    heading: Heading | None = None


# TODO generate minProperties: 1 in JSON Schema (and validate)
class DestinationWhenClause(HeadingScope):
    pass


class DestinationLabels(StrictBaseModel):
    """The type of object of the destination label."""

    model_config = ConfigDict(frozen=True)

    # Required

    value: Annotated[
        TrimmedString,
        Field(min_length=1, description="Names the object that is reached"),
    ]
    type: DestinationLabelType


@any_of("labels", "symbols")
class DestinationRule(StrictBaseModel):
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
    when: DestinationWhenClause | None = None


class RouteReference(GeometricRangeScope):
    """Route reference with linear referencing support."""

    # Optional

    name: Annotated[
        TrimmedString | None, Field(min_length=1, description="Full name of the route")
    ] = None
    network: Annotated[
        TrimmedString | None,
        Field(
            min_length=1,
            description="Name of the highway system this route belongs to",
        ),
    ] = None
    ref: Annotated[
        TrimmedString | None,
        Field(min_length=1, description="Code or number used to reference the route"),
    ] = None
    symbol: Annotated[
        TrimmedString | None,
        Field(min_length=1, description="URL or description of route signage"),
    ] = None
    wikidata: WikidataId | None = None


class Speed(StrictBaseModel):
    """A speed value, i.e. a certain number of distance units travelled per unit
    time."""

    model_config = ConfigDict(frozen=True)

    # Required

    value: SpeedValue
    unit: SpeedUnit


class IsMoreThanIntegerRelation(StrictBaseModel):
    is_more_than: int


class IsAtLeastIntegerRelation(StrictBaseModel):
    is_at_least: int


class IsEqualToIntegerRelation(StrictBaseModel):
    is_equal_to: int


class IsAtMostIntegerRelation(StrictBaseModel):
    is_at_most: int


class IsLessThanIntegerRelation(StrictBaseModel):
    is_less_than: int


IntegerRelation = Annotated[
    IsMoreThanIntegerRelation
    | IsAtLeastIntegerRelation
    | IsEqualToIntegerRelation
    | IsAtMostIntegerRelation
    | IsLessThanIntegerRelation,
    None,
]
IntegerRelation.__doc__ = """Completes an integer relational expression of the form <lhs> <operator> <length_value>. An example of such an expression is:
    `{ axle_count: { is_less_than: 2 } }`."""


class LengthValueWithUnit(StrictBaseModel):
    """Combines a length value with a length unit."""

    # Required

    unit: LengthUnit
    value: Annotated[float, Field(ge=0)]


class IsMoreThanLengthRelation(StrictBaseModel):
    is_more_than: LengthValueWithUnit


class IsAtLeastLengthRelation(StrictBaseModel):
    is_at_least: LengthValueWithUnit


class IsEqualToLengthRelation(StrictBaseModel):
    is_equal_to: LengthValueWithUnit


class IsAtMostLengthRelation(StrictBaseModel):
    is_at_most: LengthValueWithUnit


class IsLessThanLengthRelation(StrictBaseModel):
    is_less_than: LengthValueWithUnit


LengthRelation = Annotated[
    IsMoreThanLengthRelation
    | IsAtLeastLengthRelation
    | IsEqualToLengthRelation
    | IsAtMostLengthRelation
    | IsLessThanLengthRelation,
    None,
]
LengthRelation.__doc__ = """Completes a length relational expression of the form <lhs> <operator> <length_value>. An example of such an expression is:
    `{ height: { is_less_than: { value: 3, unit: 'm' } } }`."""


class WeightValueWithUnit(StrictBaseModel):
    """Combines a weight value with a weight unit."""

    # Required

    unit: WeightUnit
    value: Annotated[float, Field(ge=0)]


class IsMoreThanWeightRelation(StrictBaseModel):
    is_more_than: WeightValueWithUnit


class IsAtLeastWeightRelation(StrictBaseModel):
    is_at_least: WeightValueWithUnit


class IsEqualToWeightRelation(StrictBaseModel):
    is_equal_to: WeightValueWithUnit


class IsAtMostWeightRelation(StrictBaseModel):
    is_at_most: WeightValueWithUnit


class IsLessThanWeightRelation(StrictBaseModel):
    is_less_than: WeightValueWithUnit


WeightRelation = Annotated[
    IsMoreThanWeightRelation
    | IsAtLeastWeightRelation
    | IsEqualToWeightRelation
    | IsAtMostWeightRelation
    | IsLessThanWeightRelation,
    None,
]
WeightRelation.__doc__ = """        Completes a weight relational expression of the form <lhs> <operator> <weight_value>. An example of such an expression is:
`{ weight: { is_more_than: { value: 2, unit: 't' } } }`."""


class SequenceEntry(StrictBaseModel):
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


class PurposeOfUseScope(StrictBaseModel):
    """Properties defining usage purposes that match a rule."""

    model_config = ConfigDict(frozen=True)

    # Optional

    using: Annotated[
        list[PurposeOfUse] | None, Field(min_length=1), UniqueItemsConstraint()
    ] = None

    def __hash__(self) -> int:
        """Make PurposeOfUseScope hashable."""
        return hash((tuple(self.using) if self.using is not None else None,))


class TemporalScope(StrictBaseModel):
    """Temporal scoping properties defining the time spans when a recurring rule is
    active."""

    model_config = ConfigDict(frozen=True)

    # Optional

    during: OpeningHours | None = None


class TravelModeScope(StrictBaseModel):
    """Properties defining travel modes that match a rule."""

    model_config = ConfigDict(frozen=True)

    # Optional

    mode: Annotated[
        list[TravelMode] | None,
        Field(min_length=1, description="Travel mode(s) to which the rule applies"),
        UniqueItemsConstraint(),
    ] = None

    def __hash__(self) -> int:
        """Make TravelModeScope hashable."""
        return hash((tuple(self.mode) if self.mode is not None else None,))


class RecognizedStatusScope(StrictBaseModel):
    """Properties defining statuses that match a rule."""

    model_config = ConfigDict(frozen=True)

    # Optional

    recognized: Annotated[
        list[RecognizedStatus] | None, Field(min_length=1), UniqueItemsConstraint()
    ] = None

    def __hash__(self) -> int:
        """Make RecognizedStatusScope hashable."""
        return hash((tuple(self.recognized) if self.recognized is not None else None,))


class VehicleScopeRule(StrictBaseModel):
    """An individual vehicle scope rule."""

    model_config = ConfigDict(frozen=True)

    # Required

    dimension: VehicleDimension
    comparison: VehicleComparison
    value: Annotated[float, Field(ge=0)]

    # Optional

    unit: VehicleScopeUnit | None = None


class VehicleScope(StrictBaseModel):
    """Properties defining vehicle attributes for which a rule is active."""

    model_config = ConfigDict(frozen=True)

    # Optional

    vehicle: Annotated[
        list[VehicleScopeRule] | None,
        Field(
            min_length=1,
            description="Vehicle attributes for which the rule applies",
        ),
        UniqueItemsConstraint(),
    ] = None

    def __hash__(self) -> int:
        """Make VehicleScope hashable."""
        return hash((tuple(self.vehicle) if self.vehicle is not None else None,))


# TODO require at least one property from these classes
# TODO generate minProperties: 1
class SpeedLimitWhenClause(
    TemporalScope,
    HeadingScope,
    PurposeOfUseScope,
    RecognizedStatusScope,
    TravelModeScope,
    VehicleScope,
):
    pass


@any_of("max_speed", "min_speed")
class SpeedLimitRule(ConstraintValidatedModel, GeometricRangeScope):
    """An individual speed limit rule."""

    # TODO: Speed limits probably have directionality, so should factor out a headingScopeContainer for this purpose and use it to introduce an optional direction property in each rule.

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
    when: SpeedLimitWhenClause | None = None


# TODO require at least one property from these classes
# TODO generate minProperties: 1
class AccessRestrictionWhenClause(
    TemporalScope,
    HeadingScope,
    PurposeOfUseScope,
    RecognizedStatusScope,
    TravelModeScope,
    VehicleScope,
):
    model_config = ConfigDict(frozen=True)

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


class AccessRestrictionRule(GeometricRangeScope):
    model_config = ConfigDict(frozen=True)

    # Required

    access_type: AccessType

    # Optional

    when: AccessRestrictionWhenClause | None = None

    def __hash__(self) -> int:
        """Make AccessRestrictionRule hashable."""
        return hash((super().__hash__(), self.access_type, self.when))


# TODO require at least one property from these classes
# TODO generate minProperties: 1
class ProhibitedTransitionWhenClause(
    HeadingScope,
    TemporalScope,
    PurposeOfUseScope,
    RecognizedStatusScope,
    TravelModeScope,
    VehicleScope,
):
    pass


class ProhibitedTransitionRule(GeometricRangeScope):
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

    # Optional

    when: ProhibitedTransitionWhenClause | None = None


class RoadFlagRule(GeometricRangeScope):
    """Road-specific flag rule with geometric scoping only."""

    # Required

    values: Annotated[list[RoadFlag], Field(min_length=1), UniqueItemsConstraint()]


class RailFlagRule(GeometricRangeScope):
    """Rail-specific flag rule with geometric scoping only."""

    # Required

    values: Annotated[list[RailFlag], Field(min_length=1), UniqueItemsConstraint()]


class LevelRule(GeometricRangeScope):
    """A single level rule defining the Z-order, i.e. stacking order, applicable within
    a given scope on the road segment."""

    # Required

    value: Level


class SubclassRule(GeometricRangeScope):
    """Set of subclasses scoped along segment."""

    # Required

    value: Subclass


class SurfaceRule(GeometricRangeScope):
    # Required

    value: RoadSurface


class WidthRule(GeometricRangeScope):
    # Required

    value: Width
