"""Recursive tree walker that emits validation rules from FeatureSpec trees."""

from __future__ import annotations

from enum import Enum
from typing import cast

from annotated_types import Ge, Gt, Le, Lt, MaxLen, MinLen

from overture.schema.core.scoping.lr import LinearReferenceRangeConstraint

from ..extraction.field_constraints import constraint_pattern
from ..extraction.specs import FeatureSpec, FieldSpec
from ..extraction.type_analyzer import ConstraintSource, TypeInfo, TypeKind
from ..extraction.type_registry import is_storage_primitive_source
from .ir import ConditionIR, RuleIR

__all__ = ["walk_feature"]

# Fields that carry no domain semantics and produce no validation rules.
_STRUCTURAL_FIELDS = frozenset({"theme", "type", "bbox"})
_STRUCTURAL_PREFIX = "ext_"


def walk_feature(spec: FeatureSpec, dataset_name: str) -> list[RuleIR]:
    """Walk an expanded FeatureSpec and emit validation rules.

    Parameters
    ----------
    spec
        An expanded FeatureSpec (fields populated via expand_model_tree).
    dataset_name
        The dataset prefix used in rule names (e.g. ``"place"``).

    Returns
    -------
    list[RuleIR]
        Flat list of validation rules in field-declaration order.
    """
    rules: list[RuleIR] = []
    _walk_fields(
        spec.fields,
        dataset_name,
        prefix="",
        list_columns=[],
        parent_guard=None,
        rules=rules,
    )
    _emit_model_constraints(spec, dataset_name, rules)
    return rules


def _is_structural(field_name: str) -> bool:
    return field_name in _STRUCTURAL_FIELDS or field_name.startswith(_STRUCTURAL_PREFIX)


def _walk_fields(
    fields: list[FieldSpec],
    dataset_name: str,
    *,
    prefix: str,
    list_columns: list[str],
    parent_guard: str | None,
    rules: list[RuleIR],
) -> None:
    for field_spec in fields:
        if _is_structural(field_spec.name):
            continue
        column = f"{prefix}{field_spec.name}" if prefix else field_spec.name
        ti = field_spec.type_info
        _emit_field_rules(
            field_spec, ti, dataset_name, column, list_columns, parent_guard, rules
        )

        if field_spec.model is not None and not field_spec.starts_cycle:
            child_guard = (
                column if ti.is_optional or not field_spec.is_required else parent_guard
            )
            child_list_columns = list(list_columns)
            if ti.is_list:
                child_list_columns.append(column)
            _walk_fields(
                field_spec.model.fields,
                dataset_name,
                prefix=f"{column}.",
                list_columns=child_list_columns,
                parent_guard=child_guard,
                rules=rules,
            )


def _make_rule(
    dataset_name: str,
    column: str,
    check: str,
    suffix: str,
    *,
    value: object | None = None,
    list_columns: list[str] | None = None,
    when: ConditionIR | None = None,
) -> RuleIR:
    return RuleIR(
        name=f"{dataset_name}.{column}.{suffix}",
        column=column,
        check=check,
        severity="error",
        value=value,
        list_columns=list_columns if list_columns else None,
        when=when,
    )


def _domain_constraints(ti: TypeInfo) -> list[ConstraintSource]:
    return [
        cs for cs in ti.constraints if not is_storage_primitive_source(cs.source_name)
    ]


def _emit_field_rules(
    field_spec: FieldSpec,
    ti: TypeInfo,
    dataset_name: str,
    column: str,
    list_columns: list[str],
    parent_guard: str | None,
    rules: list[RuleIR],
) -> None:
    lc_container = list_columns if list_columns else None
    if ti.is_list:
        lc_element: list[str] | None = list(list_columns) + [column]
    else:
        lc_element = list(list_columns) if list_columns else None

    if field_spec.is_required:
        when = (
            ConditionIR(column=parent_guard, check="not_null") if parent_guard else None
        )
        rules.append(
            _make_rule(
                dataset_name,
                column,
                "not_null",
                "not_null",
                list_columns=lc_container,
                when=when,
            )
        )

    constraints = _domain_constraints(ti)
    _emit_numeric_bounds(dataset_name, column, constraints, lc_element, rules)
    _emit_length_constraints(
        dataset_name, column, ti, constraints, lc_container, lc_element, rules
    )
    _emit_enum_rules(dataset_name, column, ti, lc_element, rules)
    _emit_literal_rules(dataset_name, column, ti, lc_element, rules)
    _emit_geometry_rules(dataset_name, column, constraints, lc_container, rules)
    _emit_pattern_rules(dataset_name, column, constraints, lc_element, rules)
    _emit_unique_rules(dataset_name, column, constraints, lc_container, rules)


