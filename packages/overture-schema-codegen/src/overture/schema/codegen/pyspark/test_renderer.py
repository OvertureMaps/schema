"""Render Check / ModelCheck IR into generated conformance test modules."""

from __future__ import annotations

from typing import Any, NamedTuple

from typing_extensions import assert_never

from overture.schema.system.field_path import ArrayPath

from ..extraction.field import FieldShape
from ..extraction.field_walk import has_array_layer
from ..extraction.specs import FeatureSpec
from ._render_common import (
    check_name,
    compute_label_suffixes,
    disambiguate,
    field_label,
    jinja_env,
    model_constraint_field_label,
    parse_field_eq,
    py_literal,
)
from .check_ir import (
    Check,
    ColumnGuard,
    ModelCheck,
)
from .constraint_dispatch import (
    ExpressionDescriptor,
    ForbidIf,
    MinFieldsSet,
    ModelConstraintDescriptor,
    RadioGroup,
    RequireAnyOf,
    RequireIf,
    model_constraint_function,
    model_mutation_function,
)
from .test_data.invalid_value import invalid_value
from .test_data.scaffold import (
    generate_model_scaffold,
    generate_scaffold,
    leaf_list_depth,
)

__all__ = ["render_test_module"]


def _check_belongs_to_arm(check: Check, arm: str) -> bool:
    """Return True when a Check applies to a given union arm.

    The outermost union's discriminator surfaces as `ColumnGuard`s; inner
    unions use `ElementGuard`s on a different discriminator field and are
    irrelevant to arm filtering. A check belongs to *arm* when every
    `ColumnGuard` admits it (guards are AND-composed).
    """
    column_guards = [g for g in check.guards if isinstance(g, ColumnGuard)]
    return all(arm in g.values for g in column_guards)


def _model_check_belongs_to_arm(check: ModelCheck, arm: str) -> bool:
    """Return True when a ModelCheck applies to a given union arm.

    `ModelCheck.arm` is `None` for union-level constraints (which apply
    regardless of discriminator) and set to a discriminator value for
    constraints contributed by one specific member class.
    """
    return check.arm is None or check.arm == arm


def render_test_module(
    feature_name: str,
    field_checks: list[Check],
    model_checks: list[ModelCheck],
    *,
    expression_import: str,
    support_prefix: str,
    base_row_sparse: dict[str, Any] | None = None,
    base_row_populated: dict[str, Any] | None = None,
    arm: str | None = None,
    spec: FeatureSpec | None = None,
) -> str:
    """Render a complete pytest test file for a feature's validation checks.

    Arm filtering uses two complementary signals. A field check's
    `ColumnGuard`s identify the arms it belongs to. A model check's `arm`
    attribute is set for member-specific constraints and `None` for
    union-level constraints (which apply to every arm).
    """
    if arm is not None:
        field_checks = [c for c in field_checks if _check_belongs_to_arm(c, arm)]
        model_checks = [c for c in model_checks if _model_check_belongs_to_arm(c, arm)]

    model_scenarios, used_mutation_fns = _render_model_scenarios(
        feature_name, model_checks, spec
    )
    field_scenarios, field_helpers = _render_field_check_scenarios(
        feature_name, field_checks, spec
    )
    used_mutation_fns |= field_helpers - {"set_at_path"}

    sparse_repr = py_literal(base_row_sparse) if base_row_sparse is not None else "{}"
    populated_repr = (
        py_literal(base_row_populated) if base_row_populated is not None else "{}"
    )

    all_scenarios = field_scenarios + model_scenarios

    template = jinja_env().get_template("test_module.py.jinja2")
    return template.render(
        feature_name=feature_name,
        schema_name=f"{feature_name.upper()}_SCHEMA",
        mutation_imports=sorted(used_mutation_fns),
        needs_set_at_path="set_at_path" in field_helpers,
        base_row_sparse=sparse_repr,
        base_row_populated=populated_repr,
        scenarios=all_scenarios,
        expression_import=expression_import,
        support_prefix=support_prefix,
    )


def _scenario_entry(
    *,
    scenario_id: str,
    scaffold: dict[str, Any],
    mutate_expr: str,
    expected_field: str,
    expected_check: str,
) -> list[tuple[str, str]]:
    """Build a rendered Scenario kwargs list for the test_module template."""
    return [
        ("id", py_literal(scenario_id)),
        ("scaffold", py_literal(scaffold)),
        ("mutate", mutate_expr),
        ("expected_field", py_literal(expected_field)),
        ("expected_check", py_literal(expected_check)),
    ]


class _MutateExpr(NamedTuple):
    """One rendered `mutate=` expression and the helper it imports.

    `helper` is `None` when the expression is a literal `set_at_path`
    call (the default), and otherwise names a `mutate_*` helper from
    `tests/_support/mutations.py` to import.
    """

    expr: str
    helper: str | None


