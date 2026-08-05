"""Render Check / ModelCheck IR into generated conformance test modules."""

from __future__ import annotations

from typing import Any, NamedTuple

from typing_extensions import assert_never

from overture.schema.system.field_path import (
    ArraySegment,
    Direct,
    FieldPath,
    Iterated,
    MapProjection,
    MapSegment,
)

from ..extraction.field import FieldShape, Primitive
from ..extraction.field_walk import has_array_layer, terminal_of
from ..extraction.specs import ModelSpec
from ..extraction.type_registry import primitive_spark_category
from ._primitive_fill import PRIMITIVE_FILL_TABLE
from ._render_common import (
    disambiguate,
    field_check_rows,
    jinja_env,
    model_check_rows,
    py_literal,
    schema_const_name,
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
    RequireAnyTrue,
    RequireIf,
    model_constraint_function,
    model_mutation_function,
    parse_field_eq,
    require_bool_field_eq,
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
    return all(arm in g.values for g in check.guards if isinstance(g, ColumnGuard))


def _model_check_belongs_to_arm(check: ModelCheck, arm: str) -> bool:
    """Return True when a ModelCheck applies to a given union arm.

    `ModelCheck.arm` is `None` for union-level constraints (which apply
    regardless of discriminator) and set to a discriminator value for
    constraints contributed by one specific member class.
    """
    return check.arm is None or check.arm == arm


def _innermost_iter_segment(target: Iterated) -> ArraySegment | MapSegment:
    """Return the innermost (leaf-most) named iterating segment of *target*."""
    return target.iter_frames[-1][1]


def _first_iter_segment(target: Iterated) -> ArraySegment | MapSegment:
    """Return the outermost (first) named iterating segment of *target*."""
    return target.iter_frames[0][1]


def _is_map_target(target: FieldPath) -> bool:
    """True when *target* reaches its value map-first: no array precedes the map.

    Reads the FIRST iterating frame, matching `check_builder`
    (`_model_constraint_target` and `generate_model_scaffold` both key off
    the outermost frame). A bare or struct-prefixed map projection
    (`names.common{key}`, `sources.license_priority{value}`) is a map target,
    corrupted in place. A map reached only after array iteration
    (`items[].tags{value}`) is array-first, not a map target: its mutation
    descends the array via `set_at_path`'s map grammar. Reading the innermost
    frame instead would misroute the array-first case to a top-level map
    mutation on the array column.
    """
    return isinstance(target, Iterated) and isinstance(
        _first_iter_segment(target), MapSegment
    )


def _is_sole_map_projection(target: Iterated) -> bool:
    """True when *target* is a bare map projection with nothing trailing.

    `names.common{key}`, `sources.license_priority{value}` -- one map frame,
    no struct leaf, no further iteration. These corrupt the map's single
    entry in place via `mutate_map_key` / `mutate_map_value`.
    """
    return not target.leaf and not target.iter_struct_paths


def _map_trailing_iteration_only(target: Iterated) -> bool:
    """True when a map projection is followed only by anonymous iteration.

    `subs{value}[]` (dict[K, list[X]]) and `subs{value}{value}`
    (dict[K, dict[K2, X]]) descend the map value into a container and reach
    the constrained scalar through anonymous `[]` / `{value}` peels alone --
    no named struct navigation, no struct leaf. `set_at_path` with the full
    path peels each trailing container, so the mutation writes the scalar at
    the located slot. A struct leaf (`subs{value}.label`) or a named further
    container (`subs{value}.items[]`) is excluded: it needs navigation
    `set_at_path`'s map-first routing does not cover here.
    """
    return (
        not target.leaf
        and bool(target.iter_struct_paths)
        and all(not prefix for prefix in target.iter_struct_paths)
    )


def render_test_module(
    model_name: str,
    field_checks: list[Check],
    model_checks: list[ModelCheck],
    *,
    expression_import: str,
    support_prefix: str,
    base_row_sparse: dict[str, Any] | None = None,
    base_row_populated: dict[str, Any] | None = None,
    arm: str | None = None,
    spec: ModelSpec | None = None,
) -> str:
    """Render a complete pytest test file for a model's validation checks.

    Arm filtering uses two complementary signals. A field check's
    `ColumnGuard`s identify the arms it belongs to. A model check's `arm`
    attribute is set for member-specific constraints and `None` for
    union-level constraints (which apply to every arm).

    Both label-collision passes run over the *unfiltered* check lists so
    they agree with the expression module, which `renderer` emits once
    across every arm. Each scenario builder takes `arm` and drops rows
    that fall outside it after their suffixes are assigned; computing a
    suffix over an arm subset would let it hide a collision the shared
    module still carries, producing an `expected_field` the module never
    emits.
    """
    model_scenarios, used_mutation_fns = _render_model_scenarios(
        model_name, model_checks, spec, arm
    )
    field_scenarios, field_helpers = _render_field_check_scenarios(
        model_name, field_checks, spec, arm
    )
    used_mutation_fns |= field_helpers - {"set_at_path"}

    sparse_repr = py_literal(base_row_sparse) if base_row_sparse is not None else "{}"
    populated_repr = (
        py_literal(base_row_populated) if base_row_populated is not None else "{}"
    )

    all_scenarios = field_scenarios + model_scenarios

    template = jinja_env().get_template("test_module.py.jinja2")
    return template.render(
        model_name=model_name,
        schema_name=schema_const_name(model_name),
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
    valid_scaffold: dict[str, Any] | None = None,
) -> list[tuple[str, str]]:
    """Build a rendered Scenario kwargs list for the test_module template.

    `valid_scaffold` is emitted only when set, so scenarios without one keep
    the dataclass default (a vacuous base-row copy for the `::valid` row).
    """
    entry = [
        ("id", py_literal(scenario_id)),
        ("scaffold", py_literal(scaffold)),
        ("mutate", mutate_expr),
        ("expected_field", py_literal(expected_field)),
        ("expected_check", py_literal(expected_check)),
    ]
    if valid_scaffold is not None:
        entry.append(("valid_scaffold", py_literal(valid_scaffold)))
    return entry


class _MutateExpr(NamedTuple):
    """One rendered `mutate=` expression and the helper it imports.

    `helper` is `None` when the expression is a literal `set_at_path`
    call (the default), and otherwise names a `mutate_*` helper from
    `tests/_support/mutations.py` to import.
    """

    expr: str
    helper: str | None


def _field_mutate_expr(
    check: Check, desc: ExpressionDescriptor, spec: ModelSpec | None
) -> _MutateExpr:
    """Render the `mutate=` expression for one field-check descriptor.

    A sole map projection corrupts the map's single valid entry via
    `mutate_map_key` / `mutate_map_value`; `check_struct_unique` calls
    `mutate_unique_items` at the target path; every other descriptor --
    including a map value that is itself an iterated container
    (`subs{value}[]`, `subs{value}{value}`) -- injects a constraint-violating
    literal via `set_at_path`, whose path grammar peels each trailing
    container to the constrained scalar.
    """
    target = check.target
    if _is_map_target(target):
        assert isinstance(target, Iterated)
        if _is_sole_map_projection(target):
            return _map_field_mutate_expr(target, desc)
        if not _map_trailing_iteration_only(target):
            raise NotImplementedError(
                f"map-first field check {target!r} descends a struct leaf or a "
                f"named container after the map; no conformance mutation covers it"
            )
        # Iteration-only trailing: fall through to set_at_path with the full
        # path, which descends the map value and peels the trailing containers.
    target_repr = py_literal(str(target))
    if desc.function == "check_struct_unique":
        return _MutateExpr(
            f"lambda row: mutate_unique_items(row, {target_repr})",
            "mutate_unique_items",
        )
    iv_val = _wrap_for_list_leaf(invalid_value(desc), check, spec)
    return _MutateExpr(f"set_at_path({target_repr}, {py_literal(iv_val)})", None)


def _map_field_mutate_expr(target: Iterated, desc: ExpressionDescriptor) -> _MutateExpr:
    """Render the `mutate=` for a sole map-projection field check.

    `mutate_map_key` / `mutate_map_value` corrupt the map's single valid entry
    in place (`names.common{key}`, `sources.license_priority{value}`). The
    caller guarantees a sole projection (`_is_sole_map_projection`); a map
    value that iterates further routes to `set_at_path` instead.
    """
    seg = _first_iter_segment(target)
    assert isinstance(seg, MapSegment)
    helper = (
        "mutate_map_key" if seg.projection is MapProjection.KEY else "mutate_map_value"
    )
    col_repr = py_literal(target.outer_column)
    iv_repr = py_literal(invalid_value(desc))
    return _MutateExpr(f"lambda row: {helper}(row, {col_repr}, {iv_repr})", helper)


def _render_field_check_scenarios(
    model_name: str,
    field_checks: list[Check],
    spec: ModelSpec | None,
    arm: str | None,
) -> tuple[list[list[tuple[str, str]]], set[str]]:
    """Render Scenario entries for field-level checks.

    Returns the entries and the set of mutation helper names referenced
    by them, mirroring `_render_model_scenarios`. `field_check_rows`
    assigns collision suffixes over the unfiltered list; this drops rows
    outside `arm` afterward so per-arm modules carry the labels the shared
    expression module emits. Pass `None` to include all arms.
    """
    rows = [
        row
        for row in field_check_rows(field_checks)
        if arm is None or _check_belongs_to_arm(row.check, arm)
    ]
    scenario_ids = disambiguate(
        [f"{model_name}::{row.label}:{row.name}" for row in rows]
    )

    entries: list[list[tuple[str, str]]] = []
    used_helpers: set[str] = set()
    for row, scenario_id in zip(rows, scenario_ids, strict=True):
        desc = row.check.descriptors[row.descriptor_idx]
        scaffold = generate_scaffold(row.check, spec) if spec is not None else {}
        # For an `X | Literal[c]` field, seed the literal alternative at the
        # target so the `::valid` row proves the check accepts it.
        valid_scaffold: dict[str, Any] | None = None
        if desc.allow_literals and spec is not None:
            # generate_scaffold shapes the bare literal to the field's list
            # nesting, so pass it unwrapped.
            valid_scaffold = generate_scaffold(
                row.check, spec, leaf_value=desc.allow_literals[0]
            )
        try:
            mutate = _field_mutate_expr(row.check, desc, spec)
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
                expected_field=row.label,
                expected_check=row.name,
                valid_scaffold=valid_scaffold,
            )
        )

    return entries, used_helpers


