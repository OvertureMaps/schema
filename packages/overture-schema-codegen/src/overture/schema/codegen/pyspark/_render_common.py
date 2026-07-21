"""Shared rendering primitives used by `renderer` and `test_renderer`.

Concerns:

- `jinja_env` -- the cached Jinja2 environment.
- `py_literal` / `tuple_literal` -- render Python values back to source code.
- schema constant naming -- `schema_const_name` (the cross-module contract
  between expression and test modules).
- check/label naming -- `check_name`, `field_label`, `column_level_suffix`,
  `sanitize_field_name`, `COLUMN_LEVEL_FUNCTIONS` (membership), and
  `_COLUMN_LEVEL_SUFFIXES` (label suffix lookup).
- emission rows -- `field_check_rows` and `model_check_rows` flatten a
  check list into ordered rows carrying each row's final label, check
  name, and (for field checks) disambiguated function name. The renderer
  and test renderer both consume these rows, so the flatten-and-suffix
  logic lives here once rather than in two positionally-coupled passes.
  `disambiguate` (asymmetric, function-name keyed) and `_occurrence_indices`
  (the shared collision primitive) back them.
"""

from __future__ import annotations

import functools
import re
from collections import Counter
from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TypeVar

from jinja2 import Environment, FileSystemLoader

from overture.schema.system.field_path import ArrayPath, MapProjection

from .check_ir import Check, Guard, ModelCheck
from .constraint_dispatch import ForbidIf, RequireIf, model_constraint_function

