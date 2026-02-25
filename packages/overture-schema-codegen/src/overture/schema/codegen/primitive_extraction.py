"""Primitive extraction and partitioning."""

from annotated_types import Interval

from .docstring import first_docstring_line
from .newtype_extraction import extract_newtype
from .specs import PrimitiveSpec
from .type_analyzer import TypeInfo, is_newtype

__all__ = [
    "extract_numeric_bounds",
    "extract_primitives",
    "partition_primitive_and_geometry_names",
]


# Bound attribute names on annotated_types constraint objects (Ge, Gt, Le,
# Lt, Interval) used for numeric bound extraction.
#
# field_constraint_description.py has its own _BOUND_OPS for display formatting.
# The duplication is deliberate: these modules use the same attribute names
# for unrelated purposes (numeric extraction vs. prose rendering), and
# coupling them for four string literals adds a dependency without value.
_BOUND_ATTRS = ("ge", "gt", "le", "lt")


def extract_numeric_bounds(type_info: TypeInfo) -> Interval:
    """Extract numeric bounds from a TypeInfo's constraints.

    Checks for ge, gt, le, and lt attributes on constraint objects.
    Stops at the first constraint defining each bound.
    """
    found: dict[str, int | float] = {}
    for cs in type_info.constraints:
        c = cs.constraint
        for attr in _BOUND_ATTRS:
            if attr not in found:
                val = getattr(c, attr, None)
                if val is not None:
                    found[attr] = val
    return Interval(**found)


def extract_primitives(
    primitive_names: list[str],
    primitive_module: object,
) -> list[PrimitiveSpec]:
    """Extract specifications for numeric primitive types.

    Resolves each name against the given module, extracts its NewType
    spec, docstring, and numeric bounds.
    """
    specs: list[PrimitiveSpec] = []
    for name in primitive_names:
        obj = getattr(primitive_module, name)
        newtype_spec = extract_newtype(obj)
        bounds = extract_numeric_bounds(newtype_spec.type_info)
        description = first_docstring_line(getattr(obj, "__doc__", None))
        float_bits = _extract_float_bits(name)
        specs.append(
            PrimitiveSpec(
                name=name,
                description=description,
                bounds=bounds,
                float_bits=float_bits,
            )
        )
    return specs


_FLOAT_BITS: dict[str, int] = {
    "float32": 32,
    "float64": 64,
}


def _extract_float_bits(name: str) -> int | None:
    """Extract bit width from a float type name like 'float32'."""
    return _FLOAT_BITS.get(name)


def partition_primitive_and_geometry_names(
    primitive_module: object,
) -> tuple[list[str], list[str]]:
    """Discover primitive and geometry type names from a module's exports.

    NewType exports are numeric primitives.
    Non-constraint class/enum exports are geometry types.
    """
    module_all: list[str] = getattr(primitive_module, "__all__", [])
    primitives: list[str] = []
    geometries: list[str] = []

    for name in module_all:
        obj = getattr(primitive_module, name)
        if is_newtype(obj):
            primitives.append(name)
        elif isinstance(obj, type) and not name.endswith("Constraint"):
            geometries.append(name)

    return primitives, geometries
