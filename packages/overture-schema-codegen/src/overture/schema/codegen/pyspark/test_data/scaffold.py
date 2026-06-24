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
    ArrayPath,
    ArraySegment,
    FieldPath,
    FieldSegment,
)

from ...extraction.field_walk import has_array_layer, list_depth, terminal_model_ref
from ...extraction.specs import FieldSpec, ModelSpec
from ..check_ir import (
    Check,
    ElementGuard,
    ModelCheck,
)
from .base_row import value_for_field

__all__ = [
    "generate_model_scaffold",
    "generate_scaffold",
    "leaf_list_depth",
]


@dataclass(frozen=True, slots=True)
class _ElementDiscriminator:
    """Discriminator value to seed at one nesting depth of the scaffold."""

    field: str
    value: str
    depth: int


def _find_field_spec(fields: list[FieldSpec], name: str) -> FieldSpec | None:
    """Find a FieldSpec by name in a list."""
    for f in fields:
        if f.name == name:
            return f
    return None


def leaf_list_depth(field_path: FieldPath, spec: ModelSpec) -> int:
    """Return the unaccounted-for list depth of the leaf field.

    Walks the spec's field tree along *field_path* and returns the
    leaf's `list_depth(shape)` minus any `iter_count` on the terminal
    path segment. Paths whose terminal segment is itself an array
    target the array's elements, so the mutation already operates one
    level deep. Returns 0 when *field_path* is empty or when any
    segment fails to resolve against *spec* (e.g. union arms that
    don't share the path's intermediate fields).
    """
    segments = field_path.segments
    if not segments:
        return 0
    fields = list(spec.fields)
    for seg in segments[:-1]:
        field = _find_field_spec(fields, seg.name)
        if field is None:
            return 0
        model_ref = terminal_model_ref(field.shape)
        if model_ref is None:
            return 0
        fields = model_ref.model.fields
    leaf_seg = segments[-1]
    leaf = _find_field_spec(fields, leaf_seg.name)
    if leaf is None:
        return 0
    terminal_iter = leaf_seg.iter_count if isinstance(leaf_seg, ArraySegment) else 0
    return max(0, list_depth(leaf.shape) - terminal_iter)


def _required_siblings(
    fields: list[FieldSpec], exclude: str, spec_name: str
) -> dict[str, Any]:
    """Populate required siblings at one nesting level, excluding the target."""
    result: dict[str, Any] = {}
    for f in fields:
        if f.name == exclude or not f.is_required:
            continue
        result[f.name] = value_for_field(f, spec_name)
    return result


def _walk_to_target(
    segments: tuple[FieldSegment, ...],
    fields: list[FieldSpec],
    spec_name: str,
    *,
    discriminator: _ElementDiscriminator | None,
    current_depth: int = 0,
) -> dict[str, Any]:
    """Recursively build the scaffold dict along the path segments.

    Accepts any `FieldSegment`: struct steps recurse, an `ArraySegment`
    wraps its inner value in lists, and a trailing `MapSegment` resolves
    via `value_for_field` (which populates the map with a valid entry),
    so a `MapPath` target scaffolds the same way as a struct terminal.
    """
    if not segments:
        return {}

    seg = segments[0]
    remaining = segments[1:]
    field_spec = _find_field_spec(fields, seg.name)

    inner: Any
    child_model = (
        terminal_model_ref(field_spec.shape) if field_spec is not None else None
    )
    if remaining and child_model is not None:
        child_fields = child_model.model.fields
        inner = _walk_to_target(
            remaining,
            child_fields,
            spec_name,
            discriminator=discriminator,
            current_depth=current_depth + 1,
        )
        siblings = _required_siblings(child_fields, remaining[0].name, spec_name)
        inner = {**siblings, **inner}
    elif not remaining and field_spec is not None:
        inner = value_for_field(field_spec, spec_name)
    else:
        inner = {}

    if (
        isinstance(inner, dict)
        and discriminator is not None
        and current_depth == discriminator.depth
    ):
        inner[discriminator.field] = discriminator.value

    # When the terminal segment is an array and the field itself is a list,
    # `value_for_field` already wrapped the value -- skip extra wrapping.
    if isinstance(seg, ArraySegment):
        if (
            not remaining
            and field_spec is not None
            and has_array_layer(field_spec.shape)
        ):
            return {seg.name: inner}
        wrapped: Any = inner
        for _ in range(seg.iter_count):
            wrapped = [wrapped]
        return {seg.name: wrapped}
    if remaining and field_spec is not None and has_array_layer(field_spec.shape):
        return {seg.name: [inner]}
    return {seg.name: inner}


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


def generate_scaffold(check: Check, spec: ModelSpec) -> dict[str, Any]:
    """Build a sparse dict from null to the target field of a Check."""
    segments = check.target.segments
    if not segments:
        return {}

    if len(segments) == 1:
        seg0 = segments[0]
        field_spec = _find_field_spec(spec.fields, seg0.name)
        if field_spec is None or field_spec.is_required:
            return {}
        return {seg0.name: value_for_field(field_spec, spec.name)}

    return _walk_to_target(
        segments,
        spec.fields,
        spec.name,
        discriminator=_element_discriminator(check),
    )


def generate_model_scaffold(check: ModelCheck, spec: ModelSpec) -> dict[str, Any]:
    """Build a sparse dict for a model-level check's nesting structure.

    Only top-level array columns are supported -- a `ScalarPath` target
    returns `{}` (no scaffold needed at row root) and an `ArrayPath`
    whose column lives inside a struct raises `NotImplementedError`.
    No schema today places a list of model-constrained models inside a
    struct field, so the case has no test coverage.
    """
    match check.target:
        case ArrayPath() as target:
            pass
        case _:
            return {}
    column_prefix = target.column_prefix
    if column_prefix.segments:
        raise NotImplementedError(
            "Multi-segment column paths (struct fields containing arrays) "
            "require walking the parent tree from the root to the array "
            f"column; got {target!r}"
        )

    field_spec = _find_field_spec(spec.fields, target.column_path)
    if field_spec is None:
        return {}

    inner_levels = target.iter_struct_paths
    leaf_path = target.leaf

    inner: dict[str, Any] = {}
    root_model = terminal_model_ref(field_spec.shape)
    current_fields: list[FieldSpec] = root_model.model.fields if root_model else []
    nested = inner

    for level in inner_levels:
        for part in level:
            child_spec = _find_field_spec(current_fields, part)
            child_is_list = child_spec is not None and has_array_layer(child_spec.shape)
            child_model = (
                terminal_model_ref(child_spec.shape) if child_spec is not None else None
            )
            if child_is_list:
                nested[part] = [{}]
                nested = nested[part][0]
            else:
                nested[part] = {}
                nested = nested[part]
            current_fields = child_model.model.fields if child_model else []

    for part in leaf_path:
        nested[part] = {}
        nested = nested[part]

    if has_array_layer(field_spec.shape):
        return {target.column_path: [inner]}
    return {target.column_path: inner} if inner else {}
