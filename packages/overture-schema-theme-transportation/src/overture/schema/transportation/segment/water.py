"""Water segment and its supporting types."""

import textwrap
from typing import Annotated, Literal, NewType

from pydantic import ConfigDict, Field

from overture.schema.system.numeric import int32

from ._common import SegmentSubtype, TransportationSegment

TravelTime = NewType(
    "TravelTime",
    Annotated[
        int32,
        Field(
            ge=1,
            description=textwrap.dedent("""
                Scheduled travel time, in seconds, to traverse the full segment from end
                to end, including time spent docking, loading, and unloading. Sourced
                from the OSM duration tag on ferry routes.
            """).strip(),
        ),
    ],
)


class WaterSegment(TransportationSegment):
    """Water segment properties."""

    model_config = ConfigDict(title="segment (water)")

    # Discriminator

    subtype: Literal[SegmentSubtype.WATER]

    # Optional

    travel_time: TravelTime | None = None
