"""Walk FieldSpec trees to produce Check/ModelCheck IR for rendering.

Consults the constraint dispatch table to map each constraint to a
descriptor, then applies composition rules the dispatch table can't see:

- Coalesce ordering: gather descriptors for the same field into one
  `Check` (required first, then enum, then dispatched constraints),
  deduplicate, and split column-level checks into separate suffixed checks.
- Target resolution: a shape walker descends each field's `FieldShape`
  tree, building the `ScalarPath` or `ArrayPath` target by appending
  segments as it goes -- so the path read in the code is the path that
  lands in the IR. Entering a `list[...]` layer promotes the path's
  terminal struct segment to an iterated `ArraySegment`.
- Subtype gating: annotate variant-specific fields with discriminator
  `Guard`s, synthesize forbid_if/require_if for absent or required
  variants, and gate check_required under nullable struct ancestors.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace

from pydantic import BaseModel
from typing_extensions import assert_never

from overture.schema.system.field_path import (
    ArrayPath,
    ArraySegment,
    FieldPath,
    MapPath,
    MapProjection,
    MapSegment,
    ScalarPath,
    promote_terminal_array,
    promote_terminal_map,
)
from overture.schema.system.model_constraint import (
    FieldEqCondition,
    ModelConstraint,
    Not,
)

from ..extraction.field import (
    AnyScalar,
    ArrayOf,
    ConstraintSource,
    FieldShape,
    LiteralScalar,
    MapOf,
    ModelRef,
    NewTypeShape,
    Primitive,
    Scalar,
    UnionRef,
)
from ..extraction.field_walk import (
    all_constraints,
    enum_source,
    has_array_layer,
    terminal_of,
    terminal_primitive,
    terminal_scalar,
)
from ..extraction.specs import FieldSpec, ModelSpec, RecordSpec, UnionSpec
from ..extraction.type_registry import PRIMITIVE_TYPES
from ._render_common import COLUMN_LEVEL_FUNCTIONS
from .check_ir import (
    Check,
    ColumnGuard,
    ElementGuard,
    Guard,
    ModelCheck,
)
from .constraint_dispatch import (
    ExpressionDescriptor,
    ForbidIf,
    RequireIf,
    dispatch_base_type,
    dispatch_constraint,
    dispatch_model_constraint,
    dispatch_newtype,
    forbid_if_field_shapes,
)

__all__ = [
    "build_checks",
]


def _dispatch_layer_constraints(
    constraints: tuple[ConstraintSource, ...],
    base_type: str | None,
) -> list[ExpressionDescriptor]:
    """Dispatch one shape layer's constraints, skipping primitive-inherent ones."""
    descriptors: list[ExpressionDescriptor] = []
    for cs in constraints:
        if cs.source_name is not None and cs.source_name in PRIMITIVE_TYPES:
            continue
        desc = dispatch_constraint(cs.constraint, base_type=base_type)
        if desc is not None:
            descriptors.append(desc)
    return descriptors


def _enum_values(scalar: Scalar) -> list[object] | None:
    """Return enum/literal values for a terminal `Scalar`, or `None`."""
    if isinstance(scalar, LiteralScalar):
        return list(scalar.values)
    src = enum_source(scalar)
    if src is not None:
        return [m.value for m in src]
    return None


def _required_descriptor(gate: FieldPath | None) -> ExpressionDescriptor:
    return ExpressionDescriptor(function="check_required", gate=gate)


@dataclass(frozen=True, slots=True)
class _ShapeTerminal:
    """A `ModelRef`/`UnionRef` terminal and the path the walker reached it at.

    The `FieldSpec` recursion uses `path` directly as the prefix for the
    sub-model's or sub-union's fields. The walker returns `None` instead
    of a `_ShapeTerminal` for terminals it fully handles itself (scalars,
    maps, and NewTypes with a dispatch override).
    """

    ref: ModelRef | UnionRef
    path: FieldPath


