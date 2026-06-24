"""Constraint type to PySpark expression descriptor dispatch.

Pure mapping from constraint objects to expression descriptors.
No awareness of field paths, list depth, or struct nesting --
those are composition concerns handled by check_builder.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeAlias

from annotated_types import Ge, Gt, Interval, Le, Lt
from pydantic import Strict
from pydantic._internal._fields import PydanticMetadata

from overture.schema.system.case import to_snake_case
from overture.schema.system.field_constraint.collection import UniqueItemsConstraint
from overture.schema.system.field_constraint.string import (
    JsonPointerConstraint,
    PatternConstraint,
    StrippedConstraint,
)
from overture.schema.system.field_path import FieldPath
from overture.schema.system.model_constraint import (
    Condition,
    ForbidIfConstraint,
    MinFieldsSetConstraint,
    NoExtraFieldsConstraint,
    RadioGroupConstraint,
    RequireAnyOfConstraint,
    RequireIfConstraint,
)
from overture.schema.system.primitive import GeometryTypeConstraint
from overture.schema.system.ref import Reference

from ..extraction.docstring import first_docstring_line
from ..extraction.field import FieldShape, ModelRef, Primitive
from ..extraction.field_walk import has_array_layer, terminal_of
from ..extraction.length_constraints import (
    ArrayMaxLen,
    ArrayMinLen,
    ScalarMaxLen,
    ScalarMinLen,
)
from ..extraction.specs import FieldSpec
from ..extraction.type_registry import primitive_spark_category

__all__ = [
    "ExpressionDescriptor",
    "ForbidIf",
    "MinFieldsSet",
    "ModelConstraintDescriptor",
    "RadioGroup",
    "RequireAnyOf",
    "RequireIf",
    "dispatch_base_type",
    "dispatch_constraint",
    "dispatch_model_constraint",
    "dispatch_newtype",
    "forbid_if_field_shapes",
    "model_constraint_function",
    "model_mutation_function",
]


@dataclass(frozen=True, slots=True)
class ExpressionDescriptor:
    """Describes a constraint_expressions function call.

    `function` names the function (e.g., `"check_bounds"`).
    `args` are positional arguments after `col` and `field`.
    `kwargs` are keyword arguments, stored as a tuple of `(name, value)`
    pairs so the descriptor is hashable -- consumers convert with `dict()`
    when they need mapping access.
    `constraint_type` is the Python class of the constraint that
    produced this descriptor (e.g., `NoWhitespaceConstraint`),
    used by test generators to pick pattern-appropriate mutation values.
    `gate` is the structural path to a nullable ancestor struct; when set,
    the renderer wraps the expression in `F.when(gate.isNotNull(), ...)`.
    `label` is a human-readable description used in error messages
    (e.g., `"ISO 3166-1 alpha-2 country code"`).
    `check_name` overrides the Check.name derivation in error_key;
    when None, the renderer strips the `check_` prefix from `function`.
    """

    function: str
    args: tuple[object, ...] = ()
    kwargs: tuple[tuple[str, object], ...] = ()
    constraint_type: type | None = None
    gate: FieldPath | None = None
    label: str | None = None
    check_name: str | None = None


_BASE_TYPE_DISPATCH: dict[str, tuple[ExpressionDescriptor, ...]] = {
    "HttpUrl": (
        ExpressionDescriptor(function="check_url_format"),
        ExpressionDescriptor(function="check_url_length"),
    ),
    "EmailStr": (ExpressionDescriptor(function="check_email"),),
    "BBox": (
        ExpressionDescriptor(function="check_bbox_completeness"),
        ExpressionDescriptor(function="check_bbox_lat_ordering"),
        ExpressionDescriptor(function="check_bbox_lat_range"),
    ),
}

_NEWTYPE_DISPATCH: dict[str, tuple[ExpressionDescriptor, ...]] = {
    "LinearlyReferencedRange": (
        ExpressionDescriptor(function="check_linear_range_length"),
        ExpressionDescriptor(function="check_linear_range_bounds"),
        ExpressionDescriptor(function="check_linear_range_order"),
    ),
}


# re.UNICODE is Python's implicit default on compiled `str` patterns and needs
# no translation -- Java's regex engine is Unicode-aware without a flag.
# re.IGNORECASE maps to the inline `(?i)` flag Spark's rlike honors. A new
# supported flag with a visible matching effect also belongs in
# `field_constraints._DISPLAY_FLAG_LETTERS`, or docs will hide its behavior.
_SUPPORTED_PATTERN_FLAGS = re.IGNORECASE | re.UNICODE


def compiled_pattern_source(pattern: re.Pattern[str]) -> str:
    """Return the Spark-regex source string for a compiled `re.Pattern`.

    A compiled `re.Pattern` is the only Pydantic carrier for a flagged pattern
    (a bare `Field(pattern=str)` cannot express `re.I`). Translates the flags
    Spark's `rlike` can honor into inline prefixes -- `re.IGNORECASE` becomes
    `(?i)`, the idiom `constraint_expressions.check_url_format` already uses.
    The ASCII/Unicode case-folding divergence between Java and Python is the
    same accepted divergence documented at `check_pattern`.

    Raises
    ------
    NotImplementedError
        For any flag without a faithful `rlike` translation (e.g.
        `re.MULTILINE`), naming the flag rather than silently dropping it.
    """
    unsupported = re.RegexFlag(pattern.flags & ~_SUPPORTED_PATTERN_FLAGS)
    if unsupported:
        raise NotImplementedError(
            f"check_pattern cannot translate regex flag {unsupported!r} to Spark rlike"
        )
    source = pattern.pattern
    # Only IGNORECASE emits a prefix; UNICODE passes the gate but is a no-op
    # (Java is Unicode-aware unflagged). A new supported flag needs its own
    # translation clause here, or it will pass the gate and be silently dropped.
    if pattern.flags & re.IGNORECASE:
        source = f"(?i){source}"
    return source


def normalize_anchor(pattern: str) -> str:
    """Replace trailing `$` with `\\z` for Java/Spark regex compatibility.

    Uses backslash-parity to distinguish a real anchor from an escaped
    literal `$`. Counts the run of backslashes immediately before the
    final `$`: an even count means `$` is unescaped (convert to `\\z`);
    an odd count means it is an escaped literal `$` (leave unchanged).
    """
    if not pattern.endswith("$"):
        return pattern
    prefix = pattern[:-1]  # strip the trailing $
    backslashes = len(prefix) - len(prefix.rstrip("\\"))
    if backslashes % 2 == 0:
        return prefix + r"\z"
    return pattern


def _pattern_check_name(constraint: PatternConstraint) -> str:
    """Derive a snake_case check name from the constraint class name."""
    if type(constraint) is PatternConstraint:
        return "pattern"
    return to_snake_case(type(constraint).__name__.removesuffix("Constraint"))


def _pattern_label(constraint: PatternConstraint) -> str:
    """Extract a human-readable label from a PatternConstraint."""
    if constraint.description:
        return constraint.description
    if (summary := first_docstring_line(type(constraint).__doc__)) is not None:
        return summary.rstrip(".")
    name = type(constraint).__name__.removesuffix("Constraint")
    return to_snake_case(name).replace("_", " ")


_ConstraintHandler = Callable[[Any, str | None], ExpressionDescriptor | None]


_BOUND_ATTRS = ("ge", "gt", "le", "lt")

_FLOAT_BASE_TYPES = frozenset({"float", "float32", "float64"})


def _dispatch_bounds(
    constraint: Ge | Gt | Le | Lt | Interval,
    base_type: str | None,
) -> ExpressionDescriptor:
    """Extract bound kwargs from an annotated_types constraint.

    Coerces integer bound values to float on float-typed columns so
    that generated test mutations match the Spark DoubleType column.
    """
    is_float = base_type in _FLOAT_BASE_TYPES
    kwargs: list[tuple[str, object]] = []
    for attr in _BOUND_ATTRS:
        value = getattr(constraint, attr, None)
        if value is not None:
            if is_float and isinstance(value, int) and not isinstance(value, bool):
                value = float(value)
            kwargs.append((attr, value))
    return ExpressionDescriptor(function="check_bounds", kwargs=tuple(kwargs))


def _dispatch_pattern(
    constraint: PatternConstraint,
    _base_type: str | None,
) -> ExpressionDescriptor:
    """Map a PatternConstraint (or subclass) to a check_pattern descriptor.

    The Python `re` pattern source is embedded verbatim (anchor and inline
    flags aside) into a Java `rlike`. The two engines diverge on Unicode
    shorthand classes and `.` line-terminator handling; that is an accepted
    divergence, documented at `constraint_expressions.check_pattern`.
    """
    return ExpressionDescriptor(
        function="check_pattern",
        args=(normalize_anchor(compiled_pattern_source(constraint.pattern)),),
        constraint_type=type(constraint),
        label=_pattern_label(constraint),
        check_name=_pattern_check_name(constraint),
    )


def _raw_pattern(constraint: object) -> str | None:
    """Return the Spark-regex source of raw pydantic `Field(pattern=)`, or None.

    Pydantic represents `Field(pattern=...)` as a `PydanticMetadata` marker
    (the private `_PydanticGeneralMetadata`) carrying the pattern as either a
    `str` (`Field(pattern="...")`) or a compiled `re.Pattern`
    (`Field(pattern=re.compile(...))` -- the only carrier for a flagged,
    e.g. case-insensitive, pattern). The schema's own `PatternConstraint` is
    handled earlier; raw metadata reaches here from `dict[K, V]` keys/values
    that used `Field(pattern=)` rather than a schema constraint class
    (e.g. `Sources.license_priority`).

    The `PydanticMetadata` check -- not merely a `.pattern` attribute --
    keeps `dispatch_constraint`'s fallback contract intact: an unrelated future
    constraint that happens to expose a `.pattern` still raises `TypeError`
    rather than being silently dispatched as a `check_pattern`. A compiled
    pattern carrying an untranslatable flag raises `NotImplementedError` via
    `compiled_pattern_source`.
    """
    if not isinstance(constraint, PydanticMetadata):
        return None
    pattern = getattr(constraint, "pattern", None)
    if isinstance(pattern, str):
        return pattern
    if isinstance(pattern, re.Pattern):
        return compiled_pattern_source(pattern)
    return None


# Ordered: the first matching entry wins, so any subclass relationship
# between keys must place the more-specific class first. StrippedConstraint
# subclasses PatternConstraint, so it must appear before the PatternConstraint
# fallback entry.
_CONSTRAINT_DISPATCH: list[tuple[type | tuple[type, ...], _ConstraintHandler]] = [
    ((Reference, Strict), lambda _c, _bt: None),
    ((Ge, Gt, Le, Lt, Interval), _dispatch_bounds),
    (
        ArrayMinLen,
        lambda c, _bt: ExpressionDescriptor(
            function="check_array_min_length", args=(c.min_length,)
        ),
    ),
    (
        ArrayMaxLen,
        lambda c, _bt: ExpressionDescriptor(
            function="check_array_max_length", args=(c.max_length,)
        ),
    ),
    (
        ScalarMinLen,
        lambda c, _bt: ExpressionDescriptor(
            function="check_string_min_length", args=(c.min_length,)
        ),
    ),
    (
        ScalarMaxLen,
        lambda c, _bt: ExpressionDescriptor(
            function="check_string_max_length", args=(c.max_length,)
        ),
    ),
    (
        StrippedConstraint,
        lambda c, _bt: ExpressionDescriptor(
            function="check_stripped", constraint_type=type(c)
        ),
    ),
    (
        JsonPointerConstraint,
        lambda c, _bt: ExpressionDescriptor(
            function="check_json_pointer", constraint_type=type(c)
        ),
    ),
    (PatternConstraint, _dispatch_pattern),
    # check_struct_unique uses Spark's array_distinct: structural equality on
    # whole elements, against the raw stored values. Pydantic's
    # UniqueItemsConstraint on list[HttpUrl] compares *normalized* URLs
    # (trailing-slash, lowercase host/scheme), so it catches duplicates that
    # differ only in normalization. We accept that difference -- the PySpark
    # check catches exact duplicates only.
    (
        UniqueItemsConstraint,
        lambda _c, _bt: ExpressionDescriptor(function="check_struct_unique"),
    ),
    (
        GeometryTypeConstraint,
        lambda c, _bt: ExpressionDescriptor(
            function="check_geometry_type", args=tuple(c.allowed_types)
        ),
    ),
]


def dispatch_constraint(
    constraint: object,
    *,
    base_type: str | None = None,
) -> ExpressionDescriptor | None:
    """Map a constraint object to an expression descriptor.

    Parameters
    ----------
    constraint
        The constraint object from `ConstraintSource.constraint`. Length
        constraints arrive as `ArrayMinLen` / `ArrayMaxLen` /
        `ScalarMinLen` / `ScalarMaxLen` -- the typed variants emitted
        by `extraction.type_analyzer.attach_constraints`.
    base_type
        The field's terminal-scalar base type, used to detect float
        bounds.

    Returns
    -------
    ExpressionDescriptor or None
        `None` for explicitly skipped constraints (Reference, Strict).

    Raises
    ------
    TypeError
        For unrecognized constraint types.
    """
    for key_types, handler in _CONSTRAINT_DISPATCH:
        if isinstance(constraint, key_types):
            return handler(constraint, base_type)
    raw_pattern = _raw_pattern(constraint)
    if raw_pattern is not None:
        # Raw pydantic `Field(pattern=)` metadata. `constraint_type` stays
        # None (the pydantic class is a private closure type, not a stable
        # key); the curated valid/invalid pair lives in `PATTERN_VALUES`,
        # keyed by the normalized pattern in `args`.
        return ExpressionDescriptor(
            function="check_pattern",
            args=(normalize_anchor(raw_pattern),),
            label="pattern",
        )
    raise TypeError(f"Unhandled constraint type: {type(constraint).__name__}")


def dispatch_newtype(newtype_name: str) -> tuple[ExpressionDescriptor, ...] | None:
    """Look up a NewType-level expression override.

    Returns None when the NewType decomposes normally into
    individual constraint dispatches.
    """
    return _NEWTYPE_DISPATCH.get(newtype_name)


def dispatch_base_type(base_type: str) -> tuple[ExpressionDescriptor, ...] | None:
    """Look up a base-type-level expression override.

    Handles primitive types like HttpUrl and EmailStr that carry no
    Annotated constraints but need semantic validation functions.
    """
    return _BASE_TYPE_DISPATCH.get(base_type)


@dataclass(frozen=True, slots=True)
class RequireAnyOf:
    """Descriptor for `check_require_any_of`: at least one field must be set."""

    field_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RadioGroup:
    """Descriptor for `check_radio_group`: exactly one boolean field must be True."""

    field_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RequireIf:
    """Descriptor for `check_require_if`: field required when condition holds."""

    field_names: tuple[str, ...]
    condition: Condition


@dataclass(frozen=True, slots=True)
class ForbidIf:
    """Descriptor for `check_forbid_if`: field must be absent when condition holds.

    `field_shapes` pairs non-string-default field names with their `FieldShape`
    so the test renderer can emit type-appropriate `fill_values` literals.
    Stored as a tuple of `(name, shape)` pairs so the descriptor is
    hashable; consumers convert with `dict()` when they need mapping
    access. String fields are omitted because the renderer defaults to
    `""` for them, which is correct. Arrays, model references, and
    non-string scalars (int/uint/float/bool) require an explicit entry
    so the renderer emits a typed literal (`[{}]`, `{}`, `0`, `False`, etc.).
    """

    field_names: tuple[str, ...]
    condition: Condition
    field_shapes: tuple[tuple[str, FieldShape], ...]


@dataclass(frozen=True, slots=True)
class MinFieldsSet:
    """Descriptor for `check_min_fields_set`: at least `count` fields set.

    Matches Pydantic's `model_fields_set` semantics: required fields are
    always set (the constructor requires them) and contribute to the count
    alongside any explicitly-set optional fields. Both kinds are passed to
    the runtime check.
    """

    field_names: tuple[str, ...]
    count: int


ModelConstraintDescriptor: TypeAlias = (
    RequireAnyOf | RadioGroup | RequireIf | ForbidIf | MinFieldsSet
)
"""One variant per model-constraint kind.