def _checks_array_element(check: Check) -> bool:
    """True when the check fires on each element of an array target directly.

    The check target ends at the array (`leaf=()`), so the mutation
    replaces an array element rather than a struct field on one. For
    these checks, a `None` invalid value still needs list wrapping; for
    nested struct fields, `None` already sits at the right level.
    """
    target = check.target
    return (
        isinstance(target, Iterated)
        and isinstance(_innermost_iter_segment(target), ArraySegment)
        and not target.leaf
    )


def _wrap_for_list_leaf(
    value: object,
    check: Check,
    spec: ModelSpec | None,
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
    model_name: str,
    model_checks: list[ModelCheck],
    spec: ModelSpec | None,
    arm: str | None,
) -> tuple[list[list[tuple[str, str]]], set[str]]:
    """Render Scenario entries for model-level checks.

    Returns the entries and the set of mutation helper names referenced
    by them, so the caller can scope the test module's imports.
    `model_check_rows` assigns collision suffixes over the unfiltered
    list; this drops rows outside `arm` afterward so per-arm modules carry
    the labels the shared expression module emits. Pass `None` to include
    all arms.

    The scenario id's trailing index counts surviving rows within the arm
    (`enumerate` after the filter), not the row's position in the
    unfiltered list -- it is a test-internal disambiguator with no
    cross-module contract, kept contiguous per arm.
    """
    entries: list[list[tuple[str, str]]] = []
    used_mutation_fns: set[str] = set()

    rows = [
        row
        for row in model_check_rows(model_checks)
        if arm is None or _model_check_belongs_to_arm(row.check, arm)
    ]
    for scenario_idx, row in enumerate(rows):
        mc = row.check
        desc = mc.descriptor
        mutation_fn = model_mutation_function(desc)
        scenario_id = f"{model_name}::model:{row.name}:{scenario_idx}"
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
                expected_field=row.label,
                expected_check=row.name,
            )
        )

    return entries, used_mutation_fns