def _walk_field_shape(
    shape: FieldShape,
    path: FieldPath,
    *,
    base_type: str | None,
    required: bool,
    required_gate: FieldPath | None,
    carried_element: list[ExpressionDescriptor],
) -> tuple[list[Check], _ShapeTerminal | None]:
    """Descend a `FieldShape`, emitting the field's own Checks.

    Builds the `FieldPath` target structurally: `ArrayOf` promotes the
    path's terminal segment, `NewTypeShape` passes the path through,
    terminals emit at the path reached. Returns the emitted Checks plus,
    at a `ModelRef`/`UnionRef` terminal, a `_ShapeTerminal` for the
    `FieldSpec` recursion (`None` for terminals the walker fully handles).

    Parameters
    ----------
    path
        The path reached so far, promoted once per `ArrayOf` layer
        crossed. `required` and `path` move together: a field's path
        starts as a plain struct path and is promoted exactly when the
        first `ArrayOf` clears `required`, so while `required` holds the
        path is still the plain struct path -- a standalone
        `check_required` always lands there.
    required
        Whether the field still needs a `check_required`. Cleared by the
        first `ArrayOf`: before it, `check_required` merges into the
        terminal Check; from it on, it is a standalone column-level Check.
    carried_element
        Element-level descriptors from `ArrayOf` layers above, prepended
        to the terminal's own element-level descriptors.
    """
    match shape:
        case NewTypeShape(name=name, inner=inner):
            nt_descriptors = dispatch_newtype(name)
            if nt_descriptors is not None:
                if isinstance(path.segments[-1], ArraySegment):
                    # A NewType with a dispatch override nested under a list
                    # layer has no schema field; raise to keep the gap loud
                    # rather than emit an untested target (cf. list[list[Union]]).
                    raise NotImplementedError(
                        f"NewType with a dispatch override ({name}) nested "
                        "under a list layer is not supported"
                    )
                descriptors = list(nt_descriptors)
                if required:
                    descriptors.insert(0, _required_descriptor(required_gate))
                return [Check(descriptors=tuple(descriptors), target=path)], None
            return _walk_field_shape(
                inner,
                path,
                base_type=base_type,
                required=required,
                required_gate=required_gate,
                carried_element=carried_element,
            )

        case ArrayOf(element=element, constraints=constraints):
            layer_descriptors = _dispatch_layer_constraints(
                constraints,
                base_type,
            )
            column_descriptors = list(
                dict.fromkeys(
                    d for d in layer_descriptors if d.function in COLUMN_LEVEL_FUNCTIONS
                )
            )
            element_descriptors = [
                d for d in layer_descriptors if d.function not in COLUMN_LEVEL_FUNCTIONS
            ]
            checks: list[Check] = []
            if required:
                checks.append(
                    Check(
                        descriptors=(_required_descriptor(required_gate),),
                        target=path,
                    )
                )
            checks.extend(
                Check(descriptors=(d,), target=path) for d in column_descriptors
            )
            sub_checks, terminal = _walk_field_shape(
                element,
                promote_terminal_array(path),
                base_type=base_type,
                required=False,
                required_gate=required_gate,
                carried_element=[*carried_element, *element_descriptors],
            )
            return [*checks, *sub_checks], terminal

        case UnionRef():
            terminal_seg = path.segments[-1]
            if isinstance(terminal_seg, ArraySegment) and terminal_seg.iter_count > 1:
                # `list[list[Union]]` would build a multi-iter union target,
                # but no schema field has that shape. The walker raises to
                # keep the gap loud rather than silently emit one.
                raise NotImplementedError(
                    "Union nested under multiple list layers "
                    "(list[list[Union]]) is not supported"
                )
            return _ref_terminal_checks(shape, path, required, required_gate)

        case ModelRef():
            return _ref_terminal_checks(shape, path, required, required_gate)

        case Primitive() | LiteralScalar() | AnyScalar():
            return _terminal_scalar_checks(
                shape,
                path,
                base_type=base_type,
                required=required,
                required_gate=required_gate,
                carried_element=carried_element,
            ), None

        case MapOf(key=key_shape, value=value_shape):
            # A map is itself a terminal column: its own value carries the
            # required check and any map-level constraints (currently always
            # empty -- map-level length constraints are rejected at
            # extraction). The key and value layers are walked separately so
            # their per-key/per-value constraints land on `MapPath` targets.
            # A `ModelRef`/`UnionRef` projection hands back a `_ShapeTerminal`
            # for the caller to descend into, exactly as a `list[Model]`
            # element does.
            field_checks = _terminal_scalar_checks(
                shape,
                path,
                base_type=base_type,
                required=required,
                required_gate=required_gate,
                carried_element=carried_element,
            )
            key_checks, key_terminal = _map_projection_checks(
                key_shape, path, MapProjection.KEY
            )
            value_checks, value_terminal = _map_projection_checks(
                value_shape, path, MapProjection.VALUE
            )
            if key_terminal is not None and value_terminal is not None:
                raise NotImplementedError(
                    "map with a model key and a model value is not supported"
                )
            terminal = value_terminal if value_terminal is not None else key_terminal
            return [*field_checks, *key_checks, *value_checks], terminal

    assert_never(shape)


