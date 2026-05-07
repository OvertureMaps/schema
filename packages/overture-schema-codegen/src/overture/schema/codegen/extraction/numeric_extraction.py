"""Numeric type extraction."""

from annotated_types import Interval

from .docstring import first_docstring_line
from .field import FieldShape, Scalar
from .field_walk import terminal_of
from .newtype_extraction import extract_newtype
from .specs import NumericSpec, TypeIdentity

__all__ = [
    "extract_numeric_bounds",
    "extract_numerics",
]


# Bound attribute names on annotated_types constraints (Ge, Gt, Le, Lt, Interval).
_BOUND_ATTRS = ("ge", "gt", "le", "lt")


def extract_numeric_bounds(shape: FieldShape) -> Interval:
    """Extract numeric bounds from the constraints on a shape's terminal scalar.

    Walks `NewTypeShape` / `ArrayOf` wrappers to find the terminal
    `Scalar`, then scans its constraints for `ge`, `gt`, `le`, and `lt`
    attributes. Stops at the first constraint defining each bound.
    """
    terminal = terminal_of(shape)
    if not isinstance(terminal, Scalar):
        return Interval()
    found: dict[str, int | float] = {}
    for cs in terminal.constraints:
        c = cs.constraint
        for attr in _BOUND_ATTRS:
            if attr not in found:
                val = getattr(c, attr, None)
                if val is not None:
                    found[attr] = val
    return Interval(**found)


def extract_numerics(
    numeric_ids: list[TypeIdentity],
) -> list[NumericSpec]:
    """Extract specifications for numeric types."""
    specs: list[NumericSpec] = []
    for tid in numeric_ids:
        newtype_spec = extract_newtype(tid.obj)
        # extract_newtype strips the outer NewTypeShape, so the spec's
        # terminal scalar already carries the constraints the NewType
        # contributed -- extract_numeric_bounds walks straight to it.
        bounds = extract_numeric_bounds(newtype_spec.shape)
        description = first_docstring_line(getattr(tid.obj, "__doc__", None))
        float_bits = _extract_float_bits(tid.name)
        specs.append(
            NumericSpec(
                name=tid.name,
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
    """Extract bit width from a float type name like `float32`."""
    return _FLOAT_BITS.get(name)
