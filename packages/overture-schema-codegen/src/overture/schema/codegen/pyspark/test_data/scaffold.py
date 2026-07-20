"""Generate sparse path scaffolds for the rendered conformance tests.

`generate_scaffold` builds a sparse dict that, when merged with a base
row, supplies the nested intermediates (optional structs, arrays) the
base row lacks but a check's field path requires.
`generate_model_scaffold` does the same for model-level constraints.
`leaf_list_depth` reports unaccounted-for list depth on a target field.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from overture.schema.system.field_path import (
    ArraySegment,
    FieldPath,
    FieldSegment,
    Iterated,
    MapSegment,
    terminal_run_start,
)

from ...extraction.field_walk import (
    has_array_layer,
    list_depth,
    terminal_model_ref,
    terminal_union_ref,
)
from ...extraction.specs import FieldSpec, ModelSpec, RecordSpec
from ..check_ir import (
    Check,
    ElementGuard,
    ModelCheck,
)
from .base_row import (
    condition_overrides_for_present_field,
    generate_base_row,
    resolve_arm_spec,
    value_for_field,
)

__all__ = [
    "generate_model_scaffold",
    "generate_scaffold",
    "leaf_list_depth",
]

# Sentinel for "no leaf override": the terminal field keeps its synthesized
# value. A `None` / `""` leaf override is meaningful, so it cannot be the
# default.
_UNSET: object = object()


def _nest_leaf_value(value: object, field_spec: FieldSpec) -> object:
    """Wrap a scalar leaf override to the field's list nesting depth.

    `value_for_field` returns a list for a list-typed field, so a bare scalar
    override (e.g. a literal alternative) is wrapped to the same depth: `[v]`
    for `list[T]`, `[[v]]` for `list[list[T]]`, and `v` for a scalar field.
    """
    for _ in range(list_depth(field_spec.shape)):
        value = [value]
    return value


@dataclass(frozen=True, slots=True)
class _ElementDiscriminator:
    """Discriminator value to seed at one nesting depth of the scaffold."""

    field: str
    value: str
    depth: int


def _is_anonymous_iter(seg: FieldSegment) -> bool:
    """True when *seg* iterates a container nested directly inside another.

    In a run of nested containers the first takes the field's name; each
    further level is *anonymous*, because no field name introduces it -- the
    parent element is itself the next container. For `grid: list[list[int]]`
    the path `grid[][]` is a named `ArraySegment("grid")` followed by an
    anonymous `ArraySegment("")`; this returns False for the first and True
    for the second, the "extra" iteration past the named `grid`.
    """
    return isinstance(seg, (ArraySegment, MapSegment)) and seg.is_anonymous


def _find_field_spec(fields: list[FieldSpec], name: str) -> FieldSpec | None:
    """Find a FieldSpec by name in a list."""
    for f in fields:
        if f.name == name:
            return f
    return None


def leaf_list_depth(field_path: FieldPath, spec: ModelSpec) -> int:
    """Return the unaccounted-for list depth of the leaf field.

    Walks the spec's field tree along *field_path* and returns the leaf's
    `list_depth(shape)` minus the path's own trailing iteration depth at
    the leaf. The leaf is the last *named* segment -- any anonymous
    `ArraySegment`s after it are further list-nesting of that same field,
    not a lookup of their own, and are skipped both when descending the
    field tree and when counting how much depth the path already covers.
    Paths whose terminal segment is itself an array target the array's
    elements, so the mutation already operates one level deep. Returns 0
    when *field_path* is empty or when any segment fails to resolve
    against *spec* (e.g. union arms that don't share the path's
    intermediate fields).
    """
    segments = field_path.segments
    if not segments:
        return 0

    leaf_index = terminal_run_start(segments)
    leaf_seg = segments[leaf_index]
    terminal_iter = (
        (len(segments) - leaf_index) if isinstance(leaf_seg, ArraySegment) else 0
    )

    fields = list(spec.fields)
    for seg in segments[:leaf_index]:
        if isinstance(seg, ArraySegment) and seg.is_anonymous:
            continue
        field = _find_field_spec(fields, seg.name)
        if field is None:
            return 0
        model_ref = terminal_model_ref(field.shape)
        if model_ref is None:
            return 0
        fields = model_ref.model.fields

    leaf = _find_field_spec(fields, leaf_seg.name)
    if leaf is None:
        return 0
    return max(0, list_depth(leaf.shape) - terminal_iter)


def _child_container_spec(
    field_spec: FieldSpec, discriminator_value: object | None
) -> RecordSpec | None:
    """Resolve the model a path field descends into.

    Returns the field's terminal `ModelRef` model, or -- for a discriminated
    union -- the member arm the `discriminator_value` selects (the widest
    member when the check is not arm-gated). `None` when the field has neither
    a model nor a union terminal.
    """
    model_ref = terminal_model_ref(field_spec.shape)
    if model_ref is not None:
        return model_ref.model
    union_ref = terminal_union_ref(field_spec.shape)
    if union_ref is not None:
        return resolve_arm_spec(union_ref.union, discriminator_value)
    return None


def _walk_to_target(
    segments: tuple[FieldSegment, ...],
    fields: list[FieldSpec],
    spec_name: str,
    *,
    discriminator: _ElementDiscriminator | None,
    current_depth: int = 0,
    leaf_value: object = _UNSET,
) -> dict[str, Any]:
    """Recursively build a constraint-satisfying scaffold along the path.

    Each container model on the path is built as a valid base row
    (`generate_base_row` -- required fields populated and model constraints
    such as `require_any_of` satisfied), then the on-path child overrides its
    field. A discriminated-union element resolves to the arm the seeded
    discriminator selects (or the widest member when the check is not
    arm-gated), so the element is a valid instance of a concrete arm rather
    than an untagged `{}`.

    Accepts any `FieldSegment`: struct steps recurse, an `ArraySegment`
    wraps its inner value in lists, and a trailing `MapSegment` resolves
    via `value_for_field` (which populates the map with a valid entry),
    so a map-projection target scaffolds the same way as a struct terminal.

    `leaf_value`, when set, replaces the synthesized value at the terminal
    field -- used to seed a specific valid value (e.g. a literal alternative)
    at the check's target.
    """
    if not segments:
        return {}

    seg = segments[0]
    remaining = segments[1:]
    field_spec = _find_field_spec(fields, seg.name)

    # A path segment that resolves to no field, or that tries to descend into a
    # non-container, would leave the scaffold short of its target -- the
    # `::valid` row would then assert nothing (the vacuous-valid-row bug this
    # generator exists to prevent). Fail loud at generation time instead.
    if field_spec is None:
        raise ValueError(
            f"scaffold path segment {seg.name!r} matches no field "
            f"(available: {sorted(f.name for f in fields)})"
        )

    # Anonymous iterating segments immediately after `seg` are further
    # container-nesting of THIS SAME field (`list[list[...]]`,
    # `dict[K, dict[K2, ...]]`, no intervening field name), not separate
    # lookups -- `generate_base_row`/`value_for_field` resolve straight
    # through every list and map layer, so peeling the run here (rather than
    # recursing anonymous-segment-by-segment) keeps the base-row merge below
    # anchored on the field `seg` actually names. `extra_iter` carries only the
    # ARRAY levels to the wrap step; anonymous map levels need no manual
    # wrapping, since `value_for_field` nests the map itself.
    extra_iter = 0
    while remaining and _is_anonymous_iter(remaining[0]):
        if isinstance(remaining[0], ArraySegment):
            extra_iter += 1
        remaining = remaining[1:]

    inner: Any
    if remaining:
        discriminator_value = (
            discriminator.value
            if discriminator is not None and current_depth == discriminator.depth
            else None
        )
        child_spec = _child_container_spec(field_spec, discriminator_value)
        if child_spec is None:
            raise ValueError(
                f"scaffold cannot descend into non-container field {seg.name!r} "
                f"with path remaining {[s.name for s in remaining]!r}"
            )
        recursed = _walk_to_target(
            remaining,
            child_spec.fields,
            spec_name,
            discriminator=discriminator,
            current_depth=current_depth + 1 + extra_iter,
            leaf_value=leaf_value,
        )
        inner = {**generate_base_row(child_spec), **recursed}
    elif leaf_value is not _UNSET:
        inner = _nest_leaf_value(leaf_value, field_spec)
    else:
        inner = value_for_field(field_spec, spec_name)

    if (
        isinstance(inner, dict)
        and discriminator is not None
        and current_depth == discriminator.depth
    ):
        inner[discriminator.field] = discriminator.value

    # When the terminal segment is an array and the field itself is a list,
    # `value_for_field` already wrapped the value -- skip extra wrapping.
    if isinstance(seg, ArraySegment):
        if not remaining and has_array_layer(field_spec.shape):
            return {seg.name: inner}
        # A single-level array (extra_iter == 0) gets a constraint-valid list;
        # nested `list[list[...]]` levels (extra_iter > 0) carry no min_length>1
        # or uniqueness constraint in any current schema, so minimal nesting
        # suffices. Add per-level constraint handling here if one ever does --
        # the row would otherwise be short on the unmutated `::valid` row.
        if extra_iter == 0:
            return {seg.name: _array_with_target(inner, field_spec, spec_name)}
        wrapped: Any = inner
        for _ in range(1 + extra_iter):
            wrapped = [wrapped]
        return {seg.name: wrapped}
    if remaining and has_array_layer(field_spec.shape):
        return {seg.name: _array_with_target(inner, field_spec, spec_name)}
    return {seg.name: inner}


def _array_with_target(
    target_element: object, field_spec: FieldSpec, spec_name: str
) -> list[Any]:
    """Return a constraint-valid single-level list holding the target element.

    `value_for_field` builds a list that satisfies the field's array
    constraints (min length, unique items); the target-reaching element
    replaces the first slot. A min_length>1 or uniqueness constraint then
    holds on the unmutated `::valid` row -- a bare `[target_element]` would
    leave the row short or, after `deep_merge` replaces the base row's list,
    drop the elements that satisfied the constraint.
    """
    full = value_for_field(field_spec, spec_name)
    if isinstance(full, list) and full:
        full[0] = target_element
        return full
    return [target_element]


def _element_discriminator(check: Check) -> _ElementDiscriminator | None:
    """Return the element-level discriminator for a Check, or None.

    Bundles the discriminator field, the value to seed, and the depth at
    which to seed it (the innermost array segment in the target path).
    The check_ir invariant is that nested-union gating composes at most
    one `ElementGuard` per Check; more than one would mean the gate
    composition rule changed without updating the scaffold, so raise to
    surface the gap rather than silently dropping guards.
    """
    element_guards = [g for g in check.guards if isinstance(g, ElementGuard)]
    if len(element_guards) > 1:
        raise NotImplementedError(
            f"Check carries {len(element_guards)} ElementGuards "
            f"({element_guards!r}); the scaffold only seeds one. Update "
            "the scaffold builder when the gate composition rule changes."
        )
    if not element_guards or not element_guards[0].values:
        return None
    guard = element_guards[0]
    segments = check.target.segments
    for i in range(len(segments) - 1, -1, -1):
        if isinstance(segments[i], ArraySegment):
            return _ElementDiscriminator(
                field=guard.discriminator, value=guard.values[0], depth=i
            )
    return None


def generate_scaffold(
    check: Check, spec: ModelSpec, *, leaf_value: object = _UNSET
) -> dict[str, Any]:
    """Build a sparse dict from null to the target field of a Check.

    `leaf_value`, when set, seeds that value at the target instead of the
    field's synthesized value -- used to place a known-valid value (e.g. a
    literal alternative) at the check's target for the `::valid` row.
    """
    segments = check.target.segments
    if not segments:
        return {}

    if len(segments) == 1:
        seg0 = segments[0]
        field_spec = _find_field_spec(spec.fields, seg0.name)
        if field_spec is None:
            return {}
        # A `forbid_if` the base row triggers forbids this field; disable the
        # condition so the field can be set without invalidating the row.
        overrides = condition_overrides_for_present_field(spec, seg0.name)
        if leaf_value is not _UNSET:
            return {**overrides, seg0.name: _nest_leaf_value(leaf_value, field_spec)}
        if field_spec.is_required:
            return {}
        return {**overrides, seg0.name: value_for_field(field_spec, spec.name)}

    return _walk_to_target(
        segments,
        spec.fields,
        spec.name,
        discriminator=_element_discriminator(check),
        leaf_value=leaf_value,
    )


def generate_model_scaffold(check: ModelCheck, spec: ModelSpec) -> dict[str, Any]:
    """Build a constraint-satisfying scaffold for a model-level check.

    Two target shapes need no scaffold and return `{}`:

    - a `Direct` target -- a top-level model constraint, whose fields live
      at the row root;
    - a map-first `Iterated` target -- a `dict[K, Model]` value-model
      constraint. The mutation (`map_path=`) owns map navigation: it corrupts
      the base row's single map entry in place, or stubs one when the map is
      absent. Unlike an array, a dict scaffold can't replace a base-row map
      entry under `deep_merge`'s recursive dict merge, so there is nothing to
      add here.

    An array-first `Iterated` target walks the path with `_walk_to_target`:
    every model on the way -- including the constrained model at the leaf --
    is built as a valid base row, so the constraint under test (e.g. a
    scope's `require_any_of`) is satisfied on the unmutated `::valid` row and
    the only violation is the one the mutation introduces.

    An `Iterated` target is array-first exactly when its outermost frame is
    an `ArraySegment` (guaranteed named, so it heads `iter_frames`); a
    map-first target's mutation owns navigation, matching the former
    map-path case.
    """
    target = check.target
    if isinstance(target, Iterated) and isinstance(
        target.iter_frames[0][1], ArraySegment
    ):
        return _walk_to_target(
            target.segments, spec.fields, spec.name, discriminator=None
        )
    return {}
