from enum import Enum


class PerspectiveMode(str, Enum):
    """Perspective mode for disputed names."""

    ACCEPTED_BY = "accepted_by"
    DISPUTED_BY = "disputed_by"
