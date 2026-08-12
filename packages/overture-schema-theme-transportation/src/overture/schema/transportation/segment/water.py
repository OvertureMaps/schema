"""Water segment and its supporting types."""

from typing import Literal

from pydantic import ConfigDict

from ._common import SegmentSubtype, TransportationSegment


class WaterSegment(TransportationSegment):
    """Water segment properties."""

    model_config = ConfigDict(title="segment (water)")

    # Discriminator

    subtype: Literal[SegmentSubtype.WATER]