def _reject_non_row_root_target(target: FieldPath, mutation_fn: str) -> None:
    """Raise unless *target* is the row root (empty `Direct`).

    `mutate_radio_group` and `mutate_require_any_true` take no navigation
    kwarg, so they only reach fields at the row root. An `Iterated` target
    (array/map) or a struct-nested `Direct` target (a model reached through a
    plain struct field) would need the constraint's fields nulled/set at a
    nested node the mutation can't reach, so it raises rather than silently
    corrupting top-level columns. No live schema declares `radio_group` or
    `require_any_true` on a nested submodel; supporting one means teaching
    these mutations an `element_path` descent.
    """
    if isinstance(target, Iterated) or (isinstance(target, Direct) and target.segments):
        raise ValueError(
            f"{mutation_fn} does not support a nested target "
            f"(target={target!r}); it reaches only row-root fields"
        )


def _render_mutation_call(
    mutation_fn: str,
    desc: ModelConstraintDescriptor,
    check: ModelCheck,
) -> str:
    """Render a model mutation helper function call."""
    fields_repr = py_literal(list(desc.field_names))

    match desc:
        case RequireAnyTrue():
            # Carries `conditions`, not `field_names`: the mutation disables
            # every condition via a per-field `{field: value}` dict rather than
            # the shared field-name list the other descriptors pass.
            _reject_non_row_root_target(check.target, "mutate_require_any_true")
            return _render_require_any_true_mutation_call(mutation_fn, desc)
        case RequireIf() | ForbidIf():
            return _render_conditional_mutation_call(
                mutation_fn, desc, check, fields_repr
            )
        case RadioGroup():
            _reject_non_row_root_target(check.target, "mutate_radio_group")
            return f"{mutation_fn}(row, {fields_repr})"
        case RequireAnyOf() | MinFieldsSet():
            parts = _iter_kwargs_leaf(check, mutation_fn)
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
    kwarg_parts.extend(_iter_kwargs_inner(check, mutation_fn))
    suffix = ", " + ", ".join(kwarg_parts) if kwarg_parts else ""
    return (
        f"{mutation_fn}(row, {fields_repr}, "
        f"{py_literal(parsed.field_name)}, {py_literal(parsed.value)}{suffix})"
    )