__all__ = [
    "COLUMN_LEVEL_FUNCTIONS",
    "FieldCheckRow",
    "ModelCheckRow",
    "check_name",
    "column_level_suffix",
    "disambiguate",
    "field_check_rows",
    "field_label",
    "jinja_env",
    "map_runtime_helper",
    "model_check_rows",
    "py_literal",
    "sanitize_field_name",
    "schema_const_name",
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

_MAP_RUNTIME_HELPERS: dict[MapProjection, str] = {
    MapProjection.KEY: "map_keys_check",
    MapProjection.VALUE: "map_values_check",
}


def map_runtime_helper(projection: MapProjection) -> str:
    """Map a projection to its PySpark column-patterns helper name.

    `MapProjection.KEY` -> `map_keys_check`;
    `MapProjection.VALUE` -> `map_values_check`. This is a pyspark-layer
    concern; the mapping lives here rather than on `MapProjection` itself
    (a system-package enum) to avoid a layering violation.
    """
    return _MAP_RUNTIME_HELPERS[projection]


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


def schema_const_name(model_name: str) -> str:
    """Name of the generated `MODELNAME_SCHEMA` StructType constant.

    A cross-module contract: the generated test module imports this
    constant by name from the generated expression module.
    """
    return f"{model_name.upper()}_SCHEMA"


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
    if isinstance(value, frozenset):
        if not value:
            return "frozenset()"
        # Sort the rendered items so regenerated source is stable across runs
        # (set iteration order is not).
        return "frozenset({" + ", ".join(sorted(py_literal(v) for v in value)) + "})"
    return repr(value)


def check_name(function: str, override: str | None = None) -> str:
    """Strip the `check_` prefix to produce a human-readable check name."""
    if override is not None:
        return override
    return function.removeprefix(_CHECK_PREFIX)


# Collapses runs of path punctuation (`.`, `[`, `]`, `{`, `}`, `_`) to a
# single `_` for identifier sanitization (e.g. `names.common{key}` ->
# `names_common_key`).
_PATH_SEPARATOR_RUN = re.compile(r"[.\[\]{}_]+")


def sanitize_field_name(field: str) -> str:
    """Convert an encoded field-path string to a valid Python identifier fragment."""
    return _PATH_SEPARATOR_RUN.sub("_", field).strip("_")


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
      (`field_required` / `path.field_forbidden`); each descriptor
      carries a single target field (multi-field decorators split at
      dispatch time).
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


def _occurrence_indices(keys: list[_K]) -> list[tuple[int, int]]:
    """Pair each key with `(occurrence_index, total_count)`.

    `occurrence_index` is the 0-based position of the key among its
    equal siblings; `total_count` is how many times the key appears in
    `keys`. Both collision styles -- `disambiguate` (function names) and
    the symmetric label suffixing in the row builders -- need this
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
    untouched. This is the asymmetric style, keyed on the function-name
    string: leaving the first occurrence bare keeps readable identifiers
    for the common no-collision case.

    Assumes no input name already matches a generated `name_N` form; a
    collision there would reintroduce a duplicate. Field names in
    practice never carry that suffix, so the assumption holds.
    """
    return [
        f"{name}_{idx}" if total > 1 and idx > 0 else name
        for name, (idx, total) in zip(names, _occurrence_indices(names), strict=True)
    ]


def _symmetric_label_suffixes(keys: list[_K]) -> list[str]:
    """Per-key violation-label collision suffixes, symmetric across a group.

    Every member of a colliding group receives a `_N` suffix including
    the first (`_0`, `_1`, ...); unique keys stay bare. Symmetric unlike
    `disambiguate` because violation labels in a colliding group all
    share the same base name, so each needs an explicit index to stay a
    distinct `Check.field` identity (which keys `suppress` matching,
    `explain_errors` metadata, and the test's `expected_field`).
    """
    return [f"_{idx}" if total > 1 else "" for idx, total in _occurrence_indices(keys)]


def _field_label_suffixes(
    keys: list[tuple[str, str, tuple[Guard, ...]]],
) -> list[str]:
    """Per-row field-label collision suffixes.

    `keys` carries `(base_label, check_name, guards)` per emitted row. A
    field label collides for two reasons, resolved differently:

    - Across union arms -- the same field appears in several discriminator
      arms, each carrying its own guard tuple. Every check gated to one
      arm shares that arm's `_N` suffix (`N` its first-appearance order
      among the label's arms), so a split field reports one consistent
      label per arm. This includes a check unique to one arm (the axle
      arm's `integer` check, absent from the dimension arms), which would
      otherwise escape suffixing and report the bare label alongside its
      `_N`-suffixed siblings.
    - Within a single arm -- one field carries two same-named checks (a
      lower- and upper-`bounds` pair emitted as separate checks). These
      take a per-occurrence `_N` suffix keyed on `(label, name)`; a field
      whose check names are all distinct stays bare.

    A label reached by a single arm uses the occurrence rule (leaving
    unsplit fields untouched); a label reached by several uses the arm
    rule.
    """
    arms_by_label: dict[str, list[tuple[Guard, ...]]] = {}
    for label, _name, guards in keys:
        arms = arms_by_label.setdefault(label, [])
        if guards not in arms:
            arms.append(guards)
    occurrences = _occurrence_indices([(label, name) for label, name, _ in keys])
    suffixes: list[str] = []
    for (label, _name, guards), (occ_idx, occ_total) in zip(
        keys, occurrences, strict=True
    ):
        arms = arms_by_label[label]
        if len(arms) > 1:
            suffixes.append(f"_{arms.index(guards)}")
        elif occ_total > 1:
            suffixes.append(f"_{occ_idx}")
        else:
            suffixes.append("")
    return suffixes


@dataclass(frozen=True, slots=True)
class FieldCheckRow:
    """One emitted field-check row, with its final derived strings.

    The renderer emits one row per descriptor of each `Check`.
    `field_check_rows` flattens the check list into these rows once,
    computing both the arm-grouped `label` collision suffix and the
    asymmetric `func_name` disambiguation, so the renderer and test
    renderer agree without each re-deriving them by a positional index.

    Attributes
    ----------
    check
        The originating field check.
    descriptor_idx
        Index of this row's descriptor within `check.descriptors`.
    label
        The violation `field=` label, including any collision suffix.
    name
        The check name (`check_name(desc.function, desc.check_name)`).
    func_name
        The disambiguated private `_..._check` function name.
    """

    check: Check
    descriptor_idx: int
    label: str
    name: str
    func_name: str


def field_check_rows(field_checks: list[Check]) -> list[FieldCheckRow]:
    """Flatten field checks into emission rows with final derived strings.

    Computes both collision passes over the *unfiltered* list, so the
    expression module (rendered once across every arm) and a per-arm test
    module agree: a per-arm subset could otherwise hide a collision the
    shared module still carries, emitting an `expected_field` the module
    never produces. Callers filter the returned rows to an arm afterward
    rather than computing suffixes over a subset.

    Parameters
    ----------
    field_checks
        The complete field-check list for one generated module, before
        any per-arm filtering.

    Returns
    -------
    list
        One `FieldCheckRow` per emitted `(check, descriptor)`, in
        flattened emission order.
    """
    flattened: list[tuple[Check, int, str, str]] = []
    raw_func_names: list[str] = []
    for check in field_checks:
        label = field_label(check)
        multi = len(check.descriptors) > 1
        for desc_idx, desc in enumerate(check.descriptors):
            name = check_name(desc.function, desc.check_name)
            func_suffix = f"_{name}" if multi else ""
            raw_func_names.append(f"_{sanitize_field_name(label)}{func_suffix}_check")
            flattened.append((check, desc_idx, label, name))
    func_names = disambiguate(raw_func_names)
    label_suffixes = _field_label_suffixes(
        [(label, name, check.guards) for check, _idx, label, name in flattened]
    )
    rows = [
        FieldCheckRow(check, desc_idx, f"{label}{label_suffix}", name, func_name)
        for (check, desc_idx, label, name), label_suffix, func_name in zip(
            flattened, label_suffixes, func_names, strict=True
        )
    ]
    # Arm-grouped suffixing cannot distinguish two same-name checks that
    # land in one arm of a split field; fail generation loudly if a schema
    # ever produces that instead of emitting indistinguishable violations.
    identities = [(row.label, row.name) for row in rows]
    duplicates = {i for i in identities if identities.count(i) > 1}
    if duplicates:
        raise ValueError(
            f"Duplicate violation identities in generated checks: {sorted(duplicates)}"
        )
    return rows


@dataclass(frozen=True, slots=True)
class ModelCheckRow:
    """One emitted model-check row, with its final derived strings.

    Model function names embed `idx` and are unique by construction, so
    a row carries no `func_name` -- the renderer builds it from `idx`.

    Attributes
    ----------
    check
        The originating model check.
    idx
        Position of this check in the unfiltered model-check list; the
        renderer embeds it in the private function name.
    label
        The violation `field=` label, including any collision suffix.
    name
        The check name (`check_name(model_constraint_function(...))`).
    """

    check: ModelCheck
    idx: int
    label: str
    name: str


def model_check_rows(model_checks: list[ModelCheck]) -> list[ModelCheckRow]:
    """Flatten model checks into emission rows with final derived strings.

    Like `field_check_rows`, label collision suffixes are computed over
    the *unfiltered* list so the expression module and per-arm test
    modules agree; callers filter the returned rows to an arm afterward.

    Parameters
    ----------
    model_checks
        The complete model-check list for one generated module, before
        any per-arm filtering.

    Returns
    -------
    list
        One `ModelCheckRow` per model check, in list order.
    """
    base_labels = [_model_check_base_label(check) for check in model_checks]
    label_suffixes = _symmetric_label_suffixes(base_labels)
    return [
        ModelCheckRow(
            check,
            idx,
            f"{base_label}{label_suffix}",
            check_name(model_constraint_function(check.descriptor)),
        )
        for idx, (check, base_label, label_suffix) in enumerate(
            zip(model_checks, base_labels, label_suffixes, strict=True)
        )
    ]