def _field_mutate_expr(
    check: Check, desc: ExpressionDescriptor, spec: FeatureSpec | None
) -> _MutateExpr:
    """Render the `mutate=` expression for one field-check descriptor.

    `check_struct_unique` calls the `mutate_unique_items` helper at the
    target path; every other descriptor injects a constraint-violating
    literal via `set_at_path`.
    """
    target_repr = py_literal(str(check.target))
    if desc.function == "check_struct_unique":
        return _MutateExpr(
            f"lambda row: mutate_unique_items(row, {target_repr})",
            "mutate_unique_items",
        )
    iv_val = _wrap_for_list_leaf(invalid_value(desc), check, spec)
    return _MutateExpr(f"set_at_path({target_repr}, {py_literal(iv_val)})", None)


def _render_field_check_scenarios(
    feature_name: str,
    field_checks: list[Check],
    spec: FeatureSpec | None,
) -> tuple[list[list[tuple[str, str]]], set[str]]:
    """Render Scenario entries for field-level checks.

    Returns the entries and the set of mutation helper names referenced
    by them, mirroring `_render_model_scenarios`.
    """
    rows: list[tuple[Check, ExpressionDescriptor, str, str]] = []
    for check in field_checks:
        label = field_label(check)
        for desc in check.descriptors:
            name = check_name(desc.function, desc.check_name)
            rows.append((check, desc, label, name))

    scenario_ids = disambiguate(
        [f"{feature_name}::{label}:{name}" for _check, _desc, label, name in rows]
    )

    entries: list[list[tuple[str, str]]] = []
    used_helpers: set[str] = set()
    for (check, desc, label, name), scenario_id in zip(rows, scenario_ids, strict=True):
        scaffold = generate_scaffold(check, spec) if spec is not None else {}
        try:
            mutate = _field_mutate_expr(check, desc, spec)
        except ValueError as exc:
            raise ValueError(
                f"Cannot render mutate expression for {scenario_id}: {exc}"
            ) from exc
        used_helpers.add(mutate.helper or "set_at_path")
        entries.append(
            _scenario_entry(
                scenario_id=scenario_id,
                scaffold=scaffold,
                mutate_expr=mutate.expr,
                expected_field=label,
                expected_check=name,
            )
        )

    return entries, used_helpers


def _checks_array_element(check: Check) -> bool:
    """True when the check fires on each element of an `ArrayPath` directly.

    The check target ends at the array (`leaf=()`), so the mutation
    replaces an array element rather than a struct field on one. For
    these checks, a `None` invalid value still needs list wrapping; for
    nested struct fields, `None` already sits at the right level.
    """
    return isinstance(check.target, ArrayPath) and not check.target.leaf


def _wrap_for_list_leaf(
    value: object,
    check: Check,
    spec: FeatureSpec | None,
) -> object:
    """Wrap a scalar invalid value to match the field's list nesting depth."""
    if spec is None or isinstance(value, list):
        return value
    if value is None and not _checks_array_element(check):
        return value
    depth = leaf_list_depth(check.target, spec)
    for _ in range(depth):
        value = [value]
    return value


def _render_model_scenarios(
    feature_name: str,
    model_checks: list[ModelCheck],
    spec: FeatureSpec | None,
) -> tuple[list[list[tuple[str, str]]], set[str]]:
    """Render Scenario entries for model-level checks.

    Returns the entries and the set of mutation helper names referenced
    by them, so the caller can scope the test module's imports.
    """
    entries: list[list[tuple[str, str]]] = []
    used_mutation_fns: set[str] = set()
    label_suffixes = compute_label_suffixes(model_checks)

    for idx, mc in enumerate(model_checks):
        desc = mc.descriptor
        fn = model_constraint_function(desc)
        mutation_fn = model_mutation_function(desc)
        name = check_name(fn)
        scenario_id = f"{feature_name}::model:{name}:{idx}"
        label = model_constraint_field_label(mc, label_suffixes[idx])
        scaffold = generate_model_scaffold(mc, spec) if spec is not None else {}

        try:
            call = _render_mutation_call(mutation_fn, desc, mc)
        except ValueError as exc:
            raise ValueError(
                f"Cannot render mutation call for {scenario_id}: {exc}"
            ) from exc
        mutate_expr = f"lambda row: {call}"
        used_mutation_fns.add(mutation_fn)
        entries.append(
            _scenario_entry(
                scenario_id=scenario_id,
                scaffold=scaffold,
                mutate_expr=mutate_expr,
                expected_field=label,
                expected_check=name,
            )
        )

    return entries, used_mutation_fns


