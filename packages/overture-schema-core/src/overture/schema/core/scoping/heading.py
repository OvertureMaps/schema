from enum import Enum


class Heading(str, Enum):
    """
    Travel direction along an oriented path: forward or backward.
    """

    FORWARD = "forward"
    BACKWARD = "backward"