Each variant carries only the fields meaningful for that constraint;
`ForbidIf` adds `field_shapes` for non-string targets so the test
renderer can emit type-appropriate `fill_values` literals.
"""


def _first_required_leaf(field_spec: FieldSpec) -> str | None:
    """Return the name of the first required field in a MODEL-kind `FieldSpec`.

    Returns `None` for fields whose terminal is anything but a
    `ModelRef` (scalars, arrays, `UnionRef`s, etc.). The
    `RequireAnyOf` unwrapping uses this to drill into a struct's
    required leaf when one exists; non-struct terminals leave the
    field name unwrapped, which is the correct behavior for scalars
    and arrays. `UnionRef` returns `None` because picking one arm's
    required leaf would silently bias the constraint to that arm.
    """
    if has_array_layer(field_spec.shape):
        return None
    terminal = terminal_of(field_spec.shape)
    if not isinstance(terminal, ModelRef):
        return None
    for sub in terminal.model.fields:
        if sub.is_required:
            return sub.name
    return None


def _unwrap_require_any_of_names(
    field_names: tuple[str, ...],
    by_name: dict[str, FieldSpec],
) -> tuple[str, ...]:
    """Replace struct field names with their first required leaf path."""
    result = []
    for name in field_names:
        field_spec = by_name.get(name)
        leaf = _first_required_leaf(field_spec) if field_spec is not None else None
        result.append(f"{name}.{leaf}" if leaf is not None else name)
    return tuple(result)


def _needs_explicit_fill(shape: FieldShape) -> bool:
    """Whether `shape` needs an explicit (non-default-string) fill value.

    Arrays and model references need `[{}]` / `{}` fill. Non-string
    scalars (int/uint/float/bool families) need a typed fill (0, False,
    etc.). Plain string scalars are omitted -- the `""` default is correct.
    """
    if has_array_layer(shape):
        return True
    terminal = terminal_of(shape)
    if isinstance(terminal, ModelRef):
        return True
    if not isinstance(terminal, Primitive):
        return False
    return primitive_spark_category(terminal.base_type) in ("int", "float", "bool")


def forbid_if_field_shapes(
    field_names: tuple[str, ...],
    shape_by_name: Mapping[str, FieldShape],
) -> tuple[tuple[str, FieldShape], ...]:
    """Build the `field_shapes` pairs for non-string ForbidIf targets.

    Keeps fields whose shape is an array, a model reference, or a
    non-string scalar (int/uint/float/bool families). String fields are
    omitted because the test renderer defaults their fill value to `""`
    without needing the shape.
    """
    return tuple(
        (name, shape)
        for name in field_names
        if (shape := shape_by_name.get(name)) is not None
        and _needs_explicit_fill(shape)
    )


def dispatch_model_constraint(
    constraint: object,
    fields: list[FieldSpec],
) -> tuple[ModelConstraintDescriptor, ...]:
    """Map a model-level constraint to fully constructed typed descriptors.

    Parameters
    ----------
    constraint
        The model constraint object.
    fields
        All fields of the model. Branches consult them as needed --
        `RequireAnyOf` and `ForbidIf` index by name, `MinFieldsSet`
        enumerates every field (required and optional).

    Returns
    -------
    tuple of ModelConstraintDescriptor
        Empty tuple for explicitly skipped constraints (NoExtraFields).
        Most kinds return a single-element tuple. Multi-field
        `@require_if` / `@forbid_if` split into one descriptor per
        target field because the runtime check functions take a single
        target column each.

    Raises
    ------
    TypeError
        For unrecognized constraint types.
    """
    match constraint:
        case NoExtraFieldsConstraint():
            return ()
        case RequireAnyOfConstraint():
            unwrapped = _unwrap_require_any_of_names(
                constraint.field_names, {f.name: f for f in fields}
            )
            return (RequireAnyOf(field_names=unwrapped),)
        case RadioGroupConstraint():
            return (RadioGroup(field_names=constraint.field_names),)
        case RequireIfConstraint():
            # `@require_if(["a", "b"], cond)` means "all of a, b required when
            # cond" -- one runtime check per field, since check_require_if
            # takes a single target column.
            return tuple(
                RequireIf(field_names=(name,), condition=constraint.condition)
                for name in constraint.field_names
            )
        case ForbidIfConstraint():
            shapes_by_field = forbid_if_field_shapes(
                constraint.field_names,
                {f.name: f.shape for f in fields},
            )
            per_field_shapes = dict(shapes_by_field)
            return tuple(
                ForbidIf(
                    field_names=(name,),
                    condition=constraint.condition,
                    field_shapes=(
                        ((name, per_field_shapes[name]),)
                        if name in per_field_shapes
                        else ()
                    ),
                )
                for name in constraint.field_names
            )
        case MinFieldsSetConstraint():
            all_names = tuple(f.name for f in fields)
            return (MinFieldsSet(field_names=all_names, count=constraint.count),)
        case _:
            raise TypeError(f"Unhandled model constraint: {type(constraint).__name__}")


_MODEL_CONSTRAINT_DISPATCH: dict[type[ModelConstraintDescriptor], tuple[str, str]] = {
    RequireAnyOf: ("check_require_any_of", "mutate_require_any_of"),
    RadioGroup: ("check_radio_group", "mutate_radio_group"),
    RequireIf: ("check_require_if", "mutate_require_if"),
    ForbidIf: ("check_forbid_if", "mutate_forbid_if"),
    MinFieldsSet: ("check_min_fields_set", "mutate_min_fields_set"),
}


def model_constraint_function(d: ModelConstraintDescriptor) -> str:
    """Map a `ModelConstraintDescriptor` variant to its runtime function name."""
    return _MODEL_CONSTRAINT_DISPATCH[type(d)][0]


def model_mutation_function(d: ModelConstraintDescriptor) -> str:
    """Map a `ModelConstraintDescriptor` variant to its test mutation helper."""
    return _MODEL_CONSTRAINT_DISPATCH[type(d)][1]