def _terminal_scalar_checks(
    shape: Scalar | MapOf,
    path: FieldPath,
    *,
    base_type: str | None,
    required: bool,
    required_gate: FieldPath | None,
    carried_element: list[ExpressionDescriptor],
) -> list[Check]:
    """Build the Check(s) for a terminal value: enum, constraints, base type.

    Shared by the scalar-terminal arm and a map field's own value -- a
    `MapOf` is itself a terminal column, distinct from its key/value layers.
    """
    element_descriptors = list(carried_element)
    enum_values = _enum_values(shape) if isinstance(shape, Scalar) else None
    if enum_values is not None:
        element_descriptors.append(
            ExpressionDescriptor(function="check_enum", args=(tuple(enum_values),))
        )
    element_descriptors.extend(
        _dispatch_layer_constraints(shape.constraints, base_type)
    )
    if base_type is not None:
        base_descriptors = dispatch_base_type(base_type)
        if base_descriptors is not None:
            element_descriptors.extend(base_descriptors)
    element_descriptors = list(dict.fromkeys(element_descriptors))

    if required:
        return [
            Check(
                descriptors=(_required_descriptor(required_gate), *element_descriptors),
                target=path,
            )
        ]
    if element_descriptors:
        return [Check(descriptors=tuple(element_descriptors), target=path)]
    return []


@dataclass(frozen=True)
class MapProjectionVerdict:
    """Whether a map's projected key/value shape is representable as a `MapPath`.

    `reason` names why an unrepresentable shape was rejected (for the
    `NotImplementedError` message); it is `None` when `representable` is True.
    `has_value_to_validate` reports whether the projected shape carries a
    constraint or descends into a model -- the loud/quiet discriminator: an
    unrepresentable shape with something to validate raises, an unrepresentable
    shape with nothing to validate is silently dropped.
    """

    representable: bool
    reason: str | None
    has_value_to_validate: bool


def classify_map_projection(
    sub_shape: FieldShape,
    map_path: FieldPath,
) -> MapProjectionVerdict:
    """Classify a map's projected key/value shape against the representable bound.

    The single source of truth for which map projections a `MapPath` can
    locate. The representable shape: a scalar terminal or `ModelRef`/`UnionRef`
    terminal, reached WITHOUT array iteration (`map_path` is not an
    `ArrayPath`), with no `ArrayOf` layer in the projected shape. Both
    `_map_projection_checks` (shape-level) and the path-level guards in
    `field_path.py` (`promote_terminal_map` rejecting an `ArrayPath`) enforce
    this boundary; this classifier states it once so the prohibitions agree by
    construction rather than by parallel maintenance.

    Two shapes fall outside the bound and have no `MapPath`:

    - a map reached through an array (`list[dict[K, V]]`, a `map_path` that is
      an `ArrayPath`), whose key/value can't anchor a struct-prefixed `MapPath`;
    - a key/value carrying an array layer (`dict[K, list[V]]`), whose scalar
      terminal sits under an `ArrayOf` that `terminal_scalar` would unwrap.
    """
    is_ref_terminal = isinstance(terminal_of(sub_shape), (ModelRef, UnionRef))
    has_value_to_validate = bool(all_constraints(sub_shape)) or is_ref_terminal
    if isinstance(map_path, ArrayPath):
        return MapProjectionVerdict(
            representable=False,
            reason="map reached through an array is not representable",
            has_value_to_validate=has_value_to_validate,
        )
    if has_array_layer(sub_shape):
        return MapProjectionVerdict(
            representable=False,
            reason="map value carrying a list layer (dict[K, list[V]]) is not representable",
            has_value_to_validate=has_value_to_validate,
        )
    if not is_ref_terminal and terminal_scalar(sub_shape) is None:
        return MapProjectionVerdict(
            representable=False,
            reason="constraint on a non-scalar terminal",
            has_value_to_validate=has_value_to_validate,
        )
    return MapProjectionVerdict(
        representable=True, reason=None, has_value_to_validate=has_value_to_validate
    )


