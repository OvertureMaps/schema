"""Render Check / ModelCheck IR into complete Python modules."""

from __future__ import annotations

import re
from collections.abc import Mapping
from enum import Enum

from overture.schema.system.field_path import (
    ArrayPath,
    FieldPath,
    ScalarPath,
)
from overture.schema.system.model_constraint import Condition
from overture.schema.system.primitive import GeometryType

from ._render_common import (
    check_name,
    compute_label_suffixes,
    disambiguate,
    field_label,
    jinja_env,
    model_constraint_field_label,
    parse_field_eq,
    py_literal,
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
    ForbidIf,
    MinFieldsSet,
    RadioGroup,
    RequireAnyOf,
    RequireIf,
    model_constraint_function,
)
from .schema_builder import SHARED_TYPE_REFS, SchemaField

__all__ = [
    "render_feature_module",
]

# Descriptor function names that resolve to helpers from the
# `column_patterns` runtime module (rather than `constraint_expressions`).
# Used to route imports to the correct module. Distinct from
# `_render_common.COLUMN_LEVEL_FUNCTIONS`, which classifies checks that
# emit one Check per field rather than per array element.
_COLUMN_PATTERN_HELPERS = frozenset(
    {"array_check", "nested_array_check", "check_struct_unique"}
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


# Collapses runs of `.`, `[`, `]`, `_` to a single `_` for identifier sanitization.
_PATH_SEPARATOR_RUN = re.compile(r"[.\[\]_]+")


def _sanitize_field_name(field: str) -> str:
    """Convert an encoded field-path string to a valid Python identifier fragment."""
    return _PATH_SEPARATOR_RUN.sub("_", field).strip("_")


def _render_condition_desc(condition: Condition) -> str:
    """Render a Condition to a human-readable description string for error messages."""
    parsed = parse_field_eq(condition)
    if parsed is None:
        raise TypeError(f"Unhandled condition type: {type(condition).__name__}")
    display = repr(
        parsed.value.value if isinstance(parsed.value, Enum) else parsed.value
    )
    op = "!=" if parsed.negated else "="
    return f"{parsed.field_name} {op} {display}"


def _render_condition(
    condition: Condition, *, in_array: bool = False, var: str = "el"
) -> str:
    """Render a Condition to a PySpark Column expression string."""
    parsed = parse_field_eq(condition)
    if parsed is None:
        raise TypeError(f"Unhandled condition type: {type(condition).__name__}")
    ref = _render_field_ref(parsed.field_name, in_array=in_array, var=var)
    op = "!=" if parsed.negated else "=="
    return f"{ref} {op} {py_literal(parsed.value)}"


def _render_field_ref(
    field_name: str,
    *,
    in_array: bool,
    struct_path: tuple[str, ...] = (),
    var: str = "el",
) -> str:
    """Render a field reference as F.col("x"), el["x"], or el["struct"]["x"].

    `F.col` accepts dotted names directly so the top-level form keeps
    `field_name` intact. The in-array form descends a struct via
    `el[...]`, which requires the dotted name to be split into segments
    before applying `struct_path` and the field's own parts.
    """
    if not in_array:
        return f'F.col("{field_name}")'
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
    if desc.label is not None:
        parts.append(f"label={py_literal(desc.label)}")
    return f"{desc.function}({', '.join(parts)})"


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


def _wrap_in_array_iteration(
    column_path: str,
    inner_struct_paths: tuple[tuple[str, ...], ...],
    body: str,
    *,
    gate_parts: tuple[str, ...] = (),
) -> str:
    """Wrap `body` in nested array_check / nested_array_check frames.

    One frame per iteration: `column_path` names the outermost array
    column, `inner_struct_paths` gives the struct accessor from each
    iteration's element to the next array (its length plus one is the
    iteration count). `body` is the innermost lambda body. `gate_parts`,
    when set, wraps the outermost lambda body in a nullable-parent
    element gate.

    The recursion descends one frame per call, carrying the frame index
    and its lambda variable; the innermost frame is `array_check`, every
    outer frame `nested_array_check`.
    """
    total = 1 + len(inner_struct_paths)

    def frame(idx: int, accessor: str, var: str) -> str:
        if idx == total - 1:
            inner = body
            fn = "array_check"
        else:
            child_var = _iter_var_name(idx + 1, total)
            child_accessor = _element_accessor(var, inner_struct_paths[idx])
            inner = frame(idx + 1, child_accessor, child_var)
            fn = "nested_array_check"
        if idx == 0 and gate_parts:
            inner = _wrap_element_gate(inner, var, gate_parts)
        return f"{fn}({accessor}, lambda {var}: {inner})"

    return frame(0, f'"{column_path}"', "el")


def _render_array_check_expr(
    target: ArrayPath,
    desc: ExpressionDescriptor,
    *,
    element_guards: tuple[ElementGuard, ...] = (),
    gate_parts: tuple[str, ...] = (),
) -> str:
    """Render an ArrayPath target to an array_check / nested_array_check expression.

    Element guards are applied at the innermost iteration variable. This
    assumes each guard's discriminator lives on the same struct level as
    the leaf accessor -- which is true today because `ElementGuard`s only
    arise from a union variant whose discriminator field is the
    immediately enclosing array element. A future case where a check is
    reached through further iteration *inside* a discriminated union
    element would need per-guard depth info to apply the guard at the
    correct frame.
    """
    inner_struct_paths = target.iter_struct_paths
    iteration_count = 1 + len(inner_struct_paths)

    innermost_var = _iter_var_name(iteration_count - 1, iteration_count)
    leaf_accessor = _element_accessor(innermost_var, target.leaf)
    body = _render_expr_call(desc, leaf_accessor)

    for guard in reversed(element_guards):
        body = _render_variant_expr(
            body, guard.values, guard.discriminator, in_array=True, var=innermost_var
        )

    return _wrap_in_array_iteration(
        target.column_path, inner_struct_paths, body, gate_parts=gate_parts
    )


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

    Non-array targets emit `_{fn}_{idx}_check`. Array targets prefix the
    column path -- using the full encoded `FieldPath` when the check is
    reached via inner iteration or leaf struct navigation, otherwise the
    outer column name alone -- so collisions across nested contexts get
    distinct identifiers.
    """
    fn = model_constraint_function(check.descriptor)
    match check.target:
        case ArrayPath() as target:
            has_nested_path = bool(target.iter_struct_paths) or bool(target.leaf)
            prefix_source = str(target) if has_nested_path else target.column_path
            prefix = _sanitize_field_name(prefix_source)
            return f"_{prefix}_{fn}_{idx}_check"
        case _:
            return f"_{fn}_{idx}_check"


def _root_field_for_target(target: FieldPath) -> str | None:
    """Top-level schema column for a Check/ModelCheck target.

    Returns the first segment's name, or `None` for an empty path.
    """
    return target.segments[0].name if target.segments else None


def _check_shape_token(target: FieldPath) -> str:
    """Token naming the runtime `CheckShape` member for a target path.

    Mirrors the member names of `overture.schema.pyspark.check.CheckShape`;
    the check-function template prefixes `CheckShape.` to the result. An
    `ArrayPath` target renders to an `array<string>` expression, every
    other path to a nullable string.
    """
    return "ARRAY" if isinstance(target, ArrayPath) else "SCALAR"


def _render_check_expr(check: Check, descriptor_idx: int) -> str:
    """Render the PySpark expression for one descriptor of `check`."""
    desc = check.descriptors[descriptor_idx]
    column_guards = tuple(g for g in check.guards if isinstance(g, ColumnGuard))
    element_guards = tuple(g for g in check.guards if isinstance(g, ElementGuard))

    match check.target:
        case ScalarPath():
            expr = _render_expr_call(desc, f'F.col("{check.target}")')
            if desc.gate:
                expr = _render_column_gate(expr, desc.gate)
        case ArrayPath():
            gate_parts: tuple[str, ...] = ()
            if desc.gate is not None:
                # check_builder zeros the nullable gate when descending into
                # a list (see `_recurse_into_model`), so a gate paired with
                # an ArrayPath target should never occur today. If it does,
                # the column-level fallback below would silently hide a
                # codegen bug -- raise instead.
                element_relative = check.target.element_relative_gate(desc.gate)
                if element_relative is None:
                    raise AssertionError(
                        f"ArrayPath target with column-level gate is not "
                        f"produced by check_builder (gate={desc.gate!r}, "
                        f"target={check.target!r})"
                    )
                gate_parts = element_relative
            expr = _render_array_check_expr(
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
    *, target: FieldPath, func_name: str, field: str, name: str, expr: str
) -> dict[str, object]:
    """Assemble the template context dict for one check function."""
    return {
        "func_name": func_name,
        "field": field,
        "check_name": name,
        "expr": expr,
        "shape": _check_shape_token(target),
        "root_field": _root_field_for_target(target),
    }


def _render_check_function_context(
    check: Check, func_name: str, descriptor_idx: int = 0
) -> dict[str, object]:
    """Build the template context for a per-field check function from a Check."""
    desc = check.descriptors[descriptor_idx]
    return _check_function_context(
        target=check.target,
        func_name=func_name,
        field=field_label(check),
        name=check_name(desc.function, desc.check_name),
        expr=_render_check_expr(check, descriptor_idx),
    )


def _render_model_constraint_function_context(
    check: ModelCheck, idx: int, label_suffix: str
) -> dict[str, object]:
    """Build the template context for a model-constraint check function."""
    desc = check.descriptor
    target = check.target
    match target:
        case ArrayPath():
            in_array = True
            var = "inner" if target.iter_struct_paths else "el"
            struct_path: tuple[str, ...] = target.leaf
        case _:
            in_array = False
            var, struct_path = "el", ()

    def _field_ref(field_name: str) -> str:
        return _render_field_ref(
            field_name, in_array=in_array, struct_path=struct_path, var=var
        )

    fn = model_constraint_function(desc)

    def _cols_and_names() -> tuple[str, str]:
        cols_list = "[" + ", ".join(_field_ref(f) for f in desc.field_names) + "]"
        names_list = py_literal(list(desc.field_names))
        return cols_list, names_list

    match desc:
        case RequireAnyOf() | RadioGroup():
            cols_list, names_list = _cols_and_names()
            inner_expr = f"{fn}({cols_list}, {names_list})"
        case RequireIf() | ForbidIf():
            target_name = desc.field_names[0]
            condition_expr = _render_condition(
                desc.condition, in_array=in_array, var=var
            )
            condition_desc = _render_condition_desc(desc.condition)
            target_ref = _field_ref(target_name)
            inner_expr = (
                f"{fn}({target_ref}, {condition_expr}, {py_literal(condition_desc)})"
            )
        case MinFieldsSet():
            cols_list, names_list = _cols_and_names()
            inner_expr = f"{fn}({cols_list}, {names_list}, {desc.count})"
        case _:
            raise TypeError(f"Unhandled model constraint descriptor: {desc!r}")

    if isinstance(target, ArrayPath):
        if check.gate is not None:
            assert not target.iter_struct_paths, (
                f"gated ModelCheck with a nested-array target ({target!r}) is unsupported; "
                f"the element-gate wrap assumes a single array level"
            )
            element_relative = target.element_relative_gate(check.gate)
            assert element_relative is not None, (
                f"ModelCheck gate={check.gate!r} is not reachable as an element-level "
                f"accessor on target={target!r}; gates on ModelChecks must be ArrayPaths "
                f"entering the same outer array as the target"
            )
            inner_expr = _wrap_element_gate(inner_expr, var, element_relative)
        expr = _wrap_in_array_iteration(
            target.column_path, target.iter_struct_paths, inner_expr
        )
    else:
        assert check.gate is None, (
            f"ModelCheck gate={check.gate!r} paired with non-ArrayPath target={target!r}; "
            f"a gate only makes sense when the constrained model is inside an array"
        )
        expr = inner_expr

    return _check_function_context(
        target=target,
        func_name=_model_check_func_name(check, idx),
        field=model_constraint_field_label(check, label_suffix),
        name=check_name(fn),
        expr=expr,
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
    names: set[str] = {
        desc.function
        for check in field_checks
        for desc in check.descriptors
        if desc.function not in _COLUMN_PATTERN_HELPERS
    }
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
    """Column-pattern helpers needed to iterate `target`."""
    match target:
        case ArrayPath():
            names = {"array_check"}
            if target.iter_struct_paths:
                names.add("nested_array_check")
            return names
        case _:
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
    """Collect Spark type class names from schema field type expressions."""
    if not schema_fields:
        return set()
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
    descriptor_refs: list[tuple[Check, int]] = []
    raw_names: list[str] = []
    for check in field_checks:
        labeled = field_label(check)
        multi = len(check.descriptors) > 1
        for desc_idx, desc in enumerate(check.descriptors):
            suffix = f"_{check_name(desc.function, desc.check_name)}" if multi else ""
            raw_names.append(f"_{_sanitize_field_name(labeled)}{suffix}_check")
            descriptor_refs.append((check, desc_idx))

    func_names = disambiguate(raw_names)
    return [
        _render_check_function_context(check, func_name, desc_idx)
        for (check, desc_idx), func_name in zip(
            descriptor_refs, func_names, strict=True
        )
    ]


def _model_check_function_entries(
    model_checks: list[ModelCheck],
) -> list[dict[str, object]]:
    """Build template contexts for model-level checks."""
    label_suffixes = compute_label_suffixes(model_checks)
    return [
        _render_model_constraint_function_context(mc, idx, label_suffixes[idx])
        for idx, mc in enumerate(model_checks)
    ]


def render_feature_module(
    feature_name: str,
    field_checks: list[Check],
    model_checks: list[ModelCheck],
    schema_fields: list[SchemaField],
    geometry_types: tuple[GeometryType, ...] = (),
    *,
    entry_point: str = "tests.placeholder:Placeholder",
    partitions: Mapping[str, str] | None = None,
) -> str:
    """Render a complete Python module for a feature's checks and schema."""
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

    feature_title = feature_name.replace("_", " ").title()

    template = jinja_env().get_template("feature_module.py.jinja2")
    return template.render(
        feature_name=feature_name,
        feature_title=feature_title,
        constraint_expr_fns=constraint_expr_fns,
        column_pattern_fns=column_pattern_fns,
        spark_types=spark_types,
        schema_struct_refs=schema_struct_refs,
        geometry_type=geometry_type,
        check_functions=check_functions,
        schema_const_name=f"{feature_name.upper()}_SCHEMA",
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
