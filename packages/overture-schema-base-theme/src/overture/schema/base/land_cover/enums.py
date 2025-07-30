from enum import Enum


class LandCoverSubtype(str, Enum):
    """type of surface represented"""

    BARREN = "barren"
    CROP = "crop"
    FOREST = "forest"
    GRASS = "grass"
    MANGROVE = "mangrove"
    MOSS = "moss"
    SHRUB = "shrub"
    SNOW = "snow"
    URBAN = "urban"
    WETLAND = "wetland"