def _map_projection_checks(
    sub_shape: FieldShape,
    map_path: FieldPath,
    projection: MapProjection,
) -> tuple[list[Check], _ShapeTerminal | None]:
    """Walk a map's key or value shape, emitting checks on a `MapPath` target.

    Supports two shapes reached without array iteration: a scalar terminal
    (`dict[K, scalar]` -- per-key/value constraints land on a bare `MapPath`)
    and a `ModelRef`/`UnionRef` terminal (`dict[K, Model]` -- the returned
    `_ShapeTerminal` lets the caller descend into the model's fields and
    constraints on a `MapPath` leaf, mirroring a `list[Model]` element).

    `classify_map_projection` is the arbiter of which shapes are
    representable. An unrepresentable shape carrying something to validate
    (`has_value_to_validate`) raises `NotImplementedError` to keep the dropped
    check loud; an unrepresentable shape with nothing to validate yields no
    checks. The constraint -- not the shape alone -- is what stays loud,
    matching the silent treatment of unconstrained maps.
    """
    verdict = classify_map_projection(sub_shape, map_path)
    if not verdict.representable:
        if verdict.has_value_to_validate:
            raise NotImplementedError(
                f"map {projection.value} on an unsupported shape "
                f"({verdict.reason}) is not supported ({sub_shape!r})"
            )
        return [], None
    primitive = terminal_primitive(sub_shape)
    sub_checks, terminal = _walk_field_shape(
        sub_shape,
        promote_terminal_map(map_path, projection),
        base_type=primitive.base_type if primitive is not None else None,
        required=False,
        required_gate=None,
        carried_element=[],
    )
    return sub_checks, terminal


def _ref_terminal_checks(
    ref: ModelRef | UnionRef,
    path: FieldPath,
    required: bool,
    required_gate: FieldPath | None,
) -> tuple[list[Check], _ShapeTerminal]:
    """Handle a `ModelRef`/`UnionRef` terminal: emit `check_required`, hand back the ref.

    A required model or union field always gets a standalone
    `check_required` Check; `required` holds only before any `ArrayOf`,
    so `path` is the field's plain struct path. The sub-fields are the
    caller's job, reached via the returned `_ShapeTerminal`.
    """
    checks: list[Check] = []
    if required:
        checks.append(
            Check(
                descriptors=(_required_descriptor(required_gate),),
                target=path,
            )
        )
    return checks, _ShapeTerminal(ref=ref, path=path)


