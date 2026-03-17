"""Divisions theme.

Administrative and political divisions representing human settlements at various scales,
with point, area, and boundary geometries.
"""

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from ._common import AdminLevel, DivisionSubtype
from .division import CapitalOfDivisionItem, Division, DivisionClass, Norms
from .division_area import AreaClass, DivisionArea
from .division_boundary import BoundaryClass, DivisionBoundary

# Exclude from `__all__`: internal implementation details, and types that are effectively annotated
# primitives, such as `AdminLevel`, where a person working with one of the feature types likely
# would not need to import that type because they'll just set the field to a Python primitive value
# directly. (e.g., `my_division.admin_level = 4`).
__all__ = [
    "AreaClass",
    "BoundaryClass",
    "CapitalOfDivisionItem",
    "Division",
    "DivisionArea",
    "DivisionClass",
    "DivisionSubtype",
    "DivisionBoundary",
    "Norms",
]
