from enum import Enum


class AreaClass(str, Enum):
    """Area and boundary class designations."""

    LAND = "land"  # The area does not extend beyond the coastline.
    MARITIME = "maritime"  # The area extends beyond the coastline, in most cases to the extent of the division's territorial sea, if it has one.