def _build_field_checks(
    field_spec: FieldSpec,
    prefix: FieldPath = ScalarPath(),
    *,
    nullable_gate: FieldPath | None = None,
    arm: str | None = None,
) -> tuple[list[Check], list[ModelCheck]]:
    """Build Checks for a single field by walking its shape tree.

    `arm` is the singleton union-arm discriminator value the field belongs
    to (when it lives in exactly one arm), or `None` when the field is
    shared. It propagates to any model constraints discovered through this
    field's sub-models so per-arm test modules can filter them correctly.
    """
    # `prefix` is a ScalarPath/ArrayPath, or a MapPath when descending into
    # a `dict[K, Model]` value model -- all three define `append_struct`,
    # which extends the path's struct leaf with this field's name.
    path = prefix.append_struct(field_spec.name)
    checks, terminal = _walk_field_shape(
        field_spec.shape,
        path,
        base_type=(
            p.base_type
            if (p := terminal_primitive(field_spec.shape)) is not None
            else None
        ),
        required=field_spec.is_required,
        required_gate=nullable_gate,
        carried_element=[],
    )

    model_checks: list[ModelCheck] = []
    match terminal:
        case None:
            pass
        case _ShapeTerminal(ref=UnionRef(union=union_spec), path=terminal_path):
            sub_field_checks, sub_model_checks = _recurse_into_union(
                union_spec, terminal_path, arm=arm
            )
            checks.extend(sub_field_checks)
            model_checks.extend(sub_model_checks)
        case _ShapeTerminal(ref=ModelRef(model=model_spec), path=terminal_path):
            sub_field_checks, sub_model_checks = _recurse_into_model(
                model_spec,
                terminal_path,
                field_spec.is_optional,
                nullable_gate,
                arm=arm,
            )
            checks.extend(sub_field_checks)
            model_checks.extend(sub_model_checks)
        case _ShapeTerminal(ref=ref):
            raise AssertionError(
                f"unhandled _ShapeTerminal.ref variant: {type(ref).__name__}"
            )

    return checks, model_checks


def _recurse_into_model(
    model_spec: RecordSpec,
    prefix: FieldPath = ScalarPath(),
    is_optional: bool = False,
    nullable_gate: FieldPath | None = None,
    *,
    arm: str | None = None,
) -> tuple[list[Check], list[ModelCheck]]:
    """Walk a MODEL-kind field's children plus its model-level constraints.

    `prefix` is the terminal path the shape walker reached the `ModelRef`
    at, defaulting to the empty `ScalarPath()` at the row root. Its terminal
    segment is an `ArraySegment` (the field is a list) or a `MapSegment`
    (the field is a `dict[K, Model]` reached through its key/value
    projection) exactly when the model is reached through iteration, which
    resets the nullable gate (the iteration itself handles per-element
    nullability).

    `arm` propagates from the union arm whose variant-specific field led
    here, so model constraints declared on the sub-model are tagged with
    that arm rather than `None` (which would route them to every per-arm
    test).
    """
    last_seg = prefix.segments[-1] if prefix.segments else None
    field_is_iterated = isinstance(last_seg, (ArraySegment, MapSegment))
    if field_is_iterated:
        child_gate: FieldPath | None = None
    else:
        child_gate = prefix if is_optional else nullable_gate

    field_checks: list[Check] = []
    model_checks: list[ModelCheck] = []
    for sub_field in model_spec.fields:
        sub_field_checks, sub_model_checks = _build_field_checks(
            sub_field,
            prefix=prefix,
            nullable_gate=child_gate,
            arm=arm,
        )
        field_checks.extend(sub_field_checks)
        model_checks.extend(sub_model_checks)

    if model_spec.constraints:
        constraint_gate = (
            prefix
            if is_optional and not field_is_iterated and isinstance(prefix, ArrayPath)
            else None
        )
        sub_model_constraint_checks = _dispatch_model_constraints(
            model_spec.constraints,
            model_spec.fields,
            target=_model_constraint_target(prefix),
            arm=arm,
            gate=constraint_gate,
        )
        if sub_model_constraint_checks:
            _guard_struct_nested_anchor(prefix, model_spec.name)
        model_checks.extend(sub_model_constraint_checks)
    return field_checks, model_checks


def _is_struct_only_prefix(prefix: FieldPath) -> bool:
    """Non-root struct path with no array traversal.

    True when `prefix` has one or more struct segments but no array
    iteration -- meaning discriminator column access and model-constraint
    targeting cannot use the prefix without resolving it into a
    struct-qualified path, which the current renderer does not support.
    """
    return not isinstance(prefix, ArrayPath) and bool(prefix.segments)


def _reject_struct_only_prefix(prefix: FieldPath, message: str) -> None:
    """Raise `NotImplementedError(message)` when `prefix` is struct-only.

    Shared mechanism for the struct-nested guards: the renderer supports
    neither model-constraint anchoring nor column-level discriminator
    gating at a struct-only prefix, so reaching one with a real check is a
    renderer gap rather than a normal case.
    """
    if _is_struct_only_prefix(prefix):
        raise NotImplementedError(message)


