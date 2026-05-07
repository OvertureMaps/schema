"""Tests for the paired constraint value table."""

import pytest
from overture.schema.codegen.pyspark.constraint_dispatch import ExpressionDescriptor
from overture.schema.codegen.pyspark.test_data.constraint_values import (
    CONSTRAINT_VALUES,
    invalid_bound,
    valid_bound,
)
from overture.schema.system.field_constraint.string import (
    CountryCodeAlpha2Constraint,
    HexColorConstraint,
    JsonPointerConstraint,
    LanguageTagConstraint,
    NoWhitespaceConstraint,
    PatternConstraint,
    PhoneNumberConstraint,
    RegionCodeConstraint,
    SnakeCaseConstraint,
    StrippedConstraint,
    WikidataIdConstraint,
)


class TestConstraintValuesCompleteness:
    """CONSTRAINT_VALUES covers the expected set of constraint types."""

    def test_expected_constraint_types_present(self) -> None:
        expected = {
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
        }
        assert expected <= set(CONSTRAINT_VALUES.keys())


def _pattern_entries() -> list[type]:
    # All CONSTRAINT_VALUES keys that are PatternConstraint subclasses, minus those
    # with dedicated behavioural tests.
    # StrippedConstraint IS a PatternConstraint subclass but uses \Z (not portable
    # as a regex literal), so its contract is verified in TestStrippedConstraintValues.
    # JsonPointerConstraint is NOT a PatternConstraint subclass — it has no .pattern
    # attribute — and is verified in TestJsonPointerConstraintValues.
    _BEHAVIOURAL_EXCLUSIONS = {StrippedConstraint, JsonPointerConstraint}
    return sorted(
        [
            ct
            for ct in CONSTRAINT_VALUES
            if issubclass(ct, PatternConstraint) and ct not in _BEHAVIOURAL_EXCLUSIONS
        ],
        key=lambda ct: ct.__name__,
    )


class TestPatternConstraintValues:
    """For each PatternConstraint subclass, the valid value matches and invalid does not."""

    _PATTERN_ENTRIES = _pattern_entries()

    @pytest.mark.parametrize(
        "constraint_type", _PATTERN_ENTRIES, ids=lambda ct: ct.__name__
    )
    def test_valid_matches_pattern(self, constraint_type: type) -> None:
        constraint = constraint_type()
        assert isinstance(constraint, PatternConstraint)
        cv = CONSTRAINT_VALUES[constraint_type]
        assert isinstance(cv.valid, str)
        assert constraint.pattern.match(cv.valid), (
            f"{constraint_type.__name__}: valid value {cv.valid!r} "
            f"did not match pattern {constraint.pattern.pattern!r}"
        )

    @pytest.mark.parametrize(
        "constraint_type", _PATTERN_ENTRIES, ids=lambda ct: ct.__name__
    )
    def test_invalid_does_not_match_pattern(self, constraint_type: type) -> None:
        constraint = constraint_type()
        assert isinstance(constraint, PatternConstraint)
        cv = CONSTRAINT_VALUES[constraint_type]
        assert isinstance(cv.invalid, str)
        assert not constraint.pattern.match(cv.invalid), (
            f"{constraint_type.__name__}: invalid value {cv.invalid!r} "
            f"matched pattern {constraint.pattern.pattern!r} (should not)"
        )


class TestStrippedConstraintValues:
    """StrippedConstraint valid/invalid contract verified behaviorally."""

    def test_valid_is_stripped(self) -> None:
        cv = CONSTRAINT_VALUES[StrippedConstraint]
        assert isinstance(cv.valid, str)
        assert cv.valid == cv.valid.strip()

    def test_invalid_has_leading_or_trailing_whitespace(self) -> None:
        cv = CONSTRAINT_VALUES[StrippedConstraint]
        assert isinstance(cv.invalid, str)
        assert cv.invalid != cv.invalid.strip()


class TestJsonPointerConstraintValues:
    """JsonPointerConstraint valid/invalid contract verified behaviorally."""

    def test_valid_starts_with_slash_or_is_empty(self) -> None:
        cv = CONSTRAINT_VALUES[JsonPointerConstraint]
        assert isinstance(cv.valid, str)
        assert cv.valid == "" or cv.valid.startswith("/")

    def test_invalid_does_not_start_with_slash(self) -> None:
        cv = CONSTRAINT_VALUES[JsonPointerConstraint]
        assert isinstance(cv.invalid, str)
        assert cv.invalid != "" and not cv.invalid.startswith("/")


