from enum import Enum


class NameVariant(str, Enum):
    COMMON = "common"
    OFFICIAL = "official"
    ALTERNATE = "alternate"
    SHORT = "short"


class PerspectiveMode(str, Enum):
    """Perspective mode for disputed names."""

    ACCEPTED_BY = "accepted_by"
    DISPUTED_BY = "disputed_by"
