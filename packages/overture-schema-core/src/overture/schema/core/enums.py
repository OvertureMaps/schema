from enum import Enum


class NameVariant(str, Enum):
    COMMON = "common"
    OFFICIAL = "official"
    ALTERNATE = "alternate"
    SHORT = "short"


class Side(str, Enum):
    """Represents the side on which something appears relative to a facing or heading
    direction, e.g. the side of a road relative to the road orientation, or relative to
    the direction of travel of a person or vehicle."""

    LEFT = "left"
    RIGHT = "right"


class PerspectiveMode(str, Enum):
    """Perspective mode for disputed names."""

    ACCEPTED_BY = "accepted_by"
    DISPUTED_BY = "disputed_by"