class TestBoundFunctions:
    """valid_bound and invalid_bound produce values on opposite sides of each bound kind."""

    def test_valid_bound_ge(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("ge", 5),))
        assert valid_bound(desc) == 5

    def test_valid_bound_gt(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("gt", 5),))
        assert valid_bound(desc) == 6

    def test_valid_bound_le(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("le", 5),))
        assert valid_bound(desc) == 5

    def test_valid_bound_lt(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("lt", 5),))
        assert valid_bound(desc) == 4

    def test_valid_bound_fallback_to_zero(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=())
        assert valid_bound(desc) == 0

    def test_invalid_bound_ge(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("ge", 5),))
        assert invalid_bound(desc) == 4

    def test_invalid_bound_gt(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("gt", 5),))
        assert invalid_bound(desc) == 5

    def test_invalid_bound_le(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("le", 5),))
        assert invalid_bound(desc) == 6

    def test_invalid_bound_lt(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("lt", 5),))
        assert invalid_bound(desc) == 5

    def test_invalid_bound_unknown_raises(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("unknown", 5),))
        with pytest.raises(ValueError):
            invalid_bound(desc)

    def test_valid_bound_gt_lt_float_in_range(self) -> None:
        """Interval(gt=0.0, lt=0.5) returns a value strictly between 0.0 and 0.5."""
        desc = ExpressionDescriptor(
            function="check_bounds", kwargs=(("gt", 0.0), ("lt", 0.5))
        )
        result = valid_bound(desc)
        assert isinstance(result, (int, float))
        assert 0 < result < 0.5

    def test_valid_bound_gt_lt_int_non_degenerate(self) -> None:
        """Adjacent-but-valid int intervals return the interior midpoint."""
        desc_2 = ExpressionDescriptor(
            function="check_bounds", kwargs=(("gt", 0), ("lt", 2))
        )
        assert valid_bound(desc_2) == 1
        desc_4 = ExpressionDescriptor(
            function="check_bounds", kwargs=(("gt", 0), ("lt", 4))
        )
        assert valid_bound(desc_4) == 2

    def test_valid_bound_gt_lt_int_degenerate_raises(self) -> None:
        """Adjacent exclusive int bounds (gt=0, lt=1) have no valid integer midpoint."""
        desc = ExpressionDescriptor(
            function="check_bounds", kwargs=(("gt", 0), ("lt", 1))
        )
        with pytest.raises(ValueError, match="gt=0"):
            valid_bound(desc)

    def test_valid_bound_ge_le_in_range(self) -> None:
        """Interval(ge=0, le=10) returns a value in [0, 10]."""
        desc = ExpressionDescriptor(
            function="check_bounds", kwargs=(("ge", 0), ("le", 10))
        )
        result = valid_bound(desc)
        assert isinstance(result, (int, float))
        assert 0 <= result <= 10

    def test_valid_bound_gt_float_returns_float(self) -> None:
        """gt=0.5 (float bound) returns a float value > 0.5."""
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("gt", 0.5),))
        result = valid_bound(desc)
        assert isinstance(result, float)
        assert result > 0.5

    def test_valid_bound_lt_float_returns_float(self) -> None:
        """lt=0.5 (float bound) returns a float value < 0.5."""
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("lt", 0.5),))
        result = valid_bound(desc)
        assert isinstance(result, float)
        assert result < 0.5

    def test_valid_bound_gt_lt_float_tight_interval(self) -> None:
        """gt=0.5, lt=1.0: midpoint 0.75 satisfies both bounds."""
        desc = ExpressionDescriptor(
            function="check_bounds", kwargs=(("gt", 0.5), ("lt", 1.0))
        )
        result = valid_bound(desc)
        assert isinstance(result, float)
        assert 0.5 < result < 1.0

    def test_invalid_bound_confirmed_correct(self) -> None:
        """invalid_bound is already correct — one violated bound suffices."""
        ge_desc = ExpressionDescriptor(function="check_bounds", kwargs=(("ge", 3),))
        assert invalid_bound(ge_desc) == 2
        lt_desc = ExpressionDescriptor(function="check_bounds", kwargs=(("lt", 3),))
        assert invalid_bound(lt_desc) == 3