def _guard_struct_nested_anchor(prefix: FieldPath, name: str) -> None:
    """Raise when emitting a model constraint at a struct-only prefix.

    See `_model_constraint_target`: in that case the constraint's target
    collapses to the row root, which is wrong for any non-skipped
    constraint. Today only `NoExtraFieldsConstraint` reaches here (and
    dispatches to None); a real descriptor at this depth is a renderer
    gap, not a normal case. A `MapPath` is exempt -- it is a valid anchor
    (`_model_constraint_target` keeps it, and the renderer wraps the check
    in `map_values_check`/`map_keys_check`).
    """
    if isinstance(prefix, MapPath):
        return
    _reject_struct_only_prefix(
        prefix,
        f"Model constraint on struct-nested {name!r} "
        f"(reached at {prefix!r}) -- the renderer has no anchor "
        "for nested-struct model constraints.",
    )


def _guard_struct_nested_variant_fields(prefix: FieldPath, name: str) -> None:
    """Raise when emitting variant-gated field checks at a struct-only prefix.

    A `ColumnGuard` carries a bare discriminator name that renders as
    `F.col("<discriminator>")` -- a top-level column access. When the
    union is reached through a plain struct field, the discriminator lives
    at `<prefix>.<discriminator>`, so the rendered gate reads the wrong
    column. Raising loudly is safer than emitting a mis-gated check; no
    current schema nests a discriminated union under a plain struct.
    """
    _reject_struct_only_prefix(
        prefix,
        f"Discriminated union {name!r} with variant-gated field checks "
        f"at struct-nested prefix {prefix!r} -- `ColumnGuard` would "
        "render the discriminator as a top-level column, not a "
        "struct-qualified path.",
    )


def _recurse_into_union(
    union_spec: UnionSpec,
    prefix: FieldPath = ScalarPath(),
    *,
    arm: str | None = None,
) -> tuple[list[Check], list[ModelCheck]]:
    """Walk a UNION-kind field's variants, gathering Checks and ModelChecks.

    `prefix` is the terminal path the shape walker reached the `UnionRef`
    at; the union's variant fields live directly under it. An `ArrayPath`
    prefix means the union is reached through array iteration, so variant
    gates are element-level and model constraints target that path.

    `arm` is the outer union arm whose variant-specific field reached this
    inner union. It tags any model constraints discovered here so they
    aren't propagated to other arms' test modules.
    """
    mapping = union_spec.discriminator_mapping or {}
    value_by_class = {cls: value for value, cls in mapping.items()}
    union_target = _model_constraint_target(prefix)

    field_checks, field_model_checks = _field_checks_for_union(
        union_spec, value_by_class, prefix=prefix, arm=arm
    )
    union_level_checks = _model_checks_for_union(
        union_spec, value_by_class, union_target, arm=arm
    )
    exclusivity_checks = _exclusivity_checks_for_union(
        union_spec, value_by_class, union_target, arm=arm
    )
    if union_level_checks or exclusivity_checks:
        _guard_struct_nested_anchor(prefix, union_spec.name)
    return field_checks, union_level_checks + field_model_checks + exclusivity_checks


def _model_constraint_target(prefix: FieldPath) -> FieldPath:
    """Where a model constraint's check should be anchored.

    Three supported cases:

    - `ArrayPath` -- constraints on a sub-model reached through array
      iteration target the array path (so the renderer wraps the check
      in `array_check`).
    - `MapPath` -- constraints on a `dict[K, Model]` value model target the
      map path (so the renderer wraps the check in `map_values_check`),
      mirroring the array case.
    - Empty or struct-only `ScalarPath` -- constraints anchor at the row
      root. Pure struct nesting (e.g. `Names` reached at
      `ScalarPath('names')`) collapses here because the renderer has no
      anchor for nested-struct model constraints. The only constraint kind
      currently reachable through pure struct nesting is
      `NoExtraFieldsConstraint`, which `dispatch_model_constraint`
      discards before the target is consulted, so the collapse is
      observationally inert today; a non-skipped constraint at this depth
      would surface as a wrong-anchor bug.
    """
    return prefix if isinstance(prefix, (ArrayPath, MapPath)) else ScalarPath()


