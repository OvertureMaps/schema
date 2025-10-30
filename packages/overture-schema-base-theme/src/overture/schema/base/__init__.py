"""Base theme.

Fundamental geographic features including bathymetry, infrastructure, land, land cover,
land use, and water features.
"""

__path__ = __import__("pkgutil").extend_path(__path__, __name__)


from ._common import (
    Depth,
    Elevation,
    Height,
    SourcedFromOpenStreetMap,
    SourceTags,
    SurfaceMaterial,
)
from .bathymetry import Bathymetry
from .infrastructure import Infrastructure, InfrastructureClass, InfrastructureSubtype
from .land import Land, LandClass, LandSubtype
from .land_cover import LandCover, LandCoverSubtype
from .land_use import LandUse, LandUseClass, LandUseSubtype
from .water import Water, WaterClass, WaterSubtype

# Only the theme's feature type classes should be available for `import *`.
__all__ = [
    "Bathymetry",
    "Depth",
    "Elevation",
    "Height",
    "Infrastructure",
    "InfrastructureClass",
    "InfrastructureSubType",
    "Land",
    "LandClass",
    "LandCover",
    "LandCoverSubtype",
    "LandSubtype",
    "LandUse",
    "SourcedFromOpenStreetMap",
    "SourceTags",
    "SurfaceMaterial",
    "Water",
    "WaterClass",
    "WaterSubtype",
]