def _render_require_any_true_mutation_call(
    mutation_fn: str, desc: RequireAnyTrue
) -> str:
    """Render a `mutate_require_any_true` call.

    Passes a `{field: disabling_value}` dict that makes every condition false,
    so the invalid row violates `require_any_true` and nothing else. Conditions
    are positive boolean equalities (`require_bool_field_eq`), so each field's
    disabling value is the negation of the boolean the condition tests for.
    """
    parsed = [require_bool_field_eq(c) for c in desc.conditions]
    items = ", ".join(
        f"{py_literal(p.field_name)}: {py_literal(not p.value)}" for p in parsed
    )
    return f"{mutation_fn}(row, {{{items}}})"


def _fill_value_literal(shape: FieldShape) -> str:
    """Return a Python source literal for a type-appropriate non-null fill value."""
    if has_array_layer(shape):
        return "[{}]"
    terminal = terminal_of(shape)
    if isinstance(terminal, Primitive):
        category = primitive_spark_category(terminal.base_type)
        if category in PRIMITIVE_FILL_TABLE:
            return PRIMITIVE_FILL_TABLE[category][0]
        raise ValueError(f"unhandled Primitive base_type: {terminal.base_type!r}")
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


def _composite_element_path_kwargs(target: Iterated) -> list[str]:
    """The `element_path=` kwarg carrying *target*'s full mixed map/array descent.

    No scalar `array_path` / `map_path` expresses a container-after-container
    boundary (a map value that is a list, or a map nested under array
    iteration). The mutation helpers walk the full path generically, so emit
    it verbatim. Every map frame must be a VALUE projection -- a model can't sit
    on a map key -- so a KEY frame raises here rather than emitting a path the
    walker would reject only at runtime (matching `_map_kwargs`'s codegen-time
    guard for the map-first case).
    """
    for _prefix, seg in target.iter_frames:
        if isinstance(seg, MapSegment) and seg.projection is not MapProjection.VALUE:
            raise ValueError(
                f"element_path cannot target a map key (target={target!r}); a "
                "model-level constraint on a map key is not representable as a row"
            )
    return [f'element_path="{target}"']


