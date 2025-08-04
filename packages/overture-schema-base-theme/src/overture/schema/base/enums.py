"""Common structures and enums shared across base theme types."""

from enum import Enum


class SurfaceMaterial(str, Enum):
    """Surface material enum used by infrastructure and land features."""

    ASPHALT = "asphalt"
    COBBLESTONE = "cobblestone"
    COMPACTED = "compacted"
    CONCRETE = "concrete"
    CONCRETE_PLATES = "concrete_plates"
    DIRT = "dirt"
    EARTH = "earth"
    FINE_GRAVEL = "fine_gravel"
    GRASS = "grass"
    GRAVEL = "gravel"
    GROUND = "ground"
    PAVED = "paved"
    PAVING_STONES = "paving_stones"
    PEBBLESTONE = "pebblestone"
    RECREATION_GRASS = "recreation_grass"
    RECREATION_PAVED = "recreation_paved"
    RECREATION_SAND = "recreation_sand"
    RUBBER = "rubber"
    SAND = "sand"
    SETT = "sett"
    TARTAN = "tartan"
    UNPAVED = "unpaved"
    WOOD = "wood"
    WOODCHIPS = "woodchips"


__all__ = [
    "SurfaceMaterial",
]
