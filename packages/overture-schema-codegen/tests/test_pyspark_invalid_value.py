"""Tests for constraint-violating value generation."""

import pytest
from overture.schema.codegen.pyspark.constraint_dispatch import ExpressionDescriptor
from overture.schema.codegen.pyspark.test_data.invalid_value import invalid_value
from overture.schema.system.field_constraint.string import (
    CountryCodeAlpha2Constraint,
    JsonPointerConstraint,
    NoWhitespaceConstraint,
    RegionCodeConstraint,
    StrippedConstraint,
)
from overture.schema.system.geometric.geom import GeometryType


class TestInvalidValueRequired:
    def test_returns_none(self) -> None:
        desc = ExpressionDescriptor(function="check_required")
        assert invalid_value(desc) is None


class TestInvalidValueEnum:
    def test_returns_invalid_sentinel(self) -> None:
        desc = ExpressionDescriptor(function="check_enum", args=(["a", "b"],))
        assert invalid_value(desc) == "__INVALID__"


class TestInvalidValueBounds:
    def test_ge(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("ge", 0),))
        assert invalid_value(desc) == -1

    def test_ge_float(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("ge", 0.0),))
        assert invalid_value(desc) == -1.0
        assert isinstance(invalid_value(desc), float)

    def test_gt(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("gt", 0),))
        assert invalid_value(desc) == 0

    def test_le(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("le", 100),))
        assert invalid_value(desc) == 101

    def test_lt(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("lt", 100),))
        assert invalid_value(desc) == 100

    def test_unknown_bound_raises(self) -> None:
        desc = ExpressionDescriptor(function="check_bounds", kwargs=(("unknown", 5),))
        with pytest.raises(ValueError):
            invalid_value(desc)


class TestInvalidValueMultipleOf:
    def test_returns_non_integral_float_for_unit_divisor(self) -> None:
        desc = ExpressionDescriptor(function="check_multiple_of", args=(1,))
        value = invalid_value(desc)
        assert isinstance(value, float)
        assert not value.is_integer()

    def test_returns_non_multiple_for_non_unit_divisor(self) -> None:
        desc = ExpressionDescriptor(function="check_multiple_of", args=(0.5,))
        value = invalid_value(desc)
        assert isinstance(value, float)
        assert value % 0.5 != 0


class TestInvalidValuePattern:
    def test_unknown_constraint_type_raises(self) -> None:
        desc = ExpressionDescriptor(function="check_pattern", args=(r"^[A-Z]+$",))
        with pytest.raises(ValueError, match="No invalid value"):
            invalid_value(desc)

    def test_no_whitespace_pattern(self) -> None:
        desc = ExpressionDescriptor(
            function="check_pattern",
            args=(r"^\S+$",),
            constraint_type=NoWhitespaceConstraint,
        )
        assert invalid_value(desc) == "has whitespace"


class TestInvalidValueStringTypes:
    def test_country_code(self) -> None:
        desc = ExpressionDescriptor(
            function="check_pattern",
            constraint_type=CountryCodeAlpha2Constraint,
        )
        assert invalid_value(desc) == "99"

    def test_region_code(self) -> None:
        desc = ExpressionDescriptor(
            function="check_pattern",
            constraint_type=RegionCodeConstraint,
        )
        assert invalid_value(desc) == "99-999"

    def test_url_format(self) -> None:
        desc = ExpressionDescriptor(function="check_url_format")
        assert invalid_value(desc) == "not-a-url"

    def test_url_length(self) -> None:
        desc = ExpressionDescriptor(function="check_url_length")
        assert invalid_value(desc) == "https://" + "x" * 2076

    def test_email(self) -> None:
        desc = ExpressionDescriptor(function="check_email")
        assert invalid_value(desc) == "not-an-email"

    def test_stripped(self) -> None:
        desc = ExpressionDescriptor(
            function="check_stripped", constraint_type=StrippedConstraint
        )
        assert invalid_value(desc) == " has spaces "

    def test_json_pointer(self) -> None:
        desc = ExpressionDescriptor(
            function="check_json_pointer", constraint_type=JsonPointerConstraint
        )
        assert invalid_value(desc) == "no-slash"


class TestInvalidValueCollections:
    def test_min_length_empty_list(self) -> None:
        desc = ExpressionDescriptor(function="check_array_min_length", args=(1,))
        assert invalid_value(desc) == []

    def test_max_length_oversized(self) -> None:
        desc = ExpressionDescriptor(function="check_array_max_length", args=(3,))
        assert invalid_value(desc) == [{}] * 4

    def test_string_min_length_empty_string(self) -> None:
        desc = ExpressionDescriptor(function="check_string_min_length", args=(1,))
        assert invalid_value(desc) == ""

    def test_string_max_length_oversized_string(self) -> None:
        desc = ExpressionDescriptor(function="check_string_max_length", args=(3,))
        assert invalid_value(desc) == "x" * 4


class TestInvalidValueLinearRange:
    def test_linear_range_length(self) -> None:
        desc = ExpressionDescriptor(function="check_linear_range_length")
        assert invalid_value(desc) == [0.5]

    def test_linear_range_bounds(self) -> None:
        desc = ExpressionDescriptor(function="check_linear_range_bounds")
        assert invalid_value(desc) == [1.5, 2.0]

    def test_linear_range_order(self) -> None:
        desc = ExpressionDescriptor(function="check_linear_range_order")
        assert invalid_value(desc) == [0.8, 0.2]


class TestInvalidValueGeometry:
    def test_point_not_allowed_picks_point(self) -> None:
        # Allowed: polygon only → first candidate (POINT) not in allowed set
        desc = ExpressionDescriptor(
            function="check_geometry_type", args=(GeometryType.POLYGON,)
        )
        assert invalid_value(desc) == "POINT (0 0)"

    def test_point_allowed_picks_linestring(self) -> None:
        desc = ExpressionDescriptor(
            function="check_geometry_type",
            args=(GeometryType.POINT, GeometryType.POLYGON),
        )
        assert invalid_value(desc) == "LINESTRING (0 0, 1 1)"

    def test_point_and_linestring_allowed_picks_collection(self) -> None:
        desc = ExpressionDescriptor(
            function="check_geometry_type",
            args=(GeometryType.POINT, GeometryType.LINE_STRING),
        )
        assert invalid_value(desc) == "GEOMETRYCOLLECTION EMPTY"

    def test_all_candidates_allowed_raises(self) -> None:
        desc = ExpressionDescriptor(
            function="check_geometry_type",
            args=(
                GeometryType.POINT,
                GeometryType.LINE_STRING,
                GeometryType.GEOMETRY_COLLECTION,
            ),
        )
        with pytest.raises(ValueError):
            invalid_value(desc)


class TestInvalidValueRawPattern:
    """Raw pydantic `Field(pattern=)` map keys curated in `PATTERN_VALUES`."""

    def test_curated_license_pattern_returns_invalid(self) -> None:
        # Sources.license_priority key pattern, anchor-normalized.
        desc = ExpressionDescriptor(
            function="check_pattern", args=(r"^[A-Za-z0-9._+\-]+\z",)
        )
        assert invalid_value(desc) == "bad license!"

    def test_uncurated_pattern_still_raises(self) -> None:
        desc = ExpressionDescriptor(function="check_pattern", args=(r"^xyz\z",))
        with pytest.raises(ValueError, match="check_pattern"):
            invalid_value(desc)


class TestInvalidValueUnknown:
    def test_unknown_function_raises(self) -> None:
        desc = ExpressionDescriptor(function="check_something_unknown")
        with pytest.raises(ValueError):
            invalid_value(desc)