def _array_first_map_kwargs(target: Iterated) -> list[str] | None:
    """Composite kwargs when a map value sits under array iteration, else None.

    Called on the array-first branch (the first frame is an `ArraySegment`).
    A `MapSegment` anywhere in the frames means the target reaches a
    `dict[K, Model]` value nested under array iteration (e.g.
    `items[].configs{value}`); no scalar array/inner kwarg expresses the map
    boundary, so emit the composite descent path. A pure-array target has no
    map frame and keeps its existing scalar kwargs (returns None).
    """
    if any(isinstance(seg, MapSegment) for _prefix, seg in target.iter_frames):
        return _composite_element_path_kwargs(target)
    return None


def _map_kwargs(target: Iterated, mutation_fn: str, *, allow_leaf: bool) -> list[str]:
    """Mutation kwargs for a `dict[K, Model]` value-model constraint.

    Emits `map_path=...` (the map column) and, when `allow_leaf`, an
    optional single-segment `struct_path=...` for a sub-model reached
    through one struct field inside the value model -- the map analogue of
    `_iter_kwargs_leaf`'s array `struct_path`. A KEY projection is
    unrepresentable (a model can't be a dict key) and raises. A map value that
    is itself iterated (`dict[K, list[Model]]`, target `subs{value}[]`) folds
    its trailing container into this same named frame, so `iter_struct_paths`
    is non-empty; the map value is a container, not the model, so emit the
    composite descent path the mutation walks instead of `map_path=...`. A
    multi-segment leaf, or any leaf when `allow_leaf` is False, raises.
    """
    seg = _first_iter_segment(target)
    assert isinstance(seg, MapSegment)
    if seg.projection is not MapProjection.VALUE:
        raise ValueError(
            f"{mutation_fn} cannot target a map key (target={target!r}); a "
            "model-level constraint on a map key is not representable as a row"
        )
    if target.iter_struct_paths:
        return _composite_element_path_kwargs(target)
    kwargs = [f'map_path="{target.outer_column}"']
    leaf = target.leaf
    if leaf:
        if not allow_leaf:
            raise ValueError(
                f"{mutation_fn} does not accept a map-value leaf (leaf={leaf!r})"
            )
        if len(leaf) > 1:
            raise ValueError(
                f"multi-segment map-value leaf {leaf!r} not supported by "
                f"{mutation_fn} (struct_path must be a single segment)"
            )
        kwargs.append(f'struct_path="{leaf[0]}"')
    return kwargs