def _dispatch_model_constraints(
    constraints: tuple[ModelConstraint, ...],
    fields: list[FieldSpec],
    *,
    target: FieldPath = ScalarPath(),
    arm: str | None = None,
    gate: FieldPath | None = None,
) -> list[ModelCheck]:
    """Dispatch model constraints to ModelChecks."""
    return [
        ModelCheck(descriptor=desc, target=target, arm=arm, gate=gate)
        for mc in constraints
        for desc in dispatch_model_constraint(mc, fields)
    ]


def _singleton_arm(values: tuple[str, ...]) -> str | None:
    """Return the sole arm in `values`, or None when there isn't exactly one.

    No real schema today has a variant-specific field belonging to a
    proper subset of arms (2-of-N): every variant-specific field is
    declared on exactly one arm. If a future schema introduces a 2-of-N
    field whose sub-model declares model constraints, this collapse
    would broadcast those constraints to every arm (including the ones
    the field doesn't belong to). `TestMultiArmVariantSourcesPolicy`
    pins the current behaviour as a tombstone.
    """
    return values[0] if len(values) == 1 else None


def _field_checks_for_union(
    spec: UnionSpec,
    value_by_class: dict[type[BaseModel], str],
    prefix: FieldPath = ScalarPath(),
    *,
    arm: str | None = None,
) -> tuple[list[Check], list[ModelCheck]]:
    """Build field checks for a union spec's annotated fields.

    `arm` is the outer-union arm threaded through from an enclosing
    `_recurse_into_union`. When present, every sub-model constraint
    reached from here inherits that arm -- the inner union's own
    discriminator is irrelevant to per-arm test filtering, which always
    keys on the outermost union's discriminator.
    """
    guard_cls: type[Guard] = (
        ElementGuard if isinstance(prefix, ArrayPath) else ColumnGuard
    )
    field_checks: list[Check] = []
    model_checks: list[ModelCheck] = []
    discriminator = spec.discriminator_field
    for af in spec.annotated_fields:
        values: tuple[str, ...] = ()
        if af.variant_sources is not None and discriminator is not None:
            values = tuple(
                value_by_class[src]
                for src in af.variant_sources
                if src in value_by_class
            )
        # Outer arm dominates: when this is a nested union, every sub-model
        # constraint discovered here belongs to the outer arm. Only the
        # outermost union picks a `field_arm` from its own variant sources,
        # and only when the field is variant-specific to a single arm.
        field_arm = arm if arm is not None else _singleton_arm(values)
        checks, sub_model_checks = _build_field_checks(
            af.field_spec, prefix=prefix, arm=field_arm
        )
        model_checks.extend(sub_model_checks)
        if values and discriminator is not None:
            _guard_struct_nested_variant_fields(prefix, spec.name)
            # Outer guards land first so the renderer composes
            # outer-then-inner (e.g. a `ColumnGuard` from a parent union,
            # then an `ElementGuard` from the nested union the field
            # lives in).
            guard: Guard = guard_cls(discriminator=discriminator, values=values)
            checks = [replace(ck, guards=(guard, *ck.guards)) for ck in checks]
        field_checks.extend(checks)
    return field_checks, model_checks


def _model_checks_for_union(
    spec: UnionSpec,
    arm_by_class: dict[type[BaseModel], str],
    target: FieldPath = ScalarPath(),
    *,
    arm: str | None = None,
) -> list[ModelCheck]:
    """Build ModelChecks for the union itself plus each member's own constraints.

    When `arm` is None (top-level union): union-level constraints carry
    `arm=None` because they apply regardless of which arm matches.
    Member-class constraints (e.g. `@radio_group` on `RoadSegment`) are
    tagged with the discriminator value mapped to that class so the test
    renderer can confine them to the right per-arm test module.

    When `arm` is set (nested union reached from an outer arm): every
    check produced -- union-level and member-level -- inherits that outer
    arm. The inner union's own discriminator is irrelevant to per-arm
    test filtering, which always keys on the outermost union's
    discriminator.
    """
    model_checks = _dispatch_model_constraints(
        spec.constraints,
        spec.fields,
        target=target,
        arm=arm,
    )
    for member in spec.member_specs:
        member_constraints = ModelConstraint.get_model_constraints(member.member_cls)
        member_arm = arm if arm is not None else arm_by_class.get(member.member_cls)
        model_checks.extend(
            _dispatch_model_constraints(
                member_constraints,
                member.spec.fields,
                target=target,
                arm=member_arm,
            )
        )
    return model_checks


