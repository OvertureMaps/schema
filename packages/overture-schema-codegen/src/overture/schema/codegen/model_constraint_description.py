"""Convert model-level constraints to human-readable prose.

Handles RequireAnyOf, RadioGroup, ForbidIf, RequireIf, and other
ModelConstraint types. Produces descriptions and per-field notes for
documentation rendering.
"""

from __future__ import annotations

from dataclasses import dataclass

from overture.schema.system.model_constraint import (
    FieldEqCondition,
    ForbidIfConstraint,
    MinFieldsSetConstraint,
    ModelConstraint,
    NoExtraFieldsConstraint,
    Not,
    RadioGroupConstraint,
    RequireAnyOfConstraint,
    RequireIfConstraint,
)

__all__ = ["analyze_model_constraints"]

_ConditionalConstraint = RequireIfConstraint | ForbidIfConstraint


@dataclass(frozen=True)
class _ConstraintEntry:
    """A constraint description paired with the field names it affects."""

    description: str
    field_names: frozenset[str]


def _format_field_list(names: tuple[str, ...]) -> str:
    """Format field names as backtick-quoted, comma-separated list."""
    return ", ".join(f"`{n}`" for n in names)


def _conditional_verb(constraint: _ConditionalConstraint) -> str:
    """Return 'required' or 'forbidden' based on constraint type."""
    return "required" if isinstance(constraint, RequireIfConstraint) else "forbidden"


def _plural_verb(names: tuple[str, ...]) -> str:
    """Return 'is' or 'are' based on field count."""
    return "are" if len(names) > 1 else "is"


def _unwrap_field_eq(condition: object) -> tuple[FieldEqCondition, bool] | None:
    """Extract the FieldEqCondition from a condition, with negation flag.

    Returns (field_eq, is_negated) or None for unrecognized conditions.
    """
    if isinstance(condition, Not) and isinstance(condition.inner, FieldEqCondition):
        return condition.inner, True
    if isinstance(condition, FieldEqCondition):
        return condition, False
    return None


def _describe_condition(condition: object) -> str:
    """Render a Condition as human-readable text."""
    unwrapped = _unwrap_field_eq(condition)
    if unwrapped is not None:
        field_eq, negated = unwrapped
        op = "≠" if negated else "="
        return f"`{field_eq.field_name}` {op} `{field_eq.value}`"
    return str(condition)


def _describe_conditional(constraint: _ConditionalConstraint) -> str:
    """Describe a require_if or forbid_if constraint."""
    fields = _format_field_list(constraint.field_names)
    verb = _conditional_verb(constraint)
    cond = _describe_condition(constraint.condition)
    return f"{fields} {_plural_verb(constraint.field_names)} {verb} when {cond}"


def _consolidation_key(
    constraint: _ConditionalConstraint,
) -> tuple[type, tuple[str, ...], str] | None:
    """Return a grouping key if the constraint is consolidatable, else None.

    Consolidatable: same type, same field_names, plain FieldEqCondition
    (not negated) on the same condition field.
    """
    cond = constraint.condition
    if not isinstance(cond, FieldEqCondition):
        return None
    return (type(constraint), constraint.field_names, cond.field_name)


def _as_field_eq(constraint: _ConditionalConstraint) -> FieldEqCondition:
    """Narrow a conditional constraint's condition to FieldEqCondition.

    Only called on constraints that passed _consolidation_key, which
    rejects non-FieldEqCondition conditions.
    """
    cond = constraint.condition
    if not isinstance(cond, FieldEqCondition):
        raise TypeError(f"Expected FieldEqCondition, got {type(cond).__name__}")
    return cond


def _describe_consolidated(
    constraints: list[_ConditionalConstraint],
) -> str:
    """Describe a group of consolidated conditional constraints."""
    first = constraints[0]
    fields = _format_field_list(first.field_names)
    verb = _conditional_verb(first)
    cond_field = _as_field_eq(first).field_name
    values = ", ".join(f"`{_as_field_eq(c).value}`" for c in constraints)
    return (
        f"{fields} {_plural_verb(first.field_names)} {verb} "
        f"when `{cond_field}` is one of: {values}"
    )


