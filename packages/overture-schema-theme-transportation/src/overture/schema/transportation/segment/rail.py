"""Rail segment and its supporting types."""

import textwrap
from typing import Annotated, Literal, NewType

from pydantic import BaseModel, ConfigDict, Field

from overture.schema.common.scoping import Scope, scoped
from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields

from ._common import SegmentSubtype, TransportationSegment


class RailClass(str, DocumentedEnum):
    """Captures the kind of rail segment."""

    FUNICULAR = ("funicular", "Inclined plane / cliff railway")
    LIGHT_RAIL = (
        "light_rail",
        "Higher-standard tram system, falls between 'tram' and 'rail'",
    )
    MONORAIL = "monorail"
    NARROW_GAUGE = "narrow_gauge"
    STANDARD_GAUGE = (
        "standard_gauge",
        "Standard-gauge rail, equivalent to OSM's railway=rail tag",
    )
    SUBWAY = ("subway", "City passenger rail, often underground")
    TRAM = (
        "tram",
        "1-2 carriage rail vehicle tracks, often sharing road with vehicles",
    )
    UNKNOWN = "unknown"


class RailFlag(str, DocumentedEnum):
    """Simple flags that can be on or off for a railway segment.

    Specifies physical characteristics and can overlap.
    """

    IS_BRIDGE = "is_bridge"
    IS_TUNNEL = (
        "is_tunnel",
        "Note: You may also be looking for the 'subway' class (though subways are occasionally above-ground)",
    )
    IS_UNDER_CONSTRUCTION = "is_under_construction"
    IS_ABANDONED = "is_abandoned"
    IS_COVERED = "is_covered"
    IS_PASSENGER = "is_passenger"
    IS_FREIGHT = "is_freight"
    IS_DISUSED = "is_disused"


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE)
class RailFlagRule(BaseModel):
    """Rail-specific flag rule with geometric scoping only."""

    values: Annotated[list[RailFlag], Field(min_length=1), UniqueItemsConstraint()]


RailFlags = NewType(
    "RailFlags",
    Annotated[
        list[RailFlagRule],
        Field(
            min_length=1,
            description=textwrap.dedent("""
                Set of boolean attributes applicable to railways. May be specified either as a
                single flag array of flag values, or as an array of flag rules.
            """).strip(),
        ),
        UniqueItemsConstraint(),
    ],
)


class RailSegment(TransportationSegment):
    """Rail segment properties."""

    model_config = ConfigDict(title="segment (rail)")

    # Discriminator

    subtype: Literal[SegmentSubtype.RAIL]

    # Required

    class_: Annotated[RailClass, Field(alias="class")]

    # Optional

    rail_flags: RailFlags | None = None
