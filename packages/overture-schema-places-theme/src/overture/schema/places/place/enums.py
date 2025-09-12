from enum import Enum


class OperatingStatus(str, Enum):
    OPEN = "open"
    PERMANENTLY_CLOSED = "permanently_closed"
    TEMPORARILY_CLOSED = "temporarily_closed"
