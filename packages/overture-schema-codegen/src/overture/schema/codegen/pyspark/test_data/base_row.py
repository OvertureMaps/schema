"""Generate valid base rows for the rendered conformance tests.

`generate_base_row` produces a minimal valid row (required fields only)
from a `ModelSpec`. `generate_populated_row` produces a fully
populated row including optional fields. `generate_arm_rows` and
`generate_populated_arm_rows` do the same for each arm of a discriminated
union.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from enum import Enum
from typing import Any

from overture.schema.common.scoping.lr import LinearReferenceRangeConstraint
from overture.schema.system.geometric.geom import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.model_constraint import (
    ForbidIfConstraint,
    MinFieldsSetConstraint,
    RadioGroupConstraint,
    RequireAnyOfConstraint,
    RequireAnyTrueConstraint,
    RequireIfConstraint,
)

from ...extraction.field import (
    AnyScalar,
    ArrayOf,
    ConstraintSource,
    FieldShape,
    LiteralScalar,
    MapOf,
    ModelRef,
    NewTypeShape,
    Primitive,
    UnionRef,
)
from ...extraction.field_walk import (
    enum_source,
    has_array_layer,
    terminal_primitive,
    terminal_scalar,
)
from ...extraction.length_constraints import ArrayMinLen
from ...extraction.specs import FieldSpec, ModelSpec, RecordSpec, UnionSpec
from ...extraction.type_registry import primitive_spark_category
from .._primitive_fill import PRIMITIVE_FILL_TABLE
from ..constraint_dispatch import (
    ExpressionDescriptor,
    FieldEq,
    dispatch_constraint,
    require_bool_field_eq,
    require_field_eq,
)
from .constraint_values import (
    CONSTRAINT_VALUES,
    curated_pattern_values,
    uncurated_pattern_error,
    valid_bound,
)

__all__ = [
    "condition_overrides_for_present_field",
    "generate_arm_rows",
    "generate_base_row",
    "generate_populated_arm_rows",
    "generate_populated_row",
    "resolve_arm_spec",
    "value_for_field",
]

_BASE_ROW_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_DNS, "overturemaps.org/codegen/base_row"
)


# WKT strings for each allowed geometry type (valid side)
_VALID_GEOMETRY_WKT: dict[GeometryType, str] = {
    GeometryType.POINT: "POINT (0 0)",
    GeometryType.LINE_STRING: "LINESTRING (0 0, 1 1)",
    GeometryType.POLYGON: "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
    GeometryType.MULTI_POLYGON: "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 1, 0 0)))",
    GeometryType.MULTI_LINE_STRING: "MULTILINESTRING ((0 0, 1 1))",
}


_PRIMITIVE_DEFAULTS: dict[str, object] = {
    "str": "",
    "NoWhitespaceString": "",
    "HttpUrl": "https://example.com/",
    "EmailStr": "user@example.com",
    "bool": False,
    "bytes": b"",
    "datetime": "2024-01-01T00:00:00Z",
    "date": "2024-01-01",
}


def _bbox_value() -> dict[str, float]:
    return {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}


# Field-name overrides applied before any shape-based value generation in
# `value_for_field`. Each builder receives `(field_spec, spec_name)`.
_SPECIAL_FIELD_VALUES: dict[str, Callable[[FieldSpec, str], object]] = {
    "id": lambda _f, spec_name: str(uuid.uuid5(_BASE_ROW_NAMESPACE, spec_name)),
    "bbox": lambda _f, _spec_name: _bbox_value(),
}


def _is_geometry_terminal(terminal: Primitive) -> bool:
    """Whether this terminal represents a geometry value.

    Only fires for the `Geometry` source class. Fields wanting a
    geometry value must declare `Geometry`; ad-hoc forms like
    `Annotated[bytes, GeometryTypeConstraint(...)]` aren't recognized.
    """
    return terminal.source_type is Geometry


def generate_base_row(spec: ModelSpec, *, index: int = 0) -> dict[str, Any]:
    """Produce a minimal valid row from a feature spec (required fields only).

    The row passes `TypeAdapter(validation_type).validate_python()`.

    Parameters
    ----------
    spec
        An expanded feature spec.
    index
        Position within a parent list. Non-zero values suffix string fields
        to ensure uniqueness across list items.
    """
    return _build_row(spec, index=index, populate_optional=False)


def generate_populated_row(spec: ModelSpec, *, index: int = 0) -> dict[str, Any]:
    """Produce a fully populated valid row (all fields, including optional).

    Sub-models are recursively populated.

    Parameters
    ----------
    spec
        An expanded feature spec.
    index
        Position within a parent list. Non-zero values suffix string fields
        to ensure uniqueness across list items.
    """
    return _build_row(spec, index=index, populate_optional=True)


def generate_arm_rows(spec: ModelSpec) -> dict[str, dict[str, Any]]:
    """Produce one minimal valid row per discriminator arm of a union.

    Returns `{arm_value: row}` where each row passes TypeAdapter
    validation against the union's source annotation.

    Parameters
    ----------
    spec
        An expanded union spec.
    """
    return _build_arm_rows(_require_union(spec), populate_optional=False)


def generate_populated_arm_rows(
    spec: ModelSpec,
) -> dict[str, dict[str, Any]]:
    """Produce one fully populated valid row per discriminator arm.

    Returns `{arm_value: row}` where each row passes TypeAdapter
    validation and includes all optional fields with valid values.

    Parameters
    ----------
    spec
        An expanded union spec.
    """
    return _build_arm_rows(_require_union(spec), populate_optional=True)


def _require_union(spec: ModelSpec) -> UnionSpec:
    if not isinstance(spec, UnionSpec):
        raise TypeError(
            f"Expected a UnionSpec, got {type(spec).__name__}: {spec.name!r}"
        )
    return spec


def _build_row(
    spec: ModelSpec,
    *,
    index: int = 0,
    populate_optional: bool,
    name_override: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {}
    name = name_override or spec.name
    for field in spec.fields:
        if not populate_optional and not field.is_required:
            continue
        row[field.name] = value_for_field(
            field, name, index=index, populate_optional=populate_optional
        )
    _satisfy_model_constraints(row, spec)
    return row


def _build_arm_rows(
    spec: UnionSpec,
    *,
    populate_optional: bool,
) -> dict[str, dict[str, Any]]:
    if spec.discriminator_field is None or spec.discriminator_mapping is None:
        raise ValueError(f"UnionSpec {spec.name!r} has no discriminator")
    if spec.constraints:
        # Per-arm rows are built from member specs only; union-level
        # constraints (e.g. radio_group on the union itself) would need
        # `_satisfy_model_constraints` applied with the union's field
        # list. No schema exercises this today; raise so a future union
        # that adds one fails loudly rather than producing invalid rows.
        raise NotImplementedError(
            f"UnionSpec {spec.name!r} has {len(spec.constraints)} model "
            "constraint(s); per-arm row generation does not enforce them"
        )
    spec_by_class = {ms.member_cls: ms.spec for ms in spec.member_specs}
    result: dict[str, dict[str, Any]] = {}
    for arm_val, member_cls in spec.discriminator_mapping.items():
        row = _build_row(
            spec_by_class[member_cls],
            populate_optional=populate_optional,
            name_override=spec.name,
        )
        row[spec.discriminator_field] = arm_val
        result[arm_val] = row
    return result


def _condition_value(field_eq: FieldEq) -> object:
    """Return the condition's comparison value, with an `Enum` unwrapped to its value.

    Row dicts store raw scalar values, so an `Enum`-typed condition value is
    compared and written as its underlying `.value`.
    """
    value = field_eq.value
    return value.value if isinstance(value, Enum) else value


def _row_satisfies_condition(row: dict[str, Any], condition: object) -> bool:
    """Check whether the condition is satisfied by the row's current values.

    Handles `FieldEqCondition` and `Not(FieldEqCondition)`. Raises
    `TypeError` for any other condition kind so new condition types fail
    loudly rather than silently returning an incorrect result.

    Parameters
    ----------
    row
        Current row dict being built.
    condition
        A `Condition` from a `RequireIfConstraint` or `ForbidIfConstraint`.
    """
    field_eq = require_field_eq(condition)  # type: ignore[arg-type]
    matches = row.get(field_eq.field_name) == _condition_value(field_eq)
    return matches != field_eq.negated


def _satisfy_model_constraints(row: dict[str, Any], spec: ModelSpec) -> None:
    """Adjust *row* so each model constraint is satisfied.

    `require_if`/`radio_group`/`require_any_of`/`min_fields_set` fill in
    optional fields the constraint makes mandatory. `forbid_if` removes
    fields the constraint excludes. Constraints whose guard predicate is
    false (e.g. a `RequireIf` whose condition does not hold for the
    current row) need no adjustment and pass through; any constraint type
    not matched by an arm here is silently skipped, intentionally -- new
    constraint kinds surface via `dispatch_model_constraint` (which
    raises) rather than here.
    """
    fields_by_name = {f.name: f for f in spec.fields}
    for constraint in spec.constraints:
        match constraint:
            case RequireIfConstraint() if _row_satisfies_condition(
                row, constraint.condition
            ):
                for field_name in constraint.field_names:
                    if field_name in row:
                        continue
                    field_spec = fields_by_name.get(field_name)
                    if field_spec is not None:
                        row[field_name] = value_for_field(field_spec, spec.name)
            case RadioGroupConstraint() if not any(
                row.get(fn) is True for fn in constraint.field_names
            ):
                for field_name in constraint.field_names:
                    if field_name in fields_by_name:
                        row[field_name] = True
                        break
            case RequireAnyTrueConstraint() if not any(
                _row_satisfies_condition(row, c) for c in constraint.conditions
            ):
                # Make the first condition hold by writing the boolean it tests
                # for. `require_bool_field_eq` validates the positive-boolean
                # invariant here too -- this path runs on the raw constraint and
                # does not pass through `dispatch_model_constraint`.
                field_eq = require_bool_field_eq(constraint.conditions[0])  # type: ignore[arg-type]
                row[field_eq.field_name] = field_eq.value
            case RequireAnyOfConstraint() if not any(
                fn in row for fn in constraint.field_names
            ):
                for field_name in constraint.field_names:
                    field_spec = fields_by_name.get(field_name)
                    if field_spec is not None:
                        row[field_name] = value_for_field(field_spec, spec.name)
                        break
            case ForbidIfConstraint() if _row_satisfies_condition(
                row, constraint.condition
            ):
                for field_name in constraint.field_names:
                    row.pop(field_name, None)
            case MinFieldsSetConstraint(count=count):
                # Mirror Pydantic's `model_fields_set` semantics: every
                # required field is "set" by the constructor, and counts
                # alongside any non-null optional field. Required fields
                # are always populated by the time we reach this branch,
                # so satisfying `count` may need extra optional fills.
                missing = count - sum(1 for f in spec.fields if f.name in row)
                for opt_field in (f for f in spec.fields if not f.is_required):
                    if missing <= 0:
                        break
                    if opt_field.name in row:
                        continue
                    row[opt_field.name] = value_for_field(opt_field, spec.name)
                    missing -= 1


def _condition_disabling_value(field_eq: FieldEq, field_spec: FieldSpec) -> object:
    """Return a value for a condition field that makes the condition false.

    `FieldEqCondition(f, X)` holds when `f == X`, so a different enum member
    disables it; a negated condition (`Not(...)`, true when `f != X`) is
    disabled by `X` itself. Every condition in the schema gates on an enum
    field, so a non-enum condition field raises rather than guess a value.

    Parameters
    ----------
    field_eq
        The unwrapped field-equality condition.
    field_spec
        Spec of the condition field, used to enumerate alternative values.
    """
    forbidden = _condition_value(field_eq)
    if field_eq.negated:
        return forbidden
    terminal = terminal_primitive(field_spec.shape)
    enum_cls = enum_source(terminal) if terminal is not None else None
    if enum_cls is None:
        raise TypeError(
            f"condition field {field_eq.field_name!r} is not enum-backed; "
            "cannot derive a value that disables its forbid_if condition"
        )
    for member in enum_cls:
        if member.value != forbidden:
            return member.value
    raise ValueError(
        f"enum {enum_cls.__name__} has no member other than {forbidden!r}; "
        "cannot disable its forbid_if condition"
    )


def condition_overrides_for_present_field(
    spec: ModelSpec, field_name: str
) -> dict[str, Any]:
    """Return overrides that let `field_name` be present on a valid base row.

    A `forbid_if` whose condition the base row satisfies forbids `field_name`,
    so a scaffold that sets the field yields a row Pydantic rejects. Flip each
    such condition field to a value the forbid rejects -- which also satisfies
    the symmetric `require_if` that then mandates the field -- and re-satisfy
    the model constraints, since a flipped condition can newly require other
    fields. Returns only the fields whose value differs from the base row;
    `field_name` itself is set by the scaffold and is excluded.

    Returns `{}` when no `forbid_if` gates `field_name`, the common case.

    Parameters
    ----------
    spec
        The model whose constraints govern `field_name`.
    field_name
        A direct field of `spec` the scaffold needs to set.
    """
    forbidding = [
        c
        for c in spec.constraints
        if isinstance(c, ForbidIfConstraint) and field_name in c.field_names
    ]
    if not forbidding:
        return {}
    base = generate_base_row(spec)
    fields_by_name = {f.name: f for f in spec.fields}
    flips: dict[str, Any] = {}
    for constraint in forbidding:
        if not _row_satisfies_condition(base, constraint.condition):
            continue
        field_eq = require_field_eq(constraint.condition)
        cond_field = fields_by_name.get(field_eq.field_name)
        if cond_field is not None:
            flips[field_eq.field_name] = _condition_disabling_value(
                field_eq, cond_field
            )
    if not flips:
        return {}
    merged = {**base, **flips}
    _satisfy_model_constraints(merged, spec)
    return {
        name: value
        for name, value in merged.items()
        if name != field_name and base.get(name) != value
    }


def value_for_field(
    field: FieldSpec,
    spec_name: str,
    *,
    index: int = 0,
    populate_optional: bool = False,
) -> object:
    """Produce a valid value for a single field.

    Consults field constraints via `dispatch_constraint` to produce
    constraint-satisfying values (e.g., a valid country code instead of
    an empty string).

    Parameters
    ----------
    field
        The field spec to produce a value for.
    spec_name
        The name of the containing spec, used for deterministic UUID generation.
    index
        Position within a parent list. Non-zero values suffix string fields
        to ensure uniqueness across list items.
    populate_optional
        When True, MODEL and UNION sub-rows include optional fields via
        `generate_populated_row`. When False (default), sub-rows are sparse
        via `generate_base_row`.
    """
    special = _SPECIAL_FIELD_VALUES.get(field.name)
    if special is not None:
        return special(field, spec_name)

    shape = field.shape

    # Geometry fields short-circuit to a WKT literal. PySpark's Geometry
    # validator parses WKT via `from_wkt`; the field is stored as
    # BinaryType (WKB) downstream.
    terminal = terminal_primitive(shape)
    if terminal is not None and _is_geometry_terminal(terminal):
        return _geometry_wkt_from_shape_constraints(terminal.constraints)

    # Non-list fields: try a constraint-driven value (e.g. CountryCode -> "US")
    # before falling back to type defaults. The terminal scalar carries the
    # constraints directly in the no-list case. Lists go through the recursive
    # shape walk so array-level constraints and per-element constraints both
    # get a chance to drive value generation.
    if not has_array_layer(shape) and terminal is not None:
        constraint_val = _value_from_scalar_constraints(terminal)
        if constraint_val is not None:
            if index > 0 and isinstance(constraint_val, str):
                return f"{constraint_val}{index}"
            return constraint_val

    return _value_for_shape(
        shape,
        index=index,
        check_constraints=False,
        populate_optional=populate_optional,
    )


def _default_union_member(union: UnionSpec) -> RecordSpec:
    """Return the union member used when no discriminator value is known.

    A field shared by name across arms always resolves to the same Spark
    type in every arm (enforced by `schema_builder._deduplicate_by_name`,
    which raises otherwise), so any arm's synthesized value is safe to
    write into that shared column -- the member choice is arbitrary. Picks
    the first member, deterministically, so regeneration is stable. See
    `resolve_arm_spec` for why a *constraint* difference between arms never
    reaches this fallback.
    """
    return union.member_specs[0].spec


def resolve_arm_spec(
    union: UnionSpec, discriminator_value: object | None = None
) -> RecordSpec:
    """Return the member `RecordSpec` for one arm of a discriminated union.

    Without a discriminator value, returns the union's first member. That
    fallback is reached only for a check not gated to a specific arm, which
    happens only when the check applies uniformly across arms -- so any arm
    is representative and the first is a safe, deterministic choice.

    Nothing is lost by not knowing the arm here. Two arms can share a field
    name at the same Spark type but with *different* constraints (axle count
    is discriminated on `dimension`, and its `value` carries `ge=1,
    multiple_of=1` where the other `VehicleSelector` arms carry `ge=0`). Such
    divergent-constraint fields are emitted as separate arm-gated checks, so
    their base rows and scaffolds always arrive WITH a discriminator and
    select the correct arm below -- they never reach the first-member
    default. A raise here would therefore fire on the common, correct case
    (uniform shared fields), not catch a bug; the loud guards against a
    divergent field slipping through un-gated live where they can see the
    divergence -- `_deduplicate_by_name` (Spark-type mismatch) and the
    renderer's duplicate-violation-identity check (two checks colliding on
    one arm's label).

    With a value, returns the member that value selects, and raises when it
    selects none: a seeded discriminator that matches no arm is a
    check_builder/scaffold inconsistency, not a reason to fall back to an arm
    whose fields contradict the seed.

    Parameters
    ----------
    union
        The union to resolve an arm from.
    discriminator_value
        The discriminator value identifying the arm (e.g. a scaffold's seeded
        `ElementGuard` value), matching a `discriminator_mapping` key.

    Raises
    ------
    ValueError
        When `discriminator_value` is given but selects no member arm.
    """
    if discriminator_value is None:
        return _default_union_member(union)
    mapping = union.discriminator_mapping or {}
    member_cls = mapping.get(discriminator_value)  # type: ignore[call-overload]
    if member_cls is not None:
        for member in union.member_specs:
            if member.member_cls is member_cls:
                return member.spec
    raise ValueError(
        f"discriminator {discriminator_value!r} selects no arm of union "
        f"{union.name!r} (arms: {sorted(mapping)})"
    )


def _row_from_model_spec(
    spec: RecordSpec,
    *,
    index: int = 0,
    populate_optional: bool = False,
) -> dict[str, Any]:
    """Generate a row dict from an already-extracted model spec."""
    if populate_optional:
        return generate_populated_row(spec, index=index)
    return generate_base_row(spec, index=index)


def _value_for_shape(
    shape: FieldShape,
    *,
    index: int = 0,
    check_constraints: bool = True,
    populate_optional: bool = False,
) -> object:
    """Produce a valid value from a `FieldShape`.

    Each shape layer carries its own constraints: `ArrayOf`'s
    constraints drive list-length decisions; the element shape's
    constraints (visible after descending into `element`) drive
    per-item value generation.

    Parameters
    ----------
    shape
        The field shape to produce a value for.
    index
        Array element index, used to suffix strings for uniqueness.
    check_constraints
        When True, attempt constraint-driven value generation at the
        terminal Scalar before falling back to a primitive default.
    populate_optional
        When True, MODEL and UNION sub-rows include optional fields via
        `generate_populated_row`. When False (default), sub-rows are
        sparse via `generate_base_row`.
    """
    match shape:
        case ArrayOf(element=element, constraints=array_constraints):
            list_val = _list_value_from_shape_constraints(array_constraints)
            if list_val is not None:
                return list_val
            count = _min_length_from_shape_constraints(array_constraints)
            return [
                _value_for_shape(element, index=i, populate_optional=populate_optional)
                for i in range(count)
            ]

        case NewTypeShape(inner=inner):
            return _value_for_shape(
                inner,
                index=index,
                check_constraints=check_constraints,
                populate_optional=populate_optional,
            )

        case MapOf(key=key_shape, value=value_shape):
            # One constraint-valid entry: an empty map satisfies Pydantic
            # but leaves nothing for a conformance scenario to corrupt, so
            # the key/value checks would never fire. A `dict[K, Any]` value
            # (e.g. Infrastructure.source_tags) carries no constraint -- and
            # thus no check -- and `Any` has no value strategy, so the map
            # stays empty: there is nothing to validate or corrupt.
            if isinstance(terminal_scalar(value_shape), AnyScalar):
                return {}
            map_key = _value_for_shape(
                key_shape, index=index, populate_optional=populate_optional
            )
            map_value = _value_for_shape(
                value_shape, index=index, populate_optional=populate_optional
            )
            return {map_key: map_value}

        case LiteralScalar(values=values):
            val = values[0]
            return val.value if isinstance(val, Enum) else val

        case Primitive() as p if (enum_cls := enum_source(p)) is not None:
            return list(enum_cls)[0].value

        case ModelRef(model=m):
            return _row_from_model_spec(
                m, index=index, populate_optional=populate_optional
            )

        case UnionRef(union=u):
            # The selected member's discriminator field is a `Literal[X] = "x"`
            # with a default, so it has `is_required=False`. In the populated
            # case the LiteralScalar branch writes the literal explicitly; in
            # the sparse case the field is omitted from the dict and Pydantic
            # supplies the default during `TypeAdapter.validate_python()`.
            return _row_from_model_spec(
                _default_union_member(u),
                index=index,
                populate_optional=populate_optional,
            )

        case AnyScalar():
            # No value strategy exists for `Any`. The map walk descends
            # into key/value shapes, so a `dict[K, Any]` value would reach
            # here -- no schema declares one today, and this raises loudly
            # rather than guess a value if one ever appears.
            raise TypeError(
                "AnyScalar reached base-row generation; no value strategy exists"
            )

        case Primitive() as scalar:
            constraint_val: object | None = None
            if check_constraints:
                constraint_val = _value_from_scalar_constraints(scalar)
            val = (
                constraint_val
                if constraint_val is not None
                else _primitive_default(scalar.base_type)
            )
            if index > 0 and isinstance(val, str):
                val = f"{val}{index}"
            return val

    raise TypeError(f"Unhandled FieldShape: {shape!r}")


def _value_from_check_enum(
    desc: ExpressionDescriptor, _scalar: Primitive, _cs: ConstraintSource
) -> object:
    """Return the first allowed value from a `check_enum` descriptor."""
    return desc.args[0][0]  # type: ignore[index,no-any-return]


def _value_from_check_string_min_length(
    desc: ExpressionDescriptor, _scalar: Primitive, _cs: ConstraintSource
) -> str:
    """Return a filler string of exactly `min_length` characters.

    The descriptor's sole arg is the `min_length` bound. A shorter string
    (a single character against `min_length > 1`) would violate the
    constraint, making the generated conformance ::valid row invalid.
    """
    min_length: int = desc.args[0]  # type: ignore[assignment]
    return "a" * min_length


def _value_from_check_pattern(
    desc: ExpressionDescriptor, _scalar: Primitive, _cs: ConstraintSource
) -> object:
    """Return a pattern-matching value for a curated raw pydantic pattern.

    Only raw `Field(pattern=)` constraints reach here -- named
    `PatternConstraint` subclasses resolve earlier via `CONSTRAINT_VALUES`.
    An uncurated pattern fails loud, symmetrically with `invalid_value`:
    matching strings can't be generated generically, and silently falling
    back to the primitive default would emit a row that fails the pattern,
    surfacing later as a misleading "row should be valid" Pydantic error.

    Raises
    ------
    ValueError
        When the pattern has no curated entry in `PATTERN_VALUES`.
    """
    curated = curated_pattern_values(desc)
    if curated is None:
        raise uncurated_pattern_error(desc, side="valid")
    return curated.valid


# Builders for descriptor-driven values, keyed by `ExpressionDescriptor.function`.
# `check_bounds` is intentionally absent: it is routed through
# `_value_from_scalar_constraints` to merge multiple bound descriptors (e.g.
# separate Gt + Lt) before calling `valid_bound` once with the combined kwargs,
# so a single-bound path never silently produces a value that violates a second
# bound on the same field.
# `check_pattern` only yields a value for a curated raw pydantic pattern;
# named pattern constraints resolve earlier via `CONSTRAINT_VALUES`.
_DESCRIPTOR_VALUE_BUILDERS: dict[
    str, Callable[[ExpressionDescriptor, Primitive, ConstraintSource], object | None]
] = {
    "check_enum": _value_from_check_enum,
    "check_string_min_length": _value_from_check_string_min_length,
    "check_pattern": _value_from_check_pattern,
}


_CONSTRAINT_VALID_LIST_VALUES: dict[type, list[object]] = {
    LinearReferenceRangeConstraint: [0.0, 1.0],
}


def _value_from_scalar_constraints(scalar: Primitive) -> object | None:
    """Return a value satisfying all dispatched constraints on a scalar.

    Maps known constraint types to valid values directly. For `check_bounds`
    descriptors, merges all bound kwargs from every constraint on the field
    into one dict and calls `valid_bound` once, so a field carrying separate
    `Gt`/`Lt` constraints (two `check_bounds` descriptors) gets a value
    satisfying both bounds. Non-bounds constraints use first-match behavior.
    """
    merged_bounds: dict[str, object] = {}
    for cs in scalar.constraints:
        constraint_type = type(cs.constraint)
        if constraint_type in CONSTRAINT_VALUES:
            return CONSTRAINT_VALUES[constraint_type].valid
        desc = dispatch_constraint(cs.constraint, base_type=scalar.base_type)
        if desc is None:
            continue
        if desc.function == "check_bounds":
            # Skip structural bounds from numeric NewType ranges — those are
            # enforced by the Spark/Parquet type system, not by field constraints.
            if cs.source_name != scalar.base_type:
                merged_bounds.update(desc.kwargs)
            continue
        builder = _DESCRIPTOR_VALUE_BUILDERS.get(desc.function)
        if builder is None:
            continue
        val = builder(desc, scalar, cs)
        if val is not None:
            return val
    if merged_bounds:
        merged_desc = ExpressionDescriptor(
            function="check_bounds", kwargs=tuple(merged_bounds.items())
        )
        return valid_bound(merged_desc)
    return None


def _list_value_from_shape_constraints(
    constraints: tuple[ConstraintSource, ...],
) -> list[object] | None:
    """Return a fixed valid list value if a list-level constraint requires it."""
    for cs in constraints:
        val = _CONSTRAINT_VALID_LIST_VALUES.get(type(cs.constraint))
        if val is not None:
            return val
    return None


def _min_length_from_shape_constraints(
    constraints: tuple[ConstraintSource, ...],
) -> int:
    """Extract the array min_length from constraints anchored at this layer.

    Constraints sit on the `ArrayOf` whose iteration they govern, so any
    `ArrayMinLen` we see here applies to this list level directly -- no
    anchor arithmetic is required.
    """
    for cs in constraints:
        if isinstance(cs.constraint, ArrayMinLen):
            return max(cs.constraint.min_length, 1)
    return 1


def _primitive_default(base_type: str) -> object:
    """Return a type-appropriate default for a primitive base_type."""
    explicit = _PRIMITIVE_DEFAULTS.get(base_type)
    if explicit is not None:
        return explicit
    category = primitive_spark_category(base_type)
    entry = PRIMITIVE_FILL_TABLE.get(category)
    return entry[1] if entry is not None else ""


def _geometry_wkt_from_shape_constraints(
    constraints: tuple[ConstraintSource, ...],
) -> str:
    """Extract the allowed geometry type from constraints and return valid WKT."""
    for cs in constraints:
        if isinstance(cs.constraint, GeometryTypeConstraint):
            geom_type = cs.constraint.allowed_types[0]
            wkt = _VALID_GEOMETRY_WKT.get(geom_type)
            if wkt is not None:
                return wkt
            raise ValueError(f"No WKT defined for geometry type: {geom_type!r}")
    # No constraint — default to POINT
    return _VALID_GEOMETRY_WKT[GeometryType.POINT]