def _condition_field_names(condition: object) -> frozenset[str]:
    """Extract field names referenced by a condition."""
    unwrapped = _unwrap_field_eq(condition)
    if unwrapped is not None:
        return frozenset({unwrapped[0].field_name})
    return frozenset()


def _affected_field_names(constraint: ModelConstraint) -> frozenset[str]:
    """Return all field names referenced by a constraint.

    Includes both constrained field_names and condition trigger fields.
    Returns empty set for constraints that don't reference specific fields
    (NoExtraFieldsConstraint, MinFieldsSetConstraint).
    """
    if isinstance(constraint, (NoExtraFieldsConstraint, MinFieldsSetConstraint)):
        return frozenset()
    if isinstance(constraint, (RequireIfConstraint, ForbidIfConstraint)):
        return frozenset(constraint.field_names) | _condition_field_names(
            constraint.condition
        )
    if isinstance(constraint, (RequireAnyOfConstraint, RadioGroupConstraint)):
        return frozenset(constraint.field_names)
    return frozenset()


def _describe_one(constraint: ModelConstraint) -> str | None:
    """Describe a single constraint, or None to skip it."""
    if isinstance(constraint, NoExtraFieldsConstraint):
        return None
    if isinstance(constraint, RequireAnyOfConstraint):
        return (
            f"At least one of {_format_field_list(constraint.field_names)} must be set"
        )
    if isinstance(constraint, RadioGroupConstraint):
        return f"Exactly one of {_format_field_list(constraint.field_names)} must be `true`"
    if isinstance(constraint, MinFieldsSetConstraint):
        return f"At least {constraint.count} fields must be set"
    if isinstance(constraint, (RequireIfConstraint, ForbidIfConstraint)):
        return _describe_conditional(constraint)
    return f"`{constraint.name}`"


def _analyze_constraints(
    constraints: tuple[ModelConstraint, ...],
) -> list[_ConstraintEntry]:
    """Analyze constraints into descriptions paired with affected fields.

    Handles consolidation and filtering, preserving original declaration order.
    """
    groups: dict[
        tuple[type, tuple[str, ...], str], list[tuple[int, _ConditionalConstraint]]
    ] = {}
    standalone: list[tuple[int, ModelConstraint]] = []

    for i, c in enumerate(constraints):
        if isinstance(c, (RequireIfConstraint, ForbidIfConstraint)):
            key = _consolidation_key(c)
            if key is not None:
                groups.setdefault(key, []).append((i, c))
                continue
        standalone.append((i, c))

    entries: list[tuple[int, _ConstraintEntry]] = []

    for group_items in groups.values():
        first_idx = group_items[0][0]
        group_constraints = [c for _, c in group_items]
        all_fields = frozenset[str]().union(
            *(_affected_field_names(c) for c in group_constraints)
        )
        if len(group_constraints) == 1:
            desc = _describe_one(group_constraints[0])
        else:
            desc = _describe_consolidated(group_constraints)
        if desc is not None:
            entries.append((first_idx, _ConstraintEntry(desc, all_fields)))

    for idx, c in standalone:
        desc = _describe_one(c)
        if desc is not None:
            entries.append((idx, _ConstraintEntry(desc, _affected_field_names(c))))

    entries.sort(key=lambda e: e[0])
    return [entry for _, entry in entries]


def analyze_model_constraints(
    constraints: tuple[ModelConstraint, ...],
) -> tuple[list[str], dict[str, list[str]]]:
    """Analyze constraints into descriptions and per-field notes in one pass.

    Returns (descriptions, field_notes) where descriptions is the list of
    human-readable constraint strings and field_notes maps field names to
    constraint descriptions that reference them.
    """
    entries = _analyze_constraints(constraints)

    descriptions = [entry.description for entry in entries]

    field_notes: dict[str, list[str]] = {}
    for entry in entries:
        for name in entry.field_names:
            field_notes.setdefault(name, []).append(entry.description)

    return descriptions, field_notes
