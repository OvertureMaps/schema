"""Walk FieldSpec trees to produce Check/ModelCheck IR for rendering.

Consults the constraint dispatch table to map each constraint to a
descriptor, then applies composition rules the dispatch table can't see:

- Coalesce ordering: gather descriptors for the same field into one
  `Check` (required first, then enum, then dispatched constraints),
  deduplicate, and split column-level checks into separate suffixed checks.
- Target resolution: a shape walker descends each field's `FieldShape`
  tree, building the `Direct` or `Iterated` target by appending
  segments as it goes -- so the path read in the code is the path that
  lands in the IR. Entering a `list[...]` or `dict[K, V]` layer promotes
  the path's terminal segment to an iterated `ArraySegment` / `MapSegment`.
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
    ArraySegment,
    Direct,
    FieldPath,
    Iterated,
    MapProjection,
    MapSegment,
    promote_terminal,
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
    enum_source,
    terminal_primitive,
)
from ..extraction.literal_alternatives import LiteralAlternatives
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


def _literal_alternatives(shape: Scalar | MapOf) -> tuple[object, ...]:
    """Return the allowed literal values from a `LiteralAlternatives` constraint, or `()`.

    `MapOf` returns `()`: a map column carries no literal alternative of its
    own (its key/value projections reach their own `Scalar` shapes, which are
    handled there).
    """
    if isinstance(shape, MapOf):
        return ()
    for cs in shape.constraints:
        if isinstance(cs.constraint, LiteralAlternatives):
            return cs.constraint.values
    return ()


def _apply_literal_bypass(
    descriptors: list[ExpressionDescriptor],
    allow_literals: tuple[object, ...],
) -> list[ExpressionDescriptor]:
    """Stamp `allow_literals` onto each content descriptor.

    Content descriptors are the non-required checks: enum, pattern,
    bounds, base-type checks. `check_required` is excluded by callers
    who pass only the content portion of the descriptor list.
    """
    if not allow_literals:
        return descriptors
    return [replace(desc, allow_literals=allow_literals) for desc in descriptors]


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
                promote_terminal(path),
                base_type=base_type,
                required=False,
                required_gate=required_gate,
                carried_element=[*carried_element, *element_descriptors],
            )
            return [*checks, *sub_checks], terminal

        case UnionRef() | ModelRef():
            # A union or model reached under any array/map nesting (including
            # `list[list[Union]]`) descends the same way: the fold wraps each
            # variant-gated field check at the innermost element, where the
            # `ElementGuard`'s discriminator co-locates with the leaf accessor.
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
            # their per-key/per-value constraints land on `Iterated` targets.
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
                # Not a representational limit: the taxonomy encodes
                # `a{key}.kfield` and `a{value}.vfield` independently. The
                # barrier is that `_walk_field_shape` returns a single
                # `_ShapeTerminal`, so the FieldSpec recursion can descend only
                # one projection's sub-model -- a `dict[Model, Model]` needs
                # both descended. Lifting it means returning two terminals.
                raise NotImplementedError(
                    "dict[Model, Model] reaches a sub-model through both its "
                    "key and value projection, but _walk_field_shape returns a "
                    "single terminal, so only one projection's sub-model can be "
                    "descended"
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
    element_descriptors = _apply_literal_bypass(
        element_descriptors, _literal_alternatives(shape)
    )

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


def _map_projection_checks(
    sub_shape: FieldShape,
    map_path: FieldPath,
    projection: MapProjection,
) -> tuple[list[Check], _ShapeTerminal | None]:
    """Walk a map's key or value shape, emitting checks on an `Iterated` target.

    Promotes *map_path*'s terminal into a `MapSegment` projecting the chosen
    side, then walks the projected shape unconditionally. Every map/array
    nesting -- `dict[K, scalar]` (per-key/value constraints on a bare map
    frame), `dict[K, Model]` (the returned `_ShapeTerminal` lets the caller
    descend the value model on a map leaf), `dict[K, list]`, `dict[K, dict]`,
    and a map reached through an array -- is now representable, so the walk
    needs no representability gate: an unconstrained shape simply yields no
    checks.
    """
    primitive = terminal_primitive(sub_shape)
    return _walk_field_shape(
        sub_shape,
        promote_terminal(map_path, projection=projection),
        base_type=primitive.base_type if primitive is not None else None,
        required=False,
        required_gate=None,
        carried_element=[],
    )


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
    prefix: FieldPath = Direct(),
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
    # `prefix` is a `Direct` or an `Iterated` (the latter when descending
    # into a list element or a `dict[K, Model]` value model) -- both define
    # `append_struct`, which extends the path's struct leaf with this field's
    # name.
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
    prefix: FieldPath = Direct(),
    is_optional: bool = False,
    nullable_gate: FieldPath | None = None,
    *,
    arm: str | None = None,
) -> tuple[list[Check], list[ModelCheck]]:
    """Walk a MODEL-kind field's children plus its model-level constraints.

    `prefix` is the terminal path the shape walker reached the `ModelRef`
    at, defaulting to the empty `Direct()` at the row root. Its terminal
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
        # The constraint applies wherever the model is reached, so it inherits
        # the same nullable gate as the model's fields: `child_gate` is the
        # optional-ancestor path (or the model's own optional prefix) that must
        # be non-null for the constraint to apply, and `None` once inside any
        # iterated container (the fold handles per-element nullability). The
        # renderer wraps a Direct-target constraint in `F.when(gate.isNotNull())`
        # and an Iterated-target one element-relatively.
        sub_model_constraint_checks = _dispatch_model_constraints(
            model_spec.constraints,
            model_spec.fields,
            target=_model_constraint_target(prefix),
            arm=arm,
            gate=child_gate,
        )
        model_checks.extend(sub_model_constraint_checks)
    return field_checks, model_checks


