from enum import Enum


class BoundaryClass(str, Enum):
    # None of the boundary geometry extends beyond the
    # coastline of either associated division.
    LAND = "land"

    # All the boundary geometry extends beyond the
    # coastline of both associated divisions.
    MARITIME = "maritime"
