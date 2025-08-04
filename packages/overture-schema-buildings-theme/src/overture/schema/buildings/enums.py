from enum import Enum


class FacadeMaterial(str, Enum):
    """The outer surface material of building facade."""

    BRICK = "brick"
    CEMENT_BLOCK = "cement_block"
    CLAY = "clay"
    CONCRETE = "concrete"
    GLASS = "glass"
    METAL = "metal"
    PLASTER = "plaster"
    PLASTIC = "plastic"
    STONE = "stone"
    TIMBER_FRAMING = "timber_framing"
    WOOD = "wood"


class RoofMaterial(str, Enum):
    """The outermost material of the roof."""

    CONCRETE = "concrete"
    COPPER = "copper"
    ETERNIT = "eternit"
    GLASS = "glass"
    GRASS = "grass"
    GRAVEL = "gravel"
    METAL = "metal"
    PLASTIC = "plastic"
    ROOF_TILES = "roof_tiles"
    SLATE = "slate"
    SOLAR_PANELS = "solar_panels"
    THATCH = "thatch"
    TAR_PAPER = "tar_paper"
    WOOD = "wood"


class RoofShape(str, Enum):
    """The shape of the roof"""

    DOME = "dome"
    FLAT = "flat"
    GABLED = "gabled"
    GAMBREL = "gambrel"
    HALF_HIPPED = "half_hipped"
    HIPPED = "hipped"
    MANSARD = "mansard"
    ONION = "onion"
    PYRAMIDAL = "pyramidal"
    ROUND = "round"
    SALTBOX = "saltbox"
    SAWTOOTH = "sawtooth"
    SKILLION = "skillion"
    SPHERICAL = "spherical"


class RoofOrientation(str, Enum):
    """Orientation of the roof shape relative to the footprint shape. Either "along" or "across"."""

    ACROSS = "across"
    ALONG = "along"
