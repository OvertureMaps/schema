"""Buildings theme.

Human-made building structures, including building footprints and building parts with
attributes like height, floors, and materials.
"""

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .building import Building
from .building_part import BuildingPart

__all__ = ["Building", "BuildingPart"]
