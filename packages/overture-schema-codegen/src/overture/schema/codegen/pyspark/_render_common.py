"""Shared rendering primitives used by `renderer` and `test_renderer`.

Concerns:

- `jinja_env` -- the cached Jinja2 environment.
- `py_literal` / `tuple_literal` -- render Python values back to source code.
- `parse_field_eq` -- unwrap a `FieldEqCondition` / `Not(FieldEqCondition)`.
- check/label naming -- `check_name`, `field_label`, `column_level_suffix`,
  `model_constraint_field_label`, `COLUMN_LEVEL_FUNCTIONS` (membership),
  and `_COLUMN_LEVEL_SUFFIXES` (label suffix lookup).
- collision disambiguation -- `disambiguate` (function names) and
  `compute_label_suffixes` (violation labels).
"""

from __future__ import annotations

import functools
from collections import Counter
from collections.abc import Hashable, Iterable
from enum import Enum
from pathlib import Path
from typing import NamedTuple, TypeVar

from jinja2 import Environment, FileSystemLoader

from overture.schema.system.field_path import ArrayPath
from overture.schema.system.model_constraint import (
    Condition,
    FieldEqCondition,
    Not,
)

from .check_ir import Check, ModelCheck
from .constraint_dispatch import ForbidIf, RequireIf, model_constraint_function

__all__ = [
    "COLUMN_LEVEL_FUNCTIONS",
    "FieldEq",
    "check_name",
    "column_level_suffix",
    "compute_label_suffixes",
    "disambiguate",
    "field_label",
    "jinja_env",
    "model_constraint_field_label",
    "parse_field_eq",
    "py_literal",
    "tuple_literal",
]

_K = TypeVar("_K", bound=Hashable)

# Constraint functions that emit a column-level check (one per field
# rather than per element), used by the check builder to split them
# into their own `Check` IR nodes.
COLUMN_LEVEL_FUNCTIONS: frozenset[str] = frozenset(
    {
        "check_required",
        "check_array_min_length",
        "check_array_max_length",
        "check_struct_unique",
    }
)

# Violation label suffix per column-level check that shares its
# field's structural path. `check_required` lands on its field's own
# path, so it stays absent from this table.
_COLUMN_LEVEL_SUFFIXES: dict[str, str] = {
    "check_array_min_length": "_min_length",
    "check_array_max_length": "_max_length",
    "check_struct_unique": "_unique",
}

_TEMPLATES_DIR = Path(__file__).parent / "templates"


@functools.lru_cache(maxsize=1)
def jinja_env() -> Environment:
    """Return the shared Jinja2 environment for PySpark code generation templates."""
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,
    )
    env.filters["py_literal"] = py_literal
    return env


_CHECK_PREFIX = "check_"


def tuple_literal(rendered_items: Iterable[str]) -> str:
    """Wrap pre-rendered items as a Python tuple literal source.

    A single-element tuple needs a trailing comma; this helper applies
    that rule so callers rendering enum-like values that don't fit
    `py_literal` can still share its tuple-formatting behaviour.
    """
    items = list(rendered_items)
    joined = ", ".join(items)
    return f"({joined},)" if len(items) == 1 else f"({joined})"


def py_literal(value: object) -> str:
    """Render a Python value as source code.

    Recurses into containers to extract `Enum.value` (since `repr()` of
    an Enum member is not valid Python). Quote style and line wrapping
    are left to `ruff format`.
    """
    if isinstance(value, Enum):
        return py_literal(value.value)
    if isinstance(value, dict):
        items = ", ".join(f"{py_literal(k)}: {py_literal(v)}" for k, v in value.items())
        return "{" + items + "}"
    if isinstance(value, list):
        return "[" + ", ".join(py_literal(v) for v in value) + "]"
    if isinstance(value, tuple):
        return tuple_literal(py_literal(v) for v in value)
    return repr(value)


class FieldEq(NamedTuple):
    """An unwrapped `FieldEqCondition`, with `negated` set when wrapped in `Not`."""

    field_name: str
    value: object
    negated: bool


def parse_field_eq(condition: Condition) -> FieldEq | None:
    """Unwrap a `FieldEqCondition` or `Not(FieldEqCondition)`.

    Returns a `FieldEq` triple for either shape, or `None` for any
    other condition. `negated` is True iff the condition was wrapped
    in `Not`.
    """
    match condition:
        case Not(inner=FieldEqCondition(field_name=fn, value=v)):
            return FieldEq(fn, v, True)
        case FieldEqCondition(field_name=fn, value=v):
            return FieldEq(fn, v, False)
        case _:
            return None