def _render_mutation_call(
    mutation_fn: str,
    desc: ModelConstraintDescriptor,
    check: ModelCheck,
) -> str:
    """Render a model mutation helper function call."""
    fields_repr = py_literal(list(desc.field_names))

    match desc:
        case RequireIf() | ForbidIf():
            return _render_conditional_mutation_call(
                mutation_fn, desc, check, fields_repr
            )
        case RadioGroup():
            if isinstance(check.target, ArrayPath):
                raise ValueError(
                    "mutate_radio_group does not accept array_path "
                    f"(target={check.target!r})"
                )
            return f"{mutation_fn}(row, {fields_repr})"
        case RequireAnyOf() | MinFieldsSet():
            parts = _array_kwargs_leaf(check, mutation_fn)
            suffix = ", " + ", ".join(parts) if parts else ""
            return f"{mutation_fn}(row, {fields_repr}{suffix})"
    assert_never(desc)


def _render_conditional_mutation_call(
    mutation_fn: str,
    desc: RequireIf | ForbidIf,
    check: ModelCheck,
    fields_repr: str,
) -> str:
    """Render a mutate_require_if or mutate_forbid_if call."""
    parsed = parse_field_eq(desc.condition)
    fn = model_constraint_function(desc)
    if parsed is None:
        raise ValueError(
            f"{fn} condition {desc.condition!r} is not a "
            "FieldEqCondition or Not(FieldEqCondition); cannot render "
            f"{mutation_fn} call"
        )
    fill = _render_fill_values(desc) if isinstance(desc, ForbidIf) else None
    kwarg_parts: list[str] = []
    if parsed.negated:
        kwarg_parts.append("negate=True")
    if fill:
        kwarg_parts.append(f"fill_values={fill}")
    kwarg_parts.extend(_array_kwargs_inner(check, mutation_fn))
    suffix = ", " + ", ".join(kwarg_parts) if kwarg_parts else ""
    return (
        f"{mutation_fn}(row, {fields_repr}, "
        f"{py_literal(parsed.field_name)}, {py_literal(parsed.value)}{suffix})"
    )


def _fill_value_literal(shape: FieldShape) -> str:
    """Return a Python source literal for a type-appropriate non-null fill value."""
    if has_array_layer(shape):
        return "[{}]"
    return "{}"


def _render_fill_values(desc: ForbidIf) -> str | None:
    """Render a `fill_values` dict literal for non-string ForbidIf targets."""
    if not desc.field_shapes:
        return None
    items = [
        f"{py_literal(name)}: {_fill_value_literal(shape)}"
        for name, shape in desc.field_shapes
    ]
    return "{" + ", ".join(items) + "}"


def _array_kwargs_leaf(check: ModelCheck, mutation_fn: str) -> list[str]:
    """Array kwargs for mutations accepting `struct_path` (a trailing leaf).

    Yields `array_path=...` and optionally `struct_path=...`. Inner array
    iteration is rejected -- these mutations consume only the outermost
    array level.
    """
    if not isinstance(check.target, ArrayPath):
        return []
    inner_struct_paths = check.target.iter_struct_paths
    leaf_path = check.target.leaf

    if inner_struct_paths:
        raise ValueError(
            f"{mutation_fn} does not accept inner_array_path "
            f"(inner struct paths={inner_struct_paths!r})"
        )

    kwargs = [f'array_path="{check.target.column_path}"']
    if leaf_path:
        if len(leaf_path) > 1:
            raise ValueError(
                f"multi-segment leaf_path {leaf_path!r} not supported by "
                f"{mutation_fn} (struct_path must be a single segment)"
            )
        kwargs.append(f'struct_path="{leaf_path[0]}"')
    return kwargs


def _array_kwargs_inner(check: ModelCheck, mutation_fn: str) -> list[str]:
    """Array kwargs for mutations accepting `inner_array_path`.

    Yields `array_path=...` and optionally `inner_array_path=...`. A
    trailing leaf path is rejected -- these mutations target an inner
    array directly, not a struct field on its elements.
    """
    if not isinstance(check.target, ArrayPath):
        return []
    inner_struct_paths = check.target.iter_struct_paths
    leaf_path = check.target.leaf

    if leaf_path:
        raise ValueError(
            f"{mutation_fn} does not accept struct_path (leaf_path={leaf_path!r})"
        )

    kwargs = [f'array_path="{check.target.column_path}"']
    if inner_struct_paths:
        if len(inner_struct_paths) > 1:
            raise ValueError(
                f"multi-level inner struct paths {inner_struct_paths!r} not supported by "
                f"{mutation_fn} (inner_array_path consumes one iteration)"
            )
        if not inner_struct_paths[0]:
            raise ValueError(
                f"empty inner struct path not supported by {mutation_fn} "
                f"(target={check.target!r}); nested-iteration arrays without "
                f"intermediate struct fields cannot be addressed via inner_array_path"
            )
        kwargs.append(f'inner_array_path="{".".join(inner_struct_paths[0])}"')
    return kwargs
