"""Render Check / ModelCheck IR into complete Python modules."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from overture.schema.system.field_path import (
    ArraySegment,
    Direct,
    FieldPath,
    Iterated,
    MapProjection,
    MapSegment,
)
from overture.schema.system.geometric import GeometryType

from ._render_common import (
    FieldCheckRow,
    ModelCheckRow,
    field_check_rows,
    jinja_env,
    map_runtime_helper,
    model_check_rows,
    py_literal,
    sanitize_field_name,
    schema_const_name,
    tuple_literal,
)
from .check_ir import (
    Check,
    ColumnGuard,
    ElementGuard,
    ModelCheck,
)
from .constraint_dispatch import (
    ExpressionDescriptor,
    FieldEq,
    ForbidIf,
    MinFieldsSet,
    RadioGroup,
    RequireAnyOf,
    RequireAnyTrue,
    RequireIf,
    model_constraint_function,
    require_field_eq,
)
from .schema_builder import SHARED_TYPE_REFS, SchemaField

__all__ = [
    "render_model_module",
]

# Descriptor function names that resolve to helpers from the
# `column_patterns` runtime module (rather than `constraint_expressions`).
# Used to route imports to the correct module. Distinct from
# `_render_common.COLUMN_LEVEL_FUNCTIONS`, which classifies checks that
# emit one Check per field rather than per array element.
_COLUMN_PATTERN_HELPERS = frozenset(
    {
        "array_check",
        "nested_array_check",
        "map_keys_check",
        "map_values_check",
        "check_struct_unique",
    }
)

_SHARED_STRUCT_REFS = frozenset(SHARED_TYPE_REFS.values())

_SPARK_TYPES = frozenset(
    {
        "ArrayType",
        "BinaryType",
        "BooleanType",
        "ByteType",
        "DateType",
        "DoubleType",
        "FloatType",
        "IntegerType",
        "LongType",
        "MapType",
        "ShortType",
        "StringType",
        "StructField",
        "StructType",
        "TimestampType",
    }
)


def _render_condition_desc(parsed: FieldEq) -> str:
    """Render a parsed condition to a human-readable error-message description."""
    display = repr(
        parsed.value.value if isinstance(parsed.value, Enum) else parsed.value
    )
    op = "!=" if parsed.negated else "="
    return f"{parsed.field_name} {op} {display}"


def _render_condition(
    parsed: FieldEq,
    *,
    in_array: bool = False,
    struct_path: tuple[str, ...] = (),
    var: str = "el",
    column_prefix: tuple[str, ...] = (),
) -> str:
    """Render a parsed condition to a PySpark Column expression string.

    `struct_path` is the leaf the constrained model was reached at; the
    condition field lives beside the target field on that same model, so
    its reference must navigate the same leaf (e.g. `el["inner"]["subtype"]`,
    not `el["subtype"]`). `column_prefix` plays the same role for a
    struct-nested (non-iterated) model, qualifying the condition to
    `F.col("details.subtype")`.
    """
    ref = _render_field_ref(
        parsed.field_name,
        in_array=in_array,
        struct_path=struct_path,
        var=var,
        column_prefix=column_prefix,
    )
    op = "!=" if parsed.negated else "=="
    # A bare `== True` / `== False` -- from any boolean condition, whether
    # require_if/forbid_if or require_any_true -- trips ruff's E712, which would
    # rewrite the comparison away; wrap the boolean in `F.lit(...)` so the Column
    # comparison survives post-generation ruff intact.
    value_src = (
        f"F.lit({py_literal(parsed.value)})"
        if isinstance(parsed.value, bool)
        else py_literal(parsed.value)
    )
    return f"{ref} {op} {value_src}"


def _render_field_ref(
    field_name: str,
    *,
    in_array: bool,
    struct_path: tuple[str, ...] = (),
    var: str = "el",
    column_prefix: tuple[str, ...] = (),
) -> str:
    """Render a field reference as F.col("x"), el["x"], or el["struct"]["x"].

    `F.col` accepts dotted names directly so the top-level form keeps
    `field_name` intact. `column_prefix` names the struct segments the model
    was reached through (a struct-nested model constraint at
    `Direct('details')`), so its fields resolve to `F.col("details.foo")`; it
    is empty for a row-root constraint. The in-array form descends a struct via
    `el[...]`, which requires the dotted name to be split into segments before
    applying `struct_path` and the field's own parts.
    """
    if not in_array:
        qualified = ".".join((*column_prefix, field_name))
        return f'F.col("{qualified}")'
    parts = (*struct_path, *field_name.split("."))
    return _element_accessor(var, parts)


def _geometry_type_literal(g: GeometryType) -> str:
    """Spell out `GeometryType.NAME` as valid Python source.

    `repr(g)` yields `<GeometryType.POINT: 'point'>`, which is not a valid
    expression.
    """
    return f"GeometryType.{g.name}"


# Check functions whose first positional arg is a list of allowed values.
# Descriptors store the values as a tuple for hashability; the renderer
# unwraps that one position to a list literal so the generated call matches
# the runtime signature.
_LIST_FIRST_ARG_FUNCTIONS = frozenset({"check_enum"})


def _render_arg(arg: object) -> str:
    """Render a descriptor arg as a valid Python expression string."""
    if isinstance(arg, GeometryType):
        return _geometry_type_literal(arg)
    return py_literal(arg)


def _render_expr_call(
    desc: ExpressionDescriptor,
    col_expr: str,
) -> str:
    """Render a single ExpressionDescriptor call with col injected."""
    parts = [col_expr]
    for idx, arg in enumerate(desc.args):
        if (
            idx == 0
            and desc.function in _LIST_FIRST_ARG_FUNCTIONS
            and isinstance(arg, tuple)
        ):
            parts.append(py_literal(list(arg)))
        else:
            parts.append(_render_arg(arg))
    for k, v in desc.kwargs:
        parts.append(f"{k}={py_literal(v)}")
    if desc.check_nan is not None:
        parts.append(f"check_nan={py_literal(desc.check_nan)}")
    if desc.label is not None:
        parts.append(f"label={py_literal(desc.label)}")
    call = f"{desc.function}({', '.join(parts)})"
    if desc.allow_literals:
        literals = py_literal(list(desc.allow_literals))
        return f"except_literals({col_expr}, {call}, {literals})"
    return call


def _element_accessor(var: str, path: tuple[str, ...]) -> str:
    """Build bracket-notation accessor like `el["foo"]["bar"]`."""
    return var + "".join(f'["{p}"]' for p in path)


def _iter_var_name(idx: int, total: int) -> str:
    """Lambda variable name at iteration depth `idx` (0..total-1) of `total`.

    Single-iteration cases (`total == 1`) return `"el"` from the first
    branch; the innermost frame of a nested iteration uses `"inner"`,
    intermediate frames `"el2"`, `"el3"`, ...
    """
    if idx == 0:
        return "el"
    if idx == total - 1:
        return "inner"
    return f"el{idx + 1}"


def _wrap_element_gate(body: str, var: str, gate_parts: tuple[str, ...]) -> str:
    """Wrap a lambda body in F.when(var[gate].isNotNull(), ...) for nullable parent gating."""
    gate_accessor = _element_accessor(var, gate_parts)
    return f"F.when({gate_accessor}.isNotNull(), {body})"


def _map_iter_var(projection: MapProjection) -> str:
    """Lambda variable name for a map projection: `k` for keys, `v` for values."""
    return "k" if projection is MapProjection.KEY else "v"


@dataclass(frozen=True, slots=True)
class RenderFrame:
    """One iteration frame enriched with its lambda var and runtime helper.

    Attributes
    ----------
    prefix_structs
        Struct segment names between the previous iterating segment (or the
        start of the path) and this one. For the outermost frame this is the
        column struct prefix; joined with `segment.name` it forms the frame's
        `F.col(...)` column. For an inner named frame it is the descent from
        the previous element; for an anonymous frame it is empty.
    segment
        The iterating segment (`ArraySegment` or `MapSegment`) this frame
        iterates. Anonymous when the parent element is itself the container.
    is_innermost
        Whether this is the leaf-most iteration (the base runtime helper is
        used; outer frames use the `nested_` flattening helper).
    var_name
        The lambda parameter name (`el` / `el2` / `inner` for arrays,
        `k` / `v` for maps).
    helper_name
        The `column_patterns` helper this frame calls.
    """

    prefix_structs: tuple[str, ...]
    segment: ArraySegment | MapSegment
    is_innermost: bool
    var_name: str
    helper_name: str

    @property
    def descent(self) -> tuple[str, ...]:
        """Struct accessor from the previous element to this container.

        Empty for an anonymous frame (the parent element already IS this
        container); `prefix_structs + segment.name` for a named frame.
        """
        if self.segment.is_anonymous:
            return ()
        return (*self.prefix_structs, self.segment.name)

    @property
    def column(self) -> str:
        """Dotted `F.col(...)` name for the outermost frame."""
        return ".".join((*self.prefix_structs, self.segment.name))


def _render_frames(target: Iterated) -> tuple[RenderFrame, ...]:
    """Enrich each iteration of *target* with its lambda var and runtime helper.

    One `RenderFrame` per iteration -- every iterating segment, named and
    anonymous, since each is its own `array_check` / `map_*_check` call.
    Built once and consumed by the fold, `_pattern_imports_for`, and the
    model-constraint context so var and helper names never drift (a hazard
    with mixed nesting where two map frames both want `v`).

    Array frames use `el` / `el2` / `inner` (indexed by overall iteration
    position) with `array_check` (innermost) or `nested_array_check`; map
    frames use `k` / `v` with `map_{keys,values}_check` (innermost) or the
    `nested_map_*` flattening variant.
    """
    raw: list[tuple[tuple[str, ...], ArraySegment | MapSegment]] = []
    prefix: list[str] = []
    for seg in target.segments:
        if isinstance(seg, (ArraySegment, MapSegment)):
            raw.append((tuple(prefix), seg))
            prefix = []
        else:
            prefix.append(seg.name)
    total = len(raw)
    frames: list[RenderFrame] = []
    for i, (prefix_structs, seg) in enumerate(raw):
        is_innermost = i == total - 1
        if isinstance(seg, ArraySegment):
            var = _iter_var_name(i, total)
            helper = "array_check" if is_innermost else "nested_array_check"
        else:
            var = _map_iter_var(seg.projection)
            helper = map_runtime_helper(seg.projection, flatten=not is_innermost)
        frames.append(
            RenderFrame(
                prefix_structs=prefix_structs,
                segment=seg,
                is_innermost=is_innermost,
                var_name=var,
                helper_name=helper,
            )
        )
    return tuple(frames)


def _wrap_in_iteration(
    frames: tuple[RenderFrame, ...],
    body: str,
    *,
    gate_parts: tuple[str, ...] = (),
) -> str:
    """Fold *frames* outermost->innermost into nested iteration helper calls.

    The outermost frame targets its `column` (an `F.col` string); each inner
    frame targets an element accessor built from the outer frame's var and the
    inner frame's `descent`. The innermost frame carries `body`. `gate_parts`,
    when set, wraps the OUTERMOST frame's body in a nullable-parent element
    gate (`element_relative_gate` is relative to the outer array element);
    element guards are applied to `body` at the innermost var by the caller,
    the two wrap points staying distinct.
    """

    def build(i: int, accessor: str) -> str:
        frame = frames[i]
        if frame.is_innermost:
            inner = body
        else:
            child = frames[i + 1]
            inner = build(i + 1, _element_accessor(frame.var_name, child.descent))
        if i == 0 and gate_parts:
            inner = _wrap_element_gate(inner, frame.var_name, gate_parts)
        return f"{frame.helper_name}({accessor}, lambda {frame.var_name}: {inner})"

    return build(0, f'"{frames[0].column}"')


def _render_iterated_check_expr(
    target: Iterated,
    desc: ExpressionDescriptor,
    *,
    element_guards: tuple[ElementGuard, ...] = (),
    gate_parts: tuple[str, ...] = (),
) -> str:
    """Render an `Iterated` target to a nested iteration-fold expression.

    Element guards are applied at the innermost iteration variable. This
    assumes each guard's discriminator lives on the same struct level as
    the leaf accessor -- true today because `ElementGuard`s only arise from
    a union variant whose discriminator field is the immediately enclosing
    array element. A future case where a check is reached through further
    iteration *inside* a discriminated union element would need per-guard
    depth info to apply the guard at the correct frame.
    """
    frames = _render_frames(target)
    innermost_var = frames[-1].var_name
    leaf_accessor = _element_accessor(innermost_var, target.leaf)
    body = _render_expr_call(desc, leaf_accessor)

    for guard in reversed(element_guards):
        body = _render_variant_expr(
            body, guard.values, guard.discriminator, in_array=True, var=innermost_var
        )

    return _wrap_in_iteration(frames, body, gate_parts=gate_parts)


def _render_variant_expr(
    inner_expr: str,
    variant_values: tuple[str, ...],
    discriminator_field: str,
    *,
    in_array: bool = False,
    var: str = "el",
) -> str:
    """Wrap an expression in F.when(...).isin() gating for union variant fields."""
    values_repr = py_literal(list(variant_values))
    disc_ref = (
        f'{var}["{discriminator_field}"]'
        if in_array
        else f'F.col("{discriminator_field}")'
    )
    return f"F.when({disc_ref}.isin({values_repr}), {inner_expr})"


def _render_column_gate(expr: str, gate: FieldPath) -> str:
    """Wrap an expression in F.when(gate.isNotNull(), ...) for nullable parent gating."""
    return f'F.when(F.col("{gate}").isNotNull(), {expr})'


def _model_check_func_name(check: ModelCheck, idx: int) -> str:
    """Build the private function name for a model-constraint check.

    An `Iterated` (array/map) target prefixes the column path -- using the
    full encoded `FieldPath` when the check is reached via inner iteration or
    leaf struct navigation, otherwise the outer column name alone -- so
    collisions across nested contexts get distinct identifiers. Row-root
    (`Direct`) targets emit `_{fn}_{idx}_check`.
    """
    fn = model_constraint_function(check.descriptor)
    target = check.target
    if isinstance(target, Iterated):
        has_nested_path = bool(target.iter_struct_paths) or bool(target.leaf)
        prefix_source = str(target) if has_nested_path else target.outer_column
        prefix = sanitize_field_name(prefix_source)
        return f"_{prefix}_{fn}_{idx}_check"
    return f"_{fn}_{idx}_check"


def _check_shape_token(target: FieldPath) -> str:
    """Token naming the runtime `CheckShape` member for a target path.

    Mirrors the member names of `overture.schema.pyspark.check.CheckShape`;
    the check-function template prefixes `CheckShape.` to the result. An
    `Iterated` target renders to an `array<string>` expression (array
    iteration, or a map helper iterating the projected keys/values), a
    `Direct` target to a nullable string.
    """
    return "ARRAY" if isinstance(target, Iterated) else "SCALAR"


def _render_check_expr(check: Check, descriptor_idx: int) -> str:
    """Render the PySpark expression for one descriptor of `check`."""
    desc = check.descriptors[descriptor_idx]
    column_guards = tuple(g for g in check.guards if isinstance(g, ColumnGuard))
    element_guards = tuple(g for g in check.guards if isinstance(g, ElementGuard))

    match check.target:
        case Direct():
            expr = _render_expr_call(desc, f'F.col("{check.target}")')
            if desc.gate:
                expr = _render_column_gate(expr, desc.gate)
        case Iterated():
            gate_parts: tuple[str, ...] = ()
            if desc.gate is not None:
                # check_builder zeros the nullable gate when descending into
                # any iterated container (see `_recurse_into_model`), so a
                # gate paired with an Iterated target should never occur
                # today. If it does, the column-level fallback below would
                # silently hide a codegen bug -- raise instead.
                element_relative = check.target.element_relative_gate(desc.gate)
                if element_relative is None:
                    raise AssertionError(
                        f"Iterated target with column-level gate is not "
                        f"produced by check_builder (gate={desc.gate!r}, "
                        f"target={check.target!r})"
                    )
                gate_parts = element_relative
            expr = _render_iterated_check_expr(
                check.target,
                desc,
                element_guards=element_guards,
                gate_parts=gate_parts,
            )
        case _:
            raise TypeError(
                f"Unhandled FieldPath variant: {type(check.target).__name__}"
            )

    for guard in reversed(column_guards):
        expr = _render_variant_expr(expr, guard.values, guard.discriminator)
    return expr


def _check_function_context(
    *,
    target: FieldPath,
    func_name: str,
    field: str,
    name: str,
    expr: str,
    read_columns: frozenset[str],
) -> dict[str, object]:
    """Assemble the template context dict for one check function."""
    return {
        "func_name": func_name,
        "field": field,
        "check_name": name,
        "expr": expr,
        "shape": _check_shape_token(target),
        "read_columns": read_columns,
    }


def _render_check_function_context(row: FieldCheckRow) -> dict[str, object]:
    """Build the template context for a per-field check function from a row.

    The row carries the final `func_name`, `label`, and `name`; the
    collisions that produce them are resolved once in `field_check_rows`.
    """
    return _check_function_context(
        target=row.check.target,
        func_name=row.func_name,
        field=row.label,
        name=row.name,
        expr=_render_check_expr(row.check, row.descriptor_idx),
        read_columns=row.check.read_columns,
    )


def _render_model_constraint_function_context(row: ModelCheckRow) -> dict[str, object]:
    """Build the template context for a model-constraint check function."""
    check = row.check
    desc = check.descriptor
    target = check.target
    # Build the render frames once; both the field-reference context (var /
    # struct_path) and the iteration wrap below read from them so nothing drifts.
    frames: tuple[RenderFrame, ...] = ()
    column_prefix: tuple[str, ...] = ()
    if isinstance(target, Iterated):
        # The innermost element (array element or projected map value) is
        # iterated, so field references use the element accessor
        # (`inner["foo"]`, `v["foo"]`) under the innermost lambda variable.
        frames = _render_frames(target)
        in_array = True
        var = frames[-1].var_name
        struct_path: tuple[str, ...] = target.leaf
    else:
        # A struct-nested model constraint (`Direct` with segments) qualifies
        # every field reference with the struct prefix (`F.col("details.foo")`);
        # a row-root constraint (empty `Direct`) leaves the prefix empty.
        in_array = False
        var, struct_path = "el", ()
        column_prefix = tuple(s.name for s in target.segments)

    def _field_ref(field_name: str) -> str:
        return _render_field_ref(
            field_name,
            in_array=in_array,
            struct_path=struct_path,
            var=var,
            column_prefix=column_prefix,
        )

    def _condition_ref(parsed: FieldEq) -> str:
        return _render_condition(
            parsed,
            in_array=in_array,
            struct_path=struct_path,
            var=var,
            column_prefix=column_prefix,
        )

    fn = model_constraint_function(desc)

    def _cols_and_names(field_names: tuple[str, ...]) -> tuple[str, str]:
        cols_list = "[" + ", ".join(_field_ref(f) for f in field_names) + "]"
        names_list = py_literal(list(field_names))
        return cols_list, names_list

    match desc:
        case RequireAnyOf() | RadioGroup():
            cols_list, names_list = _cols_and_names(desc.field_names)
            inner_expr = f"{fn}({cols_list}, {names_list})"
        case RequireAnyTrue():
            parsed_conditions = [require_field_eq(c) for c in desc.conditions]
            conds_list = (
                "[" + ", ".join(_condition_ref(p) for p in parsed_conditions) + "]"
            )
            names_list = py_literal([p.field_name for p in parsed_conditions])
            inner_expr = f"{fn}({conds_list}, {names_list})"
        case RequireIf() | ForbidIf():
            target_name = desc.field_names[0]
            parsed = require_field_eq(desc.condition)
            condition_expr = _condition_ref(parsed)
            condition_desc = _render_condition_desc(parsed)
            target_ref = _field_ref(target_name)
            inner_expr = (
                f"{fn}({target_ref}, {condition_expr}, {py_literal(condition_desc)})"
            )
        case MinFieldsSet():
            cols_list, names_list = _cols_and_names(desc.field_names)
            inner_expr = f"{fn}({cols_list}, {names_list}, {desc.count})"
        case _:
            raise TypeError(f"Unhandled model constraint descriptor: {desc!r}")

    if isinstance(target, Iterated):
        if check.gate is not None:
            # A gate reaches only an array-first target: check_builder zeros
            # the gate for any iterated container, so a map-reached model
            # carries none, and `element_relative_gate` asserts the array-first
            # precondition. The wrap assumes a single array level.
            assert not target.iter_struct_paths, (
                f"gated ModelCheck with a nested-array target ({target!r}) is unsupported; "
                f"the element-gate wrap assumes a single array level"
            )
            element_relative = target.element_relative_gate(check.gate)
            assert element_relative is not None, (
                f"ModelCheck gate={check.gate!r} is not reachable as an element-level "
                f"accessor on target={target!r}; gates on ModelChecks must be Iterated "
                f"entering the same outer array as the target"
            )
            inner_expr = _wrap_element_gate(inner_expr, var, element_relative)
        expr = _wrap_in_iteration(frames, inner_expr)
    elif check.gate is not None:
        # A struct-nested model reached through an optional ancestor: skip the
        # constraint when that ancestor is null (accessing a field of a null
        # struct yields null, which would otherwise trip the constraint on an
        # absent model). The gate is a struct prefix of the target, so it reads
        # the target's top-level column and `_render_column_gate` renders
        # `F.when(F.col("details").isNotNull(), ...)`. A gate on an empty
        # (row-root) `Direct` target is meaningless -- check_builder never emits
        # one -- so guard it rather than render a nonsensical `F.when`.
        assert isinstance(target, Direct) and target.segments, (
            f"ModelCheck gate={check.gate!r} on a row-root Direct target={target!r}; "
            f"a gate only pairs with a struct-nested or iterated model"
        )
        expr = _render_column_gate(inner_expr, check.gate)
    else:
        expr = inner_expr

    return _check_function_context(
        target=target,
        func_name=_model_check_func_name(check, row.idx),
        field=row.label,
        name=row.name,
        expr=expr,
        read_columns=check.read_columns,
    )


def _collect_constraint_expr_imports(
    field_checks: list[Check],
    model_checks: list[ModelCheck],
) -> set[str]:
    """Collect all constraint_expressions function names needed.

    Field-descriptor names go through a `_COLUMN_PATTERN_HELPERS`
    filter so column-pattern helpers route to their own import bucket.
    Model-constraint function names (`check_require_any_of`,
    `check_radio_group`, ...) are disjoint from that set, so they pass
    through unfiltered.
    """
    names: set[str] = set()
    for check in field_checks:
        for desc in check.descriptors:
            if desc.function not in _COLUMN_PATTERN_HELPERS:
                names.add(desc.function)
            if desc.allow_literals:
                names.add("except_literals")
    for mc in model_checks:
        names.add(model_constraint_function(mc.descriptor))
    return names


def _needs_geometry_type_import(field_checks: list[Check]) -> bool:
    """Return True when any descriptor arg is a GeometryType instance."""
    for check in field_checks:
        for desc in check.descriptors:
            if any(isinstance(a, GeometryType) for a in desc.args):
                return True
    return False


def _pattern_imports_for(target: FieldPath) -> set[str]:
    """Column-pattern helpers needed to iterate `target`.

    Reads the helper names off `_render_frames` -- the single source of the
    frame->helper mapping the fold also consumes -- so the imports never drift
    from the emitted calls. A `Direct` target needs none.
    """
    if isinstance(target, Iterated):
        return {frame.helper_name for frame in _render_frames(target)}
    return set()


def _collect_column_pattern_imports(
    field_checks: list[Check],
    model_checks: list[ModelCheck],
) -> set[str]:
    """Collect column_patterns function names needed."""
    names: set[str] = set()
    for check in field_checks:
        names |= _pattern_imports_for(check.target)
        for desc in check.descriptors:
            if desc.function in _COLUMN_PATTERN_HELPERS:
                names.add(desc.function)
    for mc in model_checks:
        names |= _pattern_imports_for(mc.target)
    return names


_IDENTIFIER_TOKEN = re.compile(r"[A-Z][A-Za-z0-9_]*")


def _identifier_tokens(expr: str) -> set[str]:
    """Tokenize a Spark type expression into capitalized identifiers."""
    return set(_IDENTIFIER_TOKEN.findall(expr))


def _collect_spark_type_imports(schema_fields: list[SchemaField]) -> set[str]:
    """Collect Spark type class names from schema field type expressions.

    `StructType` and `StructField` are always included: the model module
    template emits the schema constant as `StructType([...])` unconditionally,
    so the import must be present even when there are no fields.
    """
    used: set[str] = {"StructType", "StructField"}
    for sf in schema_fields:
        used |= _identifier_tokens(sf.type_expr) & _SPARK_TYPES
    return used


def _collect_schema_struct_imports(schema_fields: list[SchemaField]) -> set[str]:
    """Collect _schema_structs constant names referenced in field type expressions."""
    refs: set[str] = set()
    for sf in schema_fields:
        refs |= _identifier_tokens(sf.type_expr) & _SHARED_STRUCT_REFS
    return refs


def _field_check_function_entries(
    field_checks: list[Check],
) -> list[dict[str, object]]:
    """Build template contexts for field-level checks."""
    return [
        _render_check_function_context(row) for row in field_check_rows(field_checks)
    ]


def _model_check_function_entries(
    model_checks: list[ModelCheck],
) -> list[dict[str, object]]:
    """Build template contexts for model-level checks."""
    return [
        _render_model_constraint_function_context(row)
        for row in model_check_rows(model_checks)
    ]


def render_model_module(
    model_name: str,
    field_checks: list[Check],
    model_checks: list[ModelCheck],
    schema_fields: list[SchemaField],
    geometry_types: tuple[GeometryType, ...] = (),
    *,
    entry_point: str = "tests.placeholder:Placeholder",
    partitions: Mapping[str, str] | None = None,
) -> str:
    """Render a complete Python module for a model's checks and schema."""
    constraint_expr_fns = sorted(
        _collect_constraint_expr_imports(field_checks, model_checks)
    )
    column_pattern_fns = sorted(
        _collect_column_pattern_imports(field_checks, model_checks)
    )
    spark_types = sorted(_collect_spark_type_imports(schema_fields))
    schema_struct_refs = sorted(_collect_schema_struct_imports(schema_fields))
    geometry_type = _needs_geometry_type_import(field_checks) or bool(geometry_types)
    geometry_types_literal = (
        _render_geometry_types(geometry_types) if geometry_types else None
    )

    check_functions = _field_check_function_entries(
        field_checks
    ) + _model_check_function_entries(model_checks)

    model_title = model_name.replace("_", " ").title()

    template = jinja_env().get_template("model_module.py.jinja2")
    return template.render(
        model_name=model_name,
        model_title=model_title,
        constraint_expr_fns=constraint_expr_fns,
        column_pattern_fns=column_pattern_fns,
        spark_types=spark_types,
        schema_struct_refs=schema_struct_refs,
        geometry_type=geometry_type,
        check_functions=check_functions,
        schema_const_name=schema_const_name(model_name),
        schema_fields=schema_fields,
        geometry_types_literal=geometry_types_literal,
        entry_point=entry_point,
        partitions=dict(partitions) if partitions else {},
    )


def _render_geometry_types(geo: tuple[GeometryType, ...]) -> str:
    """Render a `geometry_types` tuple literal.

    `GeometryType` is an Enum, so `repr()` does not produce a valid
    expression -- members need explicit `GeometryType.NAME` source.
    """
    return tuple_literal(_geometry_type_literal(g) for g in geo)
