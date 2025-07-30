"""Divisions theme.

Administrative and political divisions representing human settlements at various
scales, with point, area, and boundary geometries.
"""

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .division import Division
from .division_area import DivisionArea
from .division_boundary import DivisionBoundary

__all__ = ["Division", "DivisionArea", "DivisionBoundary"]
