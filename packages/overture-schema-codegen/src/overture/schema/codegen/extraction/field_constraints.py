"""Convert field-level constraints to display text.

Handles constraints from Annotated metadata and NewType wrappers:
Ge, Gt, Interval, Le, Lt, MaxLen, MinLen, GeometryTypeConstraint,
Reference, and custom constraint classes.
"""

from __future__ import annotations

from collections.abc import Callable

from annotated_types import Ge, Gt, Interval, Le, Lt, MaxLen, MinLen

from overture.schema.system.primitive import GeometryTypeConstraint
from overture.schema.system.ref import Reference

from .docstring import first_docstring_line
from .specs import TypeIdentity
from .type_analyzer import ConstraintSource

__all__ = [
    "constraint_display_text",
    "constraint_pattern",
    "describe_field_constraint",
]

# Bound attribute names paired with display operators. Each entry maps an
# annotated_types constraint attribute (Ge, Gt, Le, Lt, Interval) to its
# mathematical symbol for prose rendering.
#
# numeric_extraction.py has its own _BOUND_ATTRS for numeric extraction. The
# duplication is deliberate: these modules use the same attribute names for
# unrelated purposes (display formatting vs. numeric bound extraction), and
# coupling them for four string literals adds a dependency without value.
_BOUND_OPS: tuple[tuple[str, str], ...] = (
    ("ge", "≥"),
    ("gt", ">"),
    ("le", "≤"),
    ("lt", "<"),
)


def _first_bound(obj: object) -> str | None:
    """Return backticked notation for the first set bound, or None."""
    for attr, op in _BOUND_OPS:
        val = getattr(obj, attr, None)
        if val is not None:
            return f"`{op} {val}`"
    return None


def _describe_interval(iv: Interval) -> str:
    """Format an Interval as readable bound notation."""
    lower_val = iv.ge if iv.ge is not None else iv.gt
    lower_op = "≤" if iv.ge is not None else "<"
    upper_val = iv.le if iv.le is not None else iv.lt
    upper_op = "≤" if iv.le is not None else "<"

    if lower_val is not None and upper_val is not None:
        return f"`{lower_val} {lower_op} x {upper_op} {upper_val}`"

    return _first_bound(iv) or ""


def _is_opaque_constraint(constraint: object) -> bool:
    """Check whether the constraint has no custom __repr__ (renders as just its class name)."""
    return type(constraint).__repr__ is object.__repr__


def _geometry_type_label(value: str) -> str:
    """Convert a GeometryType value to PascalCase display name.

    >>> _geometry_type_label("line_string")
    'LineString'
    """
    return "".join(part.title() for part in value.split("_"))


def describe_field_constraint(
    constraint: object,
    link_fn: Callable[[TypeIdentity], str] | None = None,
) -> str:
    """Return a display string for a field-level constraint object.

    *link_fn* resolves a TypeIdentity to a markdown link string (e.g.
    `` [`Name`](path) ``). When None, names render as inline code.
    """
    if isinstance(constraint, GeometryTypeConstraint):
        labels = ", ".join(
            _geometry_type_label(gt.value) for gt in constraint.allowed_types
        )
        return f"Allowed geometry types: {labels}"
    if isinstance(constraint, Reference):
        rel_value: str = constraint.relationship.value  # type: ignore[assignment]
        rel_label = rel_value.replace("_", " ")
        target = constraint.relatee
        target_id = TypeIdentity.of(target)
        target_str = link_fn(target_id) if link_fn else f"`{target.__name__}`"
        return f"References {target_str} ({rel_label})"
    if isinstance(constraint, Interval):
        desc = _describe_interval(constraint)
        if desc:
            return desc
    elif isinstance(constraint, (Ge, Gt, Le, Lt)):
        result = _first_bound(constraint)
        if result is not None:
            return result
    if isinstance(constraint, MinLen):
        return f"Minimum length: {constraint.min_length}"
    if isinstance(constraint, MaxLen):
        return f"Maximum length: {constraint.max_length}"

    if _is_opaque_constraint(constraint):
        return f"`{type(constraint).__name__}`"
    return f"`{constraint}`"


def _constraint_class_description(constraint: object) -> str | None:
    """Extract the first docstring line from a custom constraint class.

    Returns None for builtins and classes without docstrings.
    """
    constraint_type = type(constraint)
    if constraint_type.__module__ == "builtins":
        return None
    line = first_docstring_line(constraint_type.__doc__)
    return line or None


def constraint_pattern(constraint: object) -> str | None:
    """Extract the regex pattern string from a constraint, if present.

    Traverses two levels: constraint.pattern is a compiled re.Pattern
    object, and re.Pattern.pattern is the raw string.
    """
    compiled = getattr(constraint, "pattern", None)
    return getattr(compiled, "pattern", None)


def constraint_display_text(
    cs: ConstraintSource,
    link_fn: Callable[[TypeIdentity], str] | None = None,
) -> str:
    """Build display text for a constraint, combining description/pattern when available."""
    description = _constraint_class_description(cs.constraint)
    if _is_opaque_constraint(cs.constraint) and description:
        cls_name = type(cs.constraint).__name__
        pattern = constraint_pattern(cs.constraint)
        if pattern:
            return f"{description} (`{cls_name}`, pattern: `{pattern}`)"
        return f"{description} (`{cls_name}`)"

    return describe_field_constraint(cs.constraint, link_fn=link_fn)
