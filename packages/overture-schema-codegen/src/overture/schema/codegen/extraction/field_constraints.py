"""Convert field-level constraints to display text.

Handles constraints from Annotated metadata and NewType wrappers:
Ge, Gt, Interval, Le, Lt, ArrayMinLen, ArrayMaxLen, ScalarMinLen,
ScalarMaxLen, GeometryTypeConstraint, Reference, and custom constraint
classes.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from annotated_types import Ge, Gt, Interval, Le, Lt, MultipleOf

from overture.schema.system.geometric import GeometryTypeConstraint
from overture.schema.system.ref import Reference

from .docstring import first_docstring_line
from .length_constraints import ArrayMaxLen, ArrayMinLen, ScalarMaxLen, ScalarMinLen
from .literal_alternatives import LiteralAlternatives
from .specs import TypeIdentity
from .type_analyzer import ConstraintSource

__all__ = [
    "constraint_display_text",
    "describe_field_constraint",
]

# Bound attribute -> mathematical symbol for prose rendering.
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
        if constraint.role:
            role_label = constraint.role.replace("_", " ")
            return f"References {target_str} ({rel_label}, {role_label})"
        return f"References {target_str} ({rel_label})"
    if isinstance(constraint, Interval):
        desc = _describe_interval(constraint)
        if desc:
            return desc
    elif isinstance(constraint, (Ge, Gt, Le, Lt)):
        result = _first_bound(constraint)
        if result is not None:
            return result
    if isinstance(constraint, MultipleOf):
        if constraint.multiple_of == 1:
            return "Must be a whole number"
        return f"Must be a multiple of {constraint.multiple_of}"
    if isinstance(constraint, (ArrayMinLen, ScalarMinLen)):
        return f"Minimum length: {constraint.min_length}"
    if isinstance(constraint, (ArrayMaxLen, ScalarMaxLen)):
        return f"Maximum length: {constraint.max_length}"
    if isinstance(constraint, LiteralAlternatives):
        return "Also accepts: " + ", ".join(f"`{v!r}`" for v in constraint.values)

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


# re.UNICODE is the implicit default on compiled `str` patterns; rendering it
# would stamp a noise `(?u)` group onto every pattern. Every other flag with a
# visible matching effect is surfaced in the documented pattern. Unlike the
# pyspark dispatch (`compiled_pattern_source`) -- which must reject flags
# Spark's rlike cannot honor -- display is faithful for known flags and never
# fails: a flag absent from this table is dropped from the rendered group, not
# raised on. A new flag added to pyspark's supported set with a visible effect
# belongs here too, or docs will hide that pattern's real behavior.
_DISPLAY_FLAG_LETTERS: tuple[tuple[re.RegexFlag, str], ...] = (
    (re.IGNORECASE, "i"),
    (re.MULTILINE, "m"),
    (re.DOTALL, "s"),
    (re.VERBOSE, "x"),
    (re.ASCII, "a"),
)


def _inline_flag_prefix(flags: int) -> str:
    """Render set regex flags as an inline group like `(?im)`, or "" if none."""
    letters = "".join(c for flag, c in _DISPLAY_FLAG_LETTERS if flags & flag)
    return f"(?{letters})" if letters else ""


def _constraint_pattern(constraint: object) -> str | None:
    """Return a constraint's compiled regex as displayable source, or None.

    Prepends an inline-flag group (e.g. `(?i)` for case-insensitivity) so a
    flagged pattern reads as the regex that actually matches rather than its
    bare, misleading source. Returns None when `constraint.pattern` is not a
    compiled `re.Pattern`.
    """
    compiled = getattr(constraint, "pattern", None)
    if not isinstance(compiled, re.Pattern):
        return None
    return f"{_inline_flag_prefix(compiled.flags)}{compiled.pattern}"


def constraint_display_text(
    cs: ConstraintSource,
    link_fn: Callable[[TypeIdentity], str] | None = None,
) -> str:
    """Build display text for a constraint, combining description/pattern when available."""
    description = _constraint_class_description(cs.constraint)
    if _is_opaque_constraint(cs.constraint) and description:
        cls_name = type(cs.constraint).__name__
        pattern = _constraint_pattern(cs.constraint)
        if pattern:
            return f"{description} (`{cls_name}`, pattern: `{pattern}`)"
        return f"{description} (`{cls_name}`)"

    return describe_field_constraint(cs.constraint, link_fn=link_fn)
