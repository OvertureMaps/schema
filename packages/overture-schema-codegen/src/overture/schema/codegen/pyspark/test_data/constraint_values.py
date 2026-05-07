"""Paired valid/invalid value generation for string-constraint and numeric-bound checks.

Each entry in `CONSTRAINT_VALUES` carries both sides of the pair:
`valid` is accepted by the constraint; `invalid` violates it.
Both sides are mandatory — partial entries are not allowed.

Consumed by `base_row` (uses the `valid` side to produce valid base rows)
and `invalid_value` (uses the `invalid` side to produce scenario mutations).

`valid_bound` and `invalid_bound` are analogous functions for numeric
bound descriptors, placed here so both sides of every constraint kind
live in one module.
"""

from __future__ import annotations

from dataclasses import dataclass

from overture.schema.system.field_constraint.string import (
    CountryCodeAlpha2Constraint,
    HexColorConstraint,
    JsonPointerConstraint,
    LanguageTagConstraint,
    NoWhitespaceConstraint,
    PhoneNumberConstraint,
    RegionCodeConstraint,
    SnakeCaseConstraint,
    StrippedConstraint,
    WikidataIdConstraint,
)

from ..constraint_dispatch import ExpressionDescriptor, normalize_anchor

__all__ = [
    "CONSTRAINT_VALUES",
    "PATTERN_VALUES",
    "ConstraintValues",
    "curated_pattern_values",
    "invalid_bound",
    "uncurated_pattern_error",
    "valid_bound",
]


@dataclass(frozen=True, slots=True)
class ConstraintValues:
    """A paired valid/invalid value for one constraint type."""

    valid: object
    invalid: object


CONSTRAINT_VALUES: dict[type, ConstraintValues] = {
    CountryCodeAlpha2Constraint: ConstraintValues(valid="US", invalid="99"),
    HexColorConstraint: ConstraintValues(valid="#aabbcc", invalid="not-hex"),
    JsonPointerConstraint: ConstraintValues(valid="/valid/pointer", invalid="no-slash"),
    LanguageTagConstraint: ConstraintValues(valid="en", invalid="123"),
    NoWhitespaceConstraint: ConstraintValues(
        valid="nowhitespace", invalid="has whitespace"
    ),
    PhoneNumberConstraint: ConstraintValues(
        valid="+1 555-555-5555", invalid="1234567890"
    ),
    RegionCodeConstraint: ConstraintValues(valid="US-CA", invalid="99-999"),
    SnakeCaseConstraint: ConstraintValues(valid="snake_case", invalid="HAS SPACES"),
    StrippedConstraint: ConstraintValues(valid="clean", invalid=" has spaces "),
    WikidataIdConstraint: ConstraintValues(valid="Q42", invalid="P999"),
}


# Curated valid/invalid pairs for fields whose only string constraint is a
# raw pydantic `Field(pattern=...)` (a `_PydanticGeneralMetadata`, not a
# schema constraint class -- so it has no `CONSTRAINT_VALUES` type key).
# Keyed by the anchor-normalized pattern that lands in the generated
# `check_pattern` descriptor's `args`, so both `base_row` and
# `invalid_value` look it up via `desc.args[0]`. An uncurated raw pattern
# fails loud on both sides rather than guessing a value.
#
# Generation-principle gap: this table is hand-maintained and keyed by the
# literal regex, so it drifts from the schema -- a renamed or retuned
# `Field(pattern=)` silently loses its entry until the next regeneration
# fails loud. The principled fix is to derive both sides from the regex
# itself (e.g. a matching/non-matching string generator), removing the
# hand-keyed table entirely. Out of scope here; tracked separately.
PATTERN_VALUES: dict[str, ConstraintValues] = {
    # Sources.license_priority key (LicenseShortname): `^[A-Za-z0-9._+\-]+$`.
    normalize_anchor(r"^[A-Za-z0-9._+\-]+$"): ConstraintValues(
        valid="ODbL-1.0", invalid="bad license!"
    ),
}