def check_name(function: str, override: str | None = None) -> str:
    """Strip the `check_` prefix to produce a human-readable check name."""
    if override is not None:
        return override
    return function.removeprefix(_CHECK_PREFIX)


def column_level_suffix(check: Check) -> str:
    """Return the column-level label suffix for `check`, or empty string.

    Column-level checks (`check_array_min_length`, `check_struct_unique`,
    etc.) share their structural path with the field they constrain; the
    suffix differentiates the violation label so each check reports a
    distinct `Check.field`.
    """
    if not check.descriptors:
        return ""
    return _COLUMN_LEVEL_SUFFIXES.get(check.descriptors[0].function, "")


def field_label(check: Check) -> str:
    """Render the violation label for a Check.

    Combines the structural field path with any column-level suffix
    (`_min_length`, `_unique`, etc.) so each check reports a distinct
    `Check.field` even when several share a structural path.
    """
    return f"{check.target}{column_level_suffix(check)}"


def _model_check_base_label(check: ModelCheck) -> str:
    """Compute the violation field label sans collision suffix.

    - `require_if` / `forbid_if` produce a per-target label
      (`field_required` / `path.field_forbidden`) since each descriptor
      now carries a single target field (multi-field decorators split
      at dispatch time).
    - Other kinds (`require_any_of`, `radio_group`, `min_fields_set`)
      name the whole constraint; on `ArrayPath` targets they use the
      path itself so anchors are distinguishable across nestings.
    """
    match check.descriptor:
        case RequireIf():
            kind_suffix = "_required"
        case ForbidIf():
            kind_suffix = "_forbidden"
        case _:
            if isinstance(check.target, ArrayPath):
                return str(check.target)
            return check_name(model_constraint_function(check.descriptor))
    target = check.descriptor.field_names[0]
    if not isinstance(check.target, ArrayPath):
        return f"{target}{kind_suffix}"
    return f"{check.target}.{target}{kind_suffix}"


def model_constraint_field_label(check: ModelCheck, label_suffix: str) -> str:
    """Compute the field label for a model constraint check.

    `label_suffix` (from `compute_label_suffixes`) disambiguates labels
    that would otherwise collide -- e.g. two `@require_any_of` on the
    same model, or two `@require_if(["x"], ...)` with different
    conditions.
    """
    return f"{_model_check_base_label(check)}{label_suffix}"


def _occurrence_indices(keys: list[_K]) -> list[tuple[int, int]]:
    """Pair each key with `(occurrence_index, total_count)`.

    `occurrence_index` is the 0-based position of the key among its
    equal siblings; `total_count` is how many times the key appears in
    `keys`. Both `disambiguate` and `compute_label_suffixes` need this
    "where am I within my collision group" view.
    """
    counts: Counter[_K] = Counter(keys)
    seen: Counter[_K] = Counter()
    result: list[tuple[int, int]] = []
    for key in keys:
        result.append((seen[key], counts[key]))
        seen[key] += 1
    return result


def disambiguate(names: list[str]) -> list[str]:
    """Make a list of names unique by appending `_N` to repeated entries.

    The first occurrence of a name is left bare; the second becomes
    `name_1`, the third `name_2`, and so on. Names that appear once are
    untouched.

    Assumes no input name already matches a generated `name_N` form; a
    collision there would reintroduce a duplicate. Field names in
    practice never carry that suffix, so the assumption holds.
    """
    return [
        f"{name}_{idx}" if total > 1 and idx > 0 else name
        for name, (idx, total) in zip(names, _occurrence_indices(names), strict=True)
    ]


def compute_label_suffixes(model_checks: list[ModelCheck]) -> list[str]:
    """Pre-compute field label suffixes, adding counters only for collisions.

    Unlike `disambiguate`, every colliding entry receives a `_N` suffix
    including the first one (`_0`, `_1`, ...). This is symmetric on
    purpose: violation labels for a colliding group all share the same
    base name, so each needs an explicit collision index to stay
    distinct. `disambiguate` operates on Python function names where
    leaving the first occurrence bare preserves readable identifiers
    for the common no-collision case.
    """
    base_labels = [_model_check_base_label(check) for check in model_checks]
    return [
        f"_{idx}" if total > 1 else ""
        for idx, total in _occurrence_indices(base_labels)
    ]