def _has_range_constraint(constraints: list[ConstraintSource]) -> bool:
    """Whether any constraint signals a paired-range field (e.g. LinearReferenceRange).

    These fields carry Ge/Le from their inner NewType but the range is
    validated structurally, not as independent bounds.
    """
    return any(
        isinstance(cs.constraint, LinearReferenceRangeConstraint) for cs in constraints
    )


def _emit_numeric_bounds(
    dataset_name: str,
    column: str,
    constraints: list[ConstraintSource],
    lc_element: list[str] | None,
    rules: list[RuleIR],
) -> None:
    if _has_range_constraint(constraints):
        return
    ge_val = gt_val = le_val = lt_val = None
    for cs in constraints:
        c = cs.constraint
        if isinstance(c, Ge):
            ge_val = c.ge
        elif isinstance(c, Gt):
            gt_val = c.gt
        elif isinstance(c, Le):
            le_val = c.le
        elif isinstance(c, Lt):
            lt_val = c.lt

    if ge_val is not None and le_val is not None and gt_val is None and lt_val is None:
        rules.append(
            _make_rule(
                dataset_name,
                column,
                "between",
                "range",
                value=[ge_val, le_val],
                list_columns=lc_element,
            )
        )
        return

    if ge_val is not None:
        rules.append(
            _make_rule(
                dataset_name,
                column,
                "gte",
                "gte",
                value=ge_val,
                list_columns=lc_element,
            )
        )
    if gt_val is not None:
        rules.append(
            _make_rule(
                dataset_name,
                column,
                "gt",
                "positive",
                value=gt_val,
                list_columns=lc_element,
            )
        )
    if le_val is not None:
        rules.append(
            _make_rule(
                dataset_name,
                column,
                "lte",
                "lte",
                value=le_val,
                list_columns=lc_element,
            )
        )
    if lt_val is not None:
        rules.append(
            _make_rule(
                dataset_name, column, "lt", "lt", value=lt_val, list_columns=lc_element
            )
        )


def _emit_length_constraints(
    dataset_name: str,
    column: str,
    ti: TypeInfo,
    constraints: list[ConstraintSource],
    lc_container: list[str] | None,
    lc_element: list[str] | None,
    rules: list[RuleIR],
) -> None:
    for cs in constraints:
        c = cs.constraint
        if isinstance(c, MinLen):
            if ti.is_list:
                rules.append(
                    _make_rule(
                        dataset_name,
                        column,
                        "min_list_length",
                        "min_list_length",
                        value=c.min_length,
                        list_columns=lc_container,
                    )
                )
            else:
                rules.append(
                    _make_rule(
                        dataset_name,
                        column,
                        "min_length",
                        "min_length",
                        value=c.min_length,
                        list_columns=lc_element,
                    )
                )
        elif isinstance(c, MaxLen):
            if ti.is_list:
                rules.append(
                    _make_rule(
                        dataset_name,
                        column,
                        "max_list_length",
                        "max_list_length",
                        value=c.max_length,
                        list_columns=lc_container,
                    )
                )
            else:
                rules.append(
                    _make_rule(
                        dataset_name,
                        column,
                        "max_length",
                        "max_length",
                        value=c.max_length,
                        list_columns=lc_element,
                    )
                )


def _emit_enum_rules(
    dataset_name: str,
    column: str,
    ti: TypeInfo,
    lc_element: list[str] | None,
    rules: list[RuleIR],
) -> None:
    if ti.kind == TypeKind.ENUM and ti.source_type is not None:
        enum_class = cast("type[Enum]", ti.source_type)
        members = sorted(m.value for m in enum_class)
        rules.append(
            _make_rule(
                dataset_name,
                column,
                "in",
                "valid",
                value=members,
                list_columns=lc_element,
            )
        )


def _emit_literal_rules(
    dataset_name: str,
    column: str,
    ti: TypeInfo,
    lc_element: list[str] | None,
    rules: list[RuleIR],
) -> None:
    if ti.kind != TypeKind.LITERAL or not ti.literal_values:
        return
    if len(ti.literal_values) == 1:
        rules.append(
            _make_rule(
                dataset_name,
                column,
                "eq",
                "eq",
                value=ti.literal_values[0],
                list_columns=lc_element,
            )
        )
    else:
        rules.append(
            _make_rule(
                dataset_name,
                column,
                "in",
                "valid",
                value=sorted(str(v) for v in ti.literal_values),
                list_columns=lc_element,
            )
        )