def _is_struct_only_prefix(prefix: FieldPath) -> bool:
    """Non-root struct path with no iteration.

    True when `prefix` has one or more struct segments but no array/map
    iteration -- meaning discriminator column access and model-constraint
    targeting cannot use the prefix without resolving it into a
    struct-qualified path, which the current renderer does not support. A
    `Direct` with segments is the only struct-only prefix; any `Iterated`
    (array- or map-reached) is a valid anchor.
    """
    return isinstance(prefix, Direct) and bool(prefix.segments)


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
    """Raise when a struct-nested UNION emits union-level or exclusivity checks.

    A plain model constraint at a struct-only prefix is supported: the target
    is the struct prefix and the renderer qualifies field references
    (`F.col("details.foo")`, see `_model_constraint_target`). A discriminated
    UNION reached through a plain struct is not: its synthesized exclusivity
    checks and union-level constraints interlock with the variant-field
    `ColumnGuard`s (`_guard_struct_nested_variant_fields`), which render the
    discriminator as a top-level column rather than a struct-qualified path.
    Gating the whole union case loudly keeps that mis-columning from shipping.
    A map-reached `Iterated` prefix is a valid anchor, so `_is_struct_only_prefix`
    -- `False` for any `Iterated` -- exempts it automatically.
    """
    _reject_struct_only_prefix(
        prefix,
        f"Model constraint on struct-nested union {name!r} "
        f"(reached at {prefix!r}) -- the discriminator gating renders "
        "as a top-level column, not a struct-qualified path.",
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


def _iteration_depth(path: FieldPath) -> int:
    """Number of iteration frames (`Array`/`Map` segments) in *path*.

    Each iterating segment -- named or anonymous -- is one lambda frame in
    the renderer's fold, so the count is the depth at which the innermost
    element variable is bound. A `Direct` path binds no element variable
    and has depth 0.
    """
    if isinstance(path, Iterated):
        return sum(
            1 for s in path.segments if isinstance(s, (ArraySegment, MapSegment))
        )
    return 0


def _guard_variant_field_past_element(
    prefix: FieldPath, checks: list[Check], name: str
) -> None:
    """Raise when an `ElementGuard`'d variant field iterates past its discriminator.

    An `ElementGuard` carries the discriminator of a union reached at
    *prefix*, and the renderer applies it at the innermost iteration
    variable (`_render_iterated_check_expr`). That placement is correct only
    when the guarded check binds the same element as the discriminator --
    i.e. the check iterates no further than *prefix*. When a variant field is
    itself an iterated container (e.g. `list[list[Union{codes: list[int]}]]`,
    where `codes[]` adds a third iteration past the union element), the
    innermost variable is that deeper element, where the discriminator does
    not live. The renderer has no per-guard depth info to place the guard at
    the discriminator's shallower iteration level, so the render would
    silently gate on the wrong element. Raise instead.
    """
    prefix_depth = _iteration_depth(prefix)
    for ck in checks:
        if _iteration_depth(ck.target) > prefix_depth:
            raise NotImplementedError(
                f"Discriminated union {name!r}: variant field check reaches "
                f"its value through iteration beyond the discriminator's "
                f"element (discriminator element at {prefix!r}, check target "
                f"{ck.target!r}). The ElementGuard is applied at the innermost "
                f"iteration variable, so it cannot be placed at the "
                f"discriminator's iteration level when the variant field "
                f"iterates further."
            )


def _recurse_into_union(
    union_spec: UnionSpec,
    prefix: FieldPath = Direct(),
    *,
    arm: str | None = None,
) -> tuple[list[Check], list[ModelCheck]]:
    """Walk a UNION-kind field's variants, gathering Checks and ModelChecks.

    `prefix` is the terminal path the shape walker reached the `UnionRef`
    at; the union's variant fields live directly under it. An `Iterated`
    prefix means the union is reached through array or map iteration, so
    variant gates are element-level and model constraints target that path.

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
    """Where a model constraint's check should be anchored -- the prefix itself.

    The check anchors exactly where the shape walker reached the constrained
    model, so this is the identity on `prefix`:

    - `Iterated` -- a sub-model reached through array or map iteration; the
      renderer wraps the check in the iteration fold (`array_check` for an
      array-reached model, `map_values_check` for a `dict[K, Model]` value
      model), and field references become element-relative accessors.
    - Struct-only `Direct` (e.g. `Details` reached at `Direct('details')`) --
      a sub-model reached through a plain struct field; the renderer qualifies
      every field reference with the struct prefix (`F.col("details.foo")`).
    - Empty `Direct` -- a row-root constraint; field references are top-level
      columns.
    """
    return prefix


def _dispatch_model_constraints(
    constraints: tuple[ModelConstraint, ...],
    fields: list[FieldSpec],
    *,
    target: FieldPath = Direct(),
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
    prefix: FieldPath = Direct(),
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
    # A union reached through any iterated container (array or map element)
    # is element-gated; only a row-/struct-level union uses a column gate.
    guard_cls: type[Guard] = (
        ElementGuard if isinstance(prefix, Iterated) else ColumnGuard
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
            if isinstance(guard, ElementGuard):
                _guard_variant_field_past_element(prefix, checks, spec.name)
            checks = [replace(ck, guards=(guard, *ck.guards)) for ck in checks]
        field_checks.extend(checks)
    return field_checks, model_checks


def _model_checks_for_union(
    spec: UnionSpec,
    arm_by_class: dict[type[BaseModel], str],
    target: FieldPath = Direct(),
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
    target: FieldPath = Direct(),
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

    Roots the walk at the empty `Direct()` and delegates to the same
    helpers used at every nested level (`_recurse_into_union` for unions,
    `_recurse_into_model` for models), so the row-root and nested cases
    share one path.
    """
    if isinstance(spec, UnionSpec):
        return _recurse_into_union(spec)
    return _recurse_into_model(spec)