def _exclusivity_checks_for_union(
    spec: UnionSpec,
    value_by_class: dict[type[BaseModel], str],
    target: FieldPath = ScalarPath(),
    *,
    arm: str | None = None,
) -> list[ModelCheck]:
    """Generate forbid_if/require_if checks from union variant structure.

    Unlike `dispatch_model_constraint` (which maps user-declared
    `ModelConstraint` objects to descriptors), this synthesizes
    `ForbidIf`/`RequireIf` descriptors directly from the union's variant
    grouping. The input is a structural property of the union, not a
    declared constraint, so there is no source `ModelConstraint` to
    dispatch from.

    `arm` is the outer-union arm threaded through when this union is
    nested inside another. Inner exclusivity checks belong to that outer
    arm rather than being broadcast to every arm.
    """
    if spec.discriminator_mapping is None or spec.discriminator_field is None:
        return []

    all_values = set(spec.discriminator_mapping)

    grouped: dict[str, set[type[BaseModel]]] = defaultdict(set)
    required_by_field: dict[str, set[type[BaseModel]]] = defaultdict(set)
    shape_by_field: dict[str, FieldShape] = {}
    for af in spec.annotated_fields:
        if af.variant_sources is None:
            continue
        name = af.field_spec.name
        shape_by_field[name] = af.field_spec.shape
        for src in af.variant_sources:
            if src in value_by_class:
                grouped[name].add(src)
                if af.field_spec.is_required:
                    required_by_field[name].add(src)

    def forbid_check(field_name: str, condition: FieldEqCondition | Not) -> ModelCheck:
        return ModelCheck(
            descriptor=ForbidIf(
                field_names=(field_name,),
                condition=condition,
                field_shapes=forbid_if_field_shapes((field_name,), shape_by_field),
            ),
            target=target,
            arm=arm,
        )

    def require_check(field_name: str, condition: FieldEqCondition | Not) -> ModelCheck:
        return ModelCheck(
            descriptor=RequireIf(field_names=(field_name,), condition=condition),
            target=target,
            arm=arm,
        )

    checks: list[ModelCheck] = []
    disc_field = spec.discriminator_field
    for field_name, variant_classes in grouped.items():
        variant_values = {value_by_class[cls] for cls in variant_classes}
        excluded_values = all_values - variant_values
        if not excluded_values:
            continue

        if len(variant_values) == 1 and len(excluded_values) > 1:
            (sole_value,) = variant_values
            checks.append(
                forbid_check(field_name, Not(FieldEqCondition(disc_field, sole_value)))
            )
        else:
            for exc_val in sorted(excluded_values):
                checks.append(
                    forbid_check(field_name, FieldEqCondition(disc_field, exc_val))
                )

        required_classes = required_by_field[field_name]
        required_values = {value_by_class[cls] for cls in required_classes}
        for req_val in sorted(required_values):
            checks.append(
                require_check(field_name, FieldEqCondition(disc_field, req_val))
            )

    return checks


def build_checks(
    spec: ModelSpec,
) -> tuple[list[Check], list[ModelCheck]]:
    """Build all check IR for a feature spec.

    Roots the walk at the empty `ScalarPath()` and delegates to the same
    helpers used at every nested level (`_recurse_into_union` for unions,
    `_recurse_into_model` for models), so the row-root and nested cases
    share one path.
    """
    if isinstance(spec, UnionSpec):
        return _recurse_into_union(spec)
    return _recurse_into_model(spec)