def _emit_geometry_rules(
    dataset_name: str,
    column: str,
    constraints: list[ConstraintSource],
    lc_container: list[str] | None,
    rules: list[RuleIR],
) -> None:
    from overture.schema.system.primitive import GeometryTypeConstraint  # noqa: PLC0415

    for cs in constraints:
        c = cs.constraint
        if isinstance(c, GeometryTypeConstraint):
            values = [
                "".join(p.title() for p in gt.value.split("_"))
                for gt in c.allowed_types
            ]
            rules.append(
                _make_rule(
                    dataset_name,
                    column,
                    "geometry_type",
                    "type",
                    value=values,
                    list_columns=lc_container,
                )
            )
            break


def _emit_pattern_rules(
    dataset_name: str,
    column: str,
    constraints: list[ConstraintSource],
    lc_element: list[str] | None,
    rules: list[RuleIR],
) -> None:
    from overture.schema.system.field_constraint.string import (  # noqa: PLC0415
        StrippedConstraint,
    )

    for cs in constraints:
        if isinstance(cs.constraint, StrippedConstraint):
            rules.append(
                _make_rule(
                    dataset_name,
                    column,
                    "pattern",
                    "pattern",
                    value=r"^(\S.*)?\S$",
                    list_columns=lc_element,
                )
            )
            return
        pattern = constraint_pattern(cs.constraint)
        if pattern:
            rules.append(
                _make_rule(
                    dataset_name,
                    column,
                    "pattern",
                    "pattern",
                    value=pattern,
                    list_columns=lc_element,
                )
            )
            return


def _emit_unique_rules(
    dataset_name: str,
    column: str,
    constraints: list[ConstraintSource],
    lc_container: list[str] | None,
    rules: list[RuleIR],
) -> None:
    from overture.schema.system.field_constraint import (  # noqa: PLC0415
        UniqueItemsConstraint,
    )

    for cs in constraints:
        if isinstance(cs.constraint, UniqueItemsConstraint):
            rules.append(
                _make_rule(
                    dataset_name, column, "unique", "unique", list_columns=lc_container
                )
            )
            break


def _emit_model_constraints(
    spec: FeatureSpec,
    dataset_name: str,
    rules: list[RuleIR],
) -> None:
    from overture.schema.system.model_constraint import (  # noqa: PLC0415
        ForbidIfConstraint,
        RadioGroupConstraint,
        RequireAnyOfConstraint,
        RequireIfConstraint,
    )

    for mc in spec.constraints:
        if isinstance(mc, RequireAnyOfConstraint):
            rules.append(
                RuleIR(
                    name=f"{dataset_name}.any_of",
                    check="any_of",
                    severity="error",
                    columns=list(mc.field_names),
                )
            )
        elif isinstance(mc, RadioGroupConstraint):
            rules.append(
                RuleIR(
                    name=f"{dataset_name}.exactly_one_of",
                    check="exactly_one_of",
                    severity="error",
                    columns=list(mc.field_names),
                )
            )
        elif isinstance(mc, RequireIfConstraint):
            cond = _convert_condition(mc.condition)
            for field_name in mc.field_names:
                rules.append(
                    RuleIR(
                        name=f"{dataset_name}.{field_name}.required_when",
                        column=field_name,
                        check="not_null",
                        severity="error",
                        when=cond,
                    )
                )
        elif isinstance(mc, ForbidIfConstraint):
            cond = _convert_condition(mc.condition)
            for field_name in mc.field_names:
                rules.append(
                    RuleIR(
                        name=f"{dataset_name}.{field_name}.forbidden_when",
                        column=field_name,
                        check="is_null",
                        severity="error",
                        when=cond,
                    )
                )


def _unwrap_enum_value(value: object) -> object:
    """Extract the raw value from an enum member, or return as-is."""
    if isinstance(value, Enum):
        return value.value
    return value


def _convert_condition(condition: object) -> ConditionIR:
    from overture.schema.system.model_constraint import (  # noqa: PLC0415
        FieldEqCondition,
        Not,
    )

    if isinstance(condition, Not) and isinstance(condition.inner, FieldEqCondition):
        value = _unwrap_enum_value(condition.inner.value)
        return ConditionIR(column=condition.inner.field_name, check="neq", value=value)
    if isinstance(condition, FieldEqCondition):
        value = _unwrap_enum_value(condition.value)
        return ConditionIR(column=condition.field_name, check="eq", value=value)
    raise ValueError(f"Unsupported condition type: {type(condition)}")