def _struct_nested_kwargs(target: Direct) -> list[str]:
    """Container kwargs for a model constraint on a struct-nested submodel.

    A row-root constraint (empty `Direct`) needs no navigation and yields no
    kwargs. A model reached through one or more plain struct fields yields
    `element_path=...` -- the pure-struct descent (`_descend_to_targets` in
    `mutations.py`) that scaffolds each struct on the way and applies the
    mutation to the constrained model, mirroring how iterated targets pass
    `array_path` / `map_path`.
    """
    return [f'element_path="{target}"'] if target.segments else []


def _iter_kwargs_leaf(check: ModelCheck, mutation_fn: str) -> list[str]:
    """Container kwargs for mutations accepting `struct_path` (a trailing leaf).

    For an array target, yields `array_path=...` and optionally
    `struct_path=...`; inner array iteration is rejected -- these mutations
    consume only the outermost array level. For a map target (a
    `dict[K, Model]` value-model constraint), delegates to `_map_kwargs`,
    which yields `map_path=...` and an optional single-segment `struct_path`.
    A struct-nested `Direct` target (a model reached through a plain struct
    field) yields `element_path=...`, the pure-struct descent the mutation
    walks to reach the constrained model.
    """
    target = check.target
    if isinstance(target, Direct):
        return _struct_nested_kwargs(target)
    if isinstance(_first_iter_segment(target), MapSegment):
        return _map_kwargs(target, mutation_fn, allow_leaf=True)
    composite = _array_first_map_kwargs(target)
    if composite is not None:
        return composite
    if target.iter_struct_paths:
        raise ValueError(
            f"{mutation_fn} does not accept inner_array_path "
            f"(inner struct paths={target.iter_struct_paths!r})"
        )

    kwargs = [f'array_path="{target.outer_column}"']
    if target.leaf:
        if len(target.leaf) > 1:
            raise ValueError(
                f"multi-segment leaf_path {target.leaf!r} not supported by "
                f"{mutation_fn} (struct_path must be a single segment)"
            )
        kwargs.append(f'struct_path="{target.leaf[0]}"')
    return kwargs


def _iter_kwargs_inner(check: ModelCheck, mutation_fn: str) -> list[str]:
    """Container kwargs for mutations accepting `inner_array_path`.

    For an array target, yields `array_path=...` and optionally
    `inner_array_path=...`; a trailing leaf path is rejected -- these
    mutations target an inner array directly, not a struct field on its
    elements. For a map target, delegates to `_map_kwargs` (no leaf: a map
    value has no inner array layer to address). A struct-nested `Direct`
    target yields `element_path=...` (the pure-struct descent to the model).
    """
    target = check.target
    if isinstance(target, Direct):
        return _struct_nested_kwargs(target)
    if isinstance(_first_iter_segment(target), MapSegment):
        return _map_kwargs(target, mutation_fn, allow_leaf=False)
    composite = _array_first_map_kwargs(target)
    if composite is not None:
        return composite
    if target.leaf:
        raise ValueError(
            f"{mutation_fn} does not accept struct_path (leaf_path={target.leaf!r})"
        )

    kwargs = [f'array_path="{target.outer_column}"']
    if target.iter_struct_paths:
        if len(target.iter_struct_paths) > 1:
            raise ValueError(
                f"multi-level inner struct paths {target.iter_struct_paths!r} not "
                f"supported by {mutation_fn} (inner_array_path consumes one iteration)"
            )
        if not target.iter_struct_paths[0]:
            raise ValueError(
                f"empty inner struct path not supported by {mutation_fn} "
                f"(target={target!r}); nested-iteration arrays without "
                f"intermediate struct fields cannot be addressed via inner_array_path"
            )
        kwargs.append(f'inner_array_path="{".".join(target.iter_struct_paths[0])}"')
    return kwargs