def curated_pattern_values(desc: ExpressionDescriptor) -> ConstraintValues | None:
    """Curated valid/invalid pair for a raw-pattern `check_pattern` descriptor.

    The pattern key is the descriptor's first arg (the anchor-normalized
    regex). Returns None when the pattern is not curated in `PATTERN_VALUES`
    -- named constraints resolve via `CONSTRAINT_VALUES` instead, and an
    uncurated raw pattern has no values.
    """
    pattern = desc.args[0] if desc.args else None
    if isinstance(pattern, str):
        return PATTERN_VALUES.get(pattern)
    return None


def uncurated_pattern_error(desc: ExpressionDescriptor, *, side: str) -> ValueError:
    """Build the error for a `check_pattern` descriptor with no curated value.

    Raised symmetrically by `base_row` (valid side) and `invalid_value`
    (invalid side) when a raw `Field(pattern=)` has no `PATTERN_VALUES`
    entry: both name the table to update rather than guessing a value.

    Parameters
    ----------
    desc
        The uncurated `check_pattern` descriptor.
    side
        Which value could not be produced -- `"valid"` or `"invalid"`.
    """
    return ValueError(
        f"No {side} value defined for check_pattern with "
        f"constraint_type={desc.constraint_type!r}, pattern={desc.args!r}. "
        "Add an entry to CONSTRAINT_VALUES (named constraint) or "
        "PATTERN_VALUES (raw pydantic pattern) in constraint_values.py."
    )


def valid_bound(desc: ExpressionDescriptor) -> object:
    """Produce a value satisfying a bounds check for base row generation.

    Prefers inclusive boundaries: if `ge` is present it is already a valid
    value; if `le` is present and `ge` is absent, `le` is valid. When only
    exclusive bounds remain, a strictly-interior value is computed: midpoint
    for both-exclusive, or a type-aware step away from a single bound.

    Parameters
    ----------
    desc
        A `check_bounds` descriptor with at least one bound kwarg.

    Returns
    -------
    object
        A value on the valid side of all bounds. Falls back to `0` when
        no recognised bound key is present.
    """
    kwargs = dict(desc.kwargs)
    if "ge" in kwargs:
        return kwargs["ge"]
    if "le" in kwargs:
        return kwargs["le"]
    gt = kwargs.get("gt")
    lt = kwargs.get("lt")
    if gt is not None and lt is not None:
        # Midpoint: integer midpoint for int bounds, float midpoint for float.
        if isinstance(gt, float) or isinstance(lt, float):
            return (float(gt) + float(lt)) / 2.0  # type: ignore[arg-type,operator]
        mid = (gt + lt) // 2  # type: ignore[operator]
        if not (gt < mid < lt):  # type: ignore[operator]
            raise ValueError(
                f"No valid integer strictly between gt={gt!r} and lt={lt!r}"
            )
        return mid
    if gt is not None:
        step: object = 1.0 if isinstance(gt, float) else 1
        return gt + step  # type: ignore[operator]
    if lt is not None:
        step = 1.0 if isinstance(lt, float) else 1
        return lt - step  # type: ignore[operator]
    return 0


def invalid_bound(desc: ExpressionDescriptor) -> object:
    """Produce a value violating a bounds check for invalid-value generation.

    The `ge` / `le` branches return one below / above the bound. For
    `ge=0` this returns `-1`, which violates the bound but would also
    underflow an unsigned base type. No schema today combines `ge=0` with
    an unsigned terminal -- if that ever changes, the caller will need to
    consult the base type and pick a sentinel (e.g. a string or null) for
    the violating value.

    Parameters
    ----------
    desc
        A `check_bounds` descriptor with at least one bound kwarg.

    Raises
    ------
    ValueError
        When no recognised bound key is found.
    """
    kwargs = dict(desc.kwargs)
    if "ge" in kwargs:
        return kwargs["ge"] - 1  # type: ignore[operator]
    if "gt" in kwargs:
        return kwargs["gt"]
    if "le" in kwargs:
        return kwargs["le"] + 1  # type: ignore[operator]
    if "lt" in kwargs:
        return kwargs["lt"]
    raise ValueError(f"No recognised bound key in kwargs: {kwargs!r}")
