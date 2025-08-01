"""Places theme.

Point-based representations of real-world facilities, services, and amenities
with category classifications and metadata.
"""

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .place import Place

__all__ = ["Place"]
