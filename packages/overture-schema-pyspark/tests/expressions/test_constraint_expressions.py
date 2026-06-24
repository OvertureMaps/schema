"""Tests for constraint_expressions — constraint type to Column translation."""

import struct

from overture.schema.pyspark.expressions.constraint_expressions import (
    check_array_max_length,
    check_array_min_length,
    check_bbox_completeness,
    check_bbox_lat_ordering,
    check_bbox_lat_range,
    check_bounds,
    check_email,
    check_enum,
    check_forbid_if,
    check_geometry_type,
    check_json_pointer,
    check_linear_range_bounds,
    check_linear_range_length,
    check_linear_range_order,
    check_min_fields_set,
    check_pattern,
    check_radio_group,
    check_require_any_of,
    check_require_if,
    check_required,
    check_string_max_length,
    check_string_min_length,
    check_stripped,
    check_url_format,
    check_url_length,
)
from overture.schema.system.primitive import GeometryType
from pyspark.sql import Row, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StructField, StructType
from shapely.geometry import LineString, MultiPolygon, Point, Polygon


def test_check_bounds_ge_le_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val=5)])
    result = df.select(check_bounds(F.col("val"), ge=1, le=10).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_bounds_ge_violation(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val=0)])
    result = df.select(check_bounds(F.col("val"), ge=1).alias("err")).collect()
    assert result[0]["err"] is not None
    assert ">= 1" in result[0]["err"]


def test_check_bounds_gt_violation(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val=0)])
    result = df.select(check_bounds(F.col("val"), gt=0).alias("err")).collect()
    assert result[0]["err"] is not None
    assert "> 0" in result[0]["err"]


def test_check_bounds_le_violation(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val=100)])
    result = df.select(check_bounds(F.col("val"), le=50).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_bounds_null_passthrough(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val=None)], schema="val int")
    result = df.select(check_bounds(F.col("val"), ge=1).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_bounds_nan_lower_bound_violation(spark: SparkSession) -> None:
    """NaN satisfies no Pydantic bound, but Spark sorts NaN above all values,
    so a lower bound (NaN < v) never fires. check_bounds must reject it."""
    df = spark.createDataFrame([Row(val=float("nan"))], schema="val double")
    result = df.select(check_bounds(F.col("val"), ge=0).alias("err")).collect()
    assert result[0]["err"] is not None
    assert "NaN" in result[0]["err"]


def test_check_bounds_nan_gt_violation(spark: SparkSession) -> None:
    """Same lower-bound leak as ge, via the strict-greater comparison."""
    df = spark.createDataFrame([Row(val=float("nan"))], schema="val double")
    result = df.select(check_bounds(F.col("val"), gt=0).alias("err")).collect()
    assert result[0]["err"] is not None
    assert "NaN" in result[0]["err"]


def test_check_bounds_nan_upper_bound_violation(spark: SparkSession) -> None:
    """An upper bound already rejects NaN in Spark (NaN > v is true); the
    explicit NaN check keeps that behavior."""
    df = spark.createDataFrame([Row(val=float("nan"))], schema="val double")
    result = df.select(check_bounds(F.col("val"), le=1).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_bounds_nan_no_bounds_passes(spark: SparkSession) -> None:
    """With no bounds there is nothing to violate; NaN passes, matching
    Pydantic's allow_inf_nan default for unconstrained floats."""
    df = spark.createDataFrame([Row(val=float("nan"))], schema="val double")
    result = df.select(check_bounds(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_bounds_valid_float_passes(spark: SparkSession) -> None:
    """A finite in-range float is unaffected by the NaN guard."""
    df = spark.createDataFrame([Row(val=0.5)], schema="val double")
    result = df.select(check_bounds(F.col("val"), ge=0, le=1).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_enum_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="road")])
    result = df.select(
        check_enum(F.col("val"), ["road", "rail", "water"]).alias("err")
    ).collect()
    assert result[0]["err"] is None


def test_check_enum_invalid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="sky")])
    result = df.select(
        check_enum(F.col("val"), ["road", "rail", "water"]).alias("err")
    ).collect()
    assert result[0]["err"] is not None
    assert "sky" in result[0]["err"]


class TestCheckPattern:
    def test_valid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("AB",)], ["v"])
        result = df.select(
            check_pattern(F.col("v"), r"^[A-Z]{2}$", label="test pattern").alias("e")
        )
        assert result.collect()[0]["e"] is None

    def test_invalid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("abc",)], ["v"])
        result = df.select(
            check_pattern(F.col("v"), r"^[A-Z]{2}$", label="test pattern").alias("e")
        )
        err = result.collect()[0]["e"]
        assert "invalid test pattern" in err
        assert "abc" in err

    def test_null_passes(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([(None,)], schema="v string")
        result = df.select(
            check_pattern(F.col("v"), r"^[A-Z]{2}$", label="test pattern").alias("e")
        )
        assert result.collect()[0]["e"] is None


class TestCheckMinLength:
    def test_at_limit(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(items=["a", "b"])], schema="items array<string>"
        )
        result = df.select(
            check_array_min_length(F.col("items"), 2).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_below_limit(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(items=["a"])], schema="items array<string>")
        result = df.select(
            check_array_min_length(F.col("items"), 2).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "minimum length 2" in result[0]["err"]

    def test_null_passthrough(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(items=None)], schema="items array<string>")
        result = df.select(
            check_array_min_length(F.col("items"), 2).alias("err")
        ).collect()
        assert result[0]["err"] is None


class TestCheckMaxLength:
    def test_within_limit(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(items=["a", "b"])], schema="items array<string>"
        )
        result = df.select(
            check_array_max_length(F.col("items"), 3).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_at_limit(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(items=["a", "b"])], schema="items array<string>"
        )
        result = df.select(
            check_array_max_length(F.col("items"), 2).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_exceeds_limit(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(items=["a", "b", "c"])], schema="items array<string>"
        )
        result = df.select(
            check_array_max_length(F.col("items"), 2).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "maximum length 2" in result[0]["err"]

    def test_null_passthrough(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(items=None)], schema="items array<string>")
        result = df.select(
            check_array_max_length(F.col("items"), 2).alias("err")
        ).collect()
        assert result[0]["err"] is None


def test_check_require_any_of_satisfied(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(a=1, b=None)], schema="a int, b int")
    result = df.select(
        check_require_any_of([F.col("a"), F.col("b")], ["a", "b"]).alias("err")
    ).collect()
    assert result[0]["err"] is None


def test_check_require_any_of_all_null(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(a=None, b=None)], schema="a int, b int")
    result = df.select(
        check_require_any_of([F.col("a"), F.col("b")], ["a", "b"]).alias("err")
    ).collect()
    assert result[0]["err"] is not None
    assert "a" in result[0]["err"]
    assert "b" in result[0]["err"]


class TestCheckRequireIf:
    def test_required_present(self, spark: SparkSession) -> None:
        """Target is present when condition is true -> no error."""
        df = spark.createDataFrame(
            [("road", "primary")], schema="subtype string, road_class string"
        )
        result = df.select(
            check_require_if(
                F.col("road_class"),
                F.col("subtype").isin(["road", "rail"]),
                "subtype in [road, rail]",
            ).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_required_absent(self, spark: SparkSession) -> None:
        """Target is null when condition is true -> error."""
        df = spark.createDataFrame(
            [("road", None)], schema="subtype string, road_class string"
        )
        result = df.select(
            check_require_if(
                F.col("road_class"),
                F.col("subtype").isin(["road", "rail"]),
                "subtype in [road, rail]",
            ).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "required" in result[0]["err"]

    def test_condition_false_skips(self, spark: SparkSession) -> None:
        """Target is null but condition is false -> no error."""
        df = spark.createDataFrame(
            [("water", None)], schema="subtype string, road_class string"
        )
        result = df.select(
            check_require_if(
                F.col("road_class"),
                F.col("subtype").isin(["road", "rail"]),
                "subtype in [road, rail]",
            ).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_with_value_cols(self, spark: SparkSession) -> None:
        """Error message includes actual discriminator value."""
        df = spark.createDataFrame(
            [("road", None)], schema="subtype string, road_class string"
        )
        result = df.select(
            check_require_if(
                F.col("road_class"),
                F.col("subtype").isin(["road", "rail"]),
                "subtype in [road, rail]",
                F.col("subtype"),
            ).alias("err")
        ).collect()
        assert "road" in result[0]["err"]


class TestCheckForbidIf:
    def test_forbidden_absent(self, spark: SparkSession) -> None:
        """Target is null when condition is true -> no error."""
        df = spark.createDataFrame(
            [Row(subtype="country", parent=None)],
            schema="subtype string, parent string",
        )
        result = df.select(
            check_forbid_if(
                F.col("parent"),
                F.col("subtype") == "country",
                "subtype = country",
            ).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_forbidden_present(self, spark: SparkSession) -> None:
        """Target is present when condition is true -> error."""
        df = spark.createDataFrame([Row(subtype="country", parent="abc")])
        result = df.select(
            check_forbid_if(
                F.col("parent"),
                F.col("subtype") == "country",
                "subtype = country",
            ).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "forbidden" in result[0]["err"]

    def test_condition_false_skips(self, spark: SparkSession) -> None:
        """Target is present but condition is false -> no error."""
        df = spark.createDataFrame([Row(subtype="region", parent="abc")])
        result = df.select(
            check_forbid_if(
                F.col("parent"),
                F.col("subtype") == "country",
                "subtype = country",
            ).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_with_value_cols(self, spark: SparkSession) -> None:
        """Error message includes actual discriminator value."""
        df = spark.createDataFrame([Row(subtype="country", parent="abc")])
        result = df.select(
            check_forbid_if(
                F.col("parent"),
                F.col("subtype") == "country",
                "subtype = country",
                F.col("subtype"),
            ).alias("err")
        ).collect()
        assert "country" in result[0]["err"]


class TestCheckStringMinLength:
    def test_valid_length(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="abc")])
        result = df.select(
            check_string_min_length(F.col("val"), 1).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_empty_string_violation(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="")])
        result = df.select(
            check_string_min_length(F.col("val"), 1).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "minimum length" in result[0]["err"]

    def test_null_passthrough(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val=None)], schema="val string")
        result = df.select(
            check_string_min_length(F.col("val"), 1).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_exact_min_length(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="ab")])
        result = df.select(
            check_string_min_length(F.col("val"), 2).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_below_min_length(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="a")])
        result = df.select(
            check_string_min_length(F.col("val"), 2).alias("err")
        ).collect()
        assert result[0]["err"] is not None


class TestCheckStringMaxLength:
    def test_valid_length(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="abc")])
        result = df.select(
            check_string_max_length(F.col("val"), 5).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_above_max_length(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="abcdef")])
        result = df.select(
            check_string_max_length(F.col("val"), 5).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "maximum length" in result[0]["err"]

    def test_null_passthrough(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val=None)], schema="val string")
        result = df.select(
            check_string_max_length(F.col("val"), 5).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_exact_max_length(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="abcde")])
        result = df.select(
            check_string_max_length(F.col("val"), 5).alias("err")
        ).collect()
        assert result[0]["err"] is None


class TestCheckRadioGroup:
    def test_exactly_one_true(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(is_land=True, is_territorial=False)])
        result = df.select(
            check_radio_group(
                [F.col("is_land"), F.col("is_territorial")],
                ["is_land", "is_territorial"],
            ).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_none_true(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(is_land=False, is_territorial=False)])
        result = df.select(
            check_radio_group(
                [F.col("is_land"), F.col("is_territorial")],
                ["is_land", "is_territorial"],
            ).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "exactly one" in result[0]["err"]
        assert "0" in result[0]["err"]

    def test_both_true(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(is_land=True, is_territorial=True)])
        result = df.select(
            check_radio_group(
                [F.col("is_land"), F.col("is_territorial")],
                ["is_land", "is_territorial"],
            ).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "2" in result[0]["err"]

    def test_null_treated_as_false(self, spark: SparkSession) -> None:
        """Null booleans count as not-true (0 toward the count)."""
        df = spark.createDataFrame(
            [Row(is_land=True, is_territorial=None)],
            schema="is_land boolean, is_territorial boolean",
        )
        result = df.select(
            check_radio_group(
                [F.col("is_land"), F.col("is_territorial")],
                ["is_land", "is_territorial"],
            ).alias("err")
        ).collect()
        assert result[0]["err"] is None


class TestCheckGeometryType:
    def test_point_matches(self, spark: SparkSession) -> None:
        wkb_bytes = Point(0, 0).wkb
        df = spark.createDataFrame(
            [Row(geometry=bytearray(wkb_bytes))], schema="geometry binary"
        )
        result = df.select(
            check_geometry_type(F.col("geometry"), GeometryType.POINT).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_point_rejects_linestring(self, spark: SparkSession) -> None:
        wkb_bytes = LineString([(0, 0), (1, 1)]).wkb
        df = spark.createDataFrame(
            [Row(geometry=bytearray(wkb_bytes))], schema="geometry binary"
        )
        result = df.select(
            check_geometry_type(F.col("geometry"), GeometryType.POINT).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "Point" in result[0]["err"]

    def test_multiple_allowed_types(self, spark: SparkSession) -> None:
        wkb_polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 0)]).wkb
        wkb_multi = MultiPolygon([Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])]).wkb
        df = spark.createDataFrame(
            [
                Row(geometry=bytearray(wkb_polygon)),
                Row(geometry=bytearray(wkb_multi)),
            ],
            schema="geometry binary",
        )
        result = df.select(
            check_geometry_type(
                F.col("geometry"),
                GeometryType.POLYGON,
                GeometryType.MULTI_POLYGON,
            ).alias("err")
        ).collect()
        assert all(r["err"] is None for r in result)

    def test_multiple_allowed_rejects_wrong_type(self, spark: SparkSession) -> None:
        wkb_point = Point(0, 0).wkb
        df = spark.createDataFrame(
            [Row(geometry=bytearray(wkb_point))], schema="geometry binary"
        )
        result = df.select(
            check_geometry_type(
                F.col("geometry"),
                GeometryType.POLYGON,
                GeometryType.MULTI_POLYGON,
            ).alias("err")
        ).collect()
        assert result[0]["err"] is not None

    def test_null_passthrough(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(geometry=None)], schema="geometry binary")
        result = df.select(
            check_geometry_type(F.col("geometry"), GeometryType.POINT).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_big_endian_wkb(self, spark: SparkSession) -> None:
        """Verify BE byte order handling.

        Shapely writes LE by default. Construct BE WKB for a Point
        manually: byte_order=0x00, type=0x00000001, x=0.0, y=0.0.
        """
        be_point = struct.pack(">bIdd", 0, 1, 0.0, 0.0)
        df = spark.createDataFrame(
            [Row(geometry=bytearray(be_point))], schema="geometry binary"
        )
        result = df.select(
            check_geometry_type(F.col("geometry"), GeometryType.POINT).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_iso_wkb_z_point_accepted(self, spark: SparkSession) -> None:
        """ISO WKB encodes Z by offsetting the type (PointZ=1001), shifting
        the low byte to 0xE9. GeoParquet mandates ISO WKB, so 3D geometries
        reach the check this way and must still validate by base type."""
        iso_point_z = struct.pack("<bIddd", 1, 1001, 0.0, 0.0, 5.0)
        df = spark.createDataFrame(
            [Row(geometry=bytearray(iso_point_z))], schema="geometry binary"
        )
        result = df.select(
            check_geometry_type(F.col("geometry"), GeometryType.POINT).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_iso_wkb_z_point_big_endian_accepted(self, spark: SparkSession) -> None:
        iso_point_z_be = struct.pack(">bIddd", 0, 1001, 0.0, 0.0, 5.0)
        df = spark.createDataFrame(
            [Row(geometry=bytearray(iso_point_z_be))], schema="geometry binary"
        )
        result = df.select(
            check_geometry_type(F.col("geometry"), GeometryType.POINT).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_ewkb_z_point_accepted(self, spark: SparkSession) -> None:
        """EWKB encodes Z as a high flag bit (0x80000001), leaving the low
        byte at 0x01 -- shapely's `.wkb` default. Must keep validating."""
        ewkb_point_z = struct.pack("<bIddd", 1, 0x80000001, 0.0, 0.0, 5.0)
        df = spark.createDataFrame(
            [Row(geometry=bytearray(ewkb_point_z))], schema="geometry binary"
        )
        result = df.select(
            check_geometry_type(F.col("geometry"), GeometryType.POINT).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_shapely_3d_point_accepted(self, spark: SparkSession) -> None:
        """shapely's native 3D WKB output validates as POINT."""
        df = spark.createDataFrame(
            [Row(geometry=bytearray(Point(0, 0, 5).wkb))], schema="geometry binary"
        )
        result = df.select(
            check_geometry_type(F.col("geometry"), GeometryType.POINT).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_iso_wkb_z_wrong_type_rejected(self, spark: SparkSession) -> None:
        """A 3D LineString (ISO 1002) is still rejected when POINT is expected
        -- normalization strips the dimension offset, not the base type."""
        iso_linestring_z = struct.pack("<bI", 1, 1002)
        df = spark.createDataFrame(
            [Row(geometry=bytearray(iso_linestring_z))], schema="geometry binary"
        )
        result = df.select(
            check_geometry_type(F.col("geometry"), GeometryType.POINT).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "Point" in result[0]["err"]


class TestCheckStripped:
    def test_clean_string(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="hello world")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is None

    def test_single_char(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="x")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is None

    def test_leading_space(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val=" hello")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is not None
        assert "whitespace" in result[0]["err"]

    def test_trailing_space(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="hello ")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is not None
        assert "whitespace" in result[0]["err"]

    def test_leading_tab(self, spark: SparkSession) -> None:
        """Tab is Unicode whitespace -- must be caught (not just ASCII space)."""
        df = spark.createDataFrame([Row(val="\thello")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is not None

    def test_trailing_newline(self, spark: SparkSession) -> None:
        """Trailing newline requires \\z anchor -- $ matches before it in Java regex."""
        df = spark.createDataFrame([Row(val="hello\n")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is not None

    def test_null_passthrough(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val=None)], schema="val string")
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is None

    def test_empty_string(self, spark: SparkSession) -> None:
        """Empty string has no leading/trailing whitespace -- passes."""
        df = spark.createDataFrame([Row(val="")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is None

    def test_trailing_unit_separator(self, spark: SparkSession) -> None:
        """U+001F (unit separator) -- Python strips it, Java \\S with (?U) does not."""
        df = spark.createDataFrame([Row(val="Main St \x1f")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is not None

    def test_leading_file_separator(self, spark: SparkSession) -> None:
        """U+001C (file separator) -- C0 control char Python treats as whitespace."""
        df = spark.createDataFrame([Row(val="\x1chello")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is not None

    def test_trailing_soh(self, spark: SparkSession) -> None:
        """U+0001 (SOH) -- C0 control char that even Python's strip() misses."""
        df = spark.createDataFrame([Row(val="hello\x01")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is not None

    def test_trailing_del(self, spark: SparkSession) -> None:
        """U+007F (DEL) -- control char outside C0 range."""
        df = spark.createDataFrame([Row(val="hello\x7f")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is not None

    def test_trailing_c1_control(self, spark: SparkSession) -> None:
        """U+009F (APC) -- C1 control char."""
        df = spark.createDataFrame([Row(val="hello\x9f")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is not None

    def test_control_char_in_middle_passes(self, spark: SparkSession) -> None:
        """Control chars in the middle of a string are not a stripped concern."""
        df = spark.createDataFrame([Row(val="hel\x1flo")])
        result = df.select(check_stripped(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is None


class TestCheckJsonPointer:
    def test_valid_pointer(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="/properties/name")])
        result = df.select(check_json_pointer(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is None

    def test_root_pointer(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="/")])
        result = df.select(check_json_pointer(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is None

    def test_empty_string_valid(self, spark: SparkSession) -> None:
        """Empty string is valid per RFC 6901 (references whole document)."""
        df = spark.createDataFrame([Row(val="")])
        result = df.select(check_json_pointer(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is None

    def test_missing_leading_slash(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val="properties/name")])
        result = df.select(check_json_pointer(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is not None
        assert "JSON pointer" in result[0]["err"]
        assert "properties/name" in result[0]["err"]

    def test_null_passthrough(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(val=None)], schema="val string")
        result = df.select(check_json_pointer(F.col("val")).alias("err")).collect()
        assert result[0]["err"] is None


class TestCheckLinearRangeLength:
    def test_valid_length(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(between=[0.0, 1.0])], schema="between array<double>"
        )
        result = df.select(
            check_linear_range_length(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_wrong_length_one(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(between=[0.5])], schema="between array<double>")
        result = df.select(
            check_linear_range_length(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "2 elements" in result[0]["err"]

    def test_wrong_length_three(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(between=[0.0, 0.5, 1.0])], schema="between array<double>"
        )
        result = df.select(
            check_linear_range_length(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "2 elements" in result[0]["err"]

    def test_empty_array(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(between=[])], schema="between array<double>")
        result = df.select(
            check_linear_range_length(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "2 elements" in result[0]["err"]

    def test_null_passthrough(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(between=None)], schema="between array<double>")
        result = df.select(
            check_linear_range_length(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is None


class TestCheckLinearRangeBounds:
    def test_valid_bounds(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(between=[0.2, 0.8])], schema="between array<double>"
        )
        result = df.select(
            check_linear_range_bounds(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_value_below_zero(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(between=[-0.1, 0.5])], schema="between array<double>"
        )
        result = df.select(
            check_linear_range_bounds(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "[0.0, 1.0]" in result[0]["err"]

    def test_value_above_one(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(between=[0.0, 1.1])], schema="between array<double>"
        )
        result = df.select(
            check_linear_range_bounds(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "[0.0, 1.0]" in result[0]["err"]

    def test_wrong_length_passthrough(self, spark: SparkSession) -> None:
        """Wrong-length arrays are not this function's concern."""
        df = spark.createDataFrame([Row(between=[0.5])], schema="between array<double>")
        result = df.select(
            check_linear_range_bounds(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_null_passthrough(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(between=None)], schema="between array<double>")
        result = df.select(
            check_linear_range_bounds(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is None


class TestCheckLinearRangeOrder:
    def test_valid_order(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(between=[0.2, 0.8])], schema="between array<double>"
        )
        result = df.select(
            check_linear_range_order(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_start_equals_end(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(between=[0.5, 0.5])], schema="between array<double>"
        )
        result = df.select(
            check_linear_range_order(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "start must be < end" in result[0]["err"]

    def test_start_after_end(self, spark: SparkSession) -> None:
        df = spark.createDataFrame(
            [Row(between=[0.8, 0.2])], schema="between array<double>"
        )
        result = df.select(
            check_linear_range_order(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is not None
        assert "start must be < end" in result[0]["err"]

    def test_wrong_length_passthrough(self, spark: SparkSession) -> None:
        """Wrong-length arrays are not this function's concern."""
        df = spark.createDataFrame([Row(between=[0.5])], schema="between array<double>")
        result = df.select(
            check_linear_range_order(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_null_passthrough(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([Row(between=None)], schema="between array<double>")
        result = df.select(
            check_linear_range_order(F.col("between")).alias("err")
        ).collect()
        assert result[0]["err"] is None


def test_check_required_null_is_error(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val=None)], schema="val string")
    result = df.select(check_required(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None
    assert "missing" in result[0]["err"]


def test_check_required_non_null_passes(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="hello")])
    result = df.select(check_required(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_required_composes_with_enum(spark: SparkSession) -> None:
    """check_required + check_enum via F.coalesce catches both null and invalid."""
    df = spark.createDataFrame([Row(val=None)], schema="val string")
    expr = F.coalesce(
        check_required(F.col("val")),
        check_enum(F.col("val"), ["a", "b"]),
    )
    result = df.select(expr.alias("err")).collect()
    assert result[0]["err"] is not None
    assert "missing" in result[0]["err"]


_COUNTRY_CODE_PATTERN = r"^[A-Z]{2}\z"
_COUNTRY_CODE_LABEL = "ISO 3166-1 alpha-2 country code"


class TestCheckCountryCodeViaPattern:
    """Country code validation through check_pattern with label."""

    def test_valid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("US",)], ["v"])
        result = df.select(
            check_pattern(
                F.col("v"), _COUNTRY_CODE_PATTERN, label=_COUNTRY_CODE_LABEL
            ).alias("e")
        )
        assert result.collect()[0]["e"] is None

    def test_lowercase_invalid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("us",)], ["v"])
        result = df.select(
            check_pattern(
                F.col("v"), _COUNTRY_CODE_PATTERN, label=_COUNTRY_CODE_LABEL
            ).alias("e")
        )
        err = result.collect()[0]["e"]
        assert f"invalid {_COUNTRY_CODE_LABEL}" in err
        assert "us" in err

    def test_three_chars_invalid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("USA",)], ["v"])
        result = df.select(
            check_pattern(
                F.col("v"), _COUNTRY_CODE_PATTERN, label=_COUNTRY_CODE_LABEL
            ).alias("e")
        )
        assert result.collect()[0]["e"] is not None

    def test_null_passes(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([(None,)], schema="v string")
        result = df.select(
            check_pattern(
                F.col("v"), _COUNTRY_CODE_PATTERN, label=_COUNTRY_CODE_LABEL
            ).alias("e")
        )
        assert result.collect()[0]["e"] is None


_REGION_CODE_PATTERN = r"^[A-Z]{2}-[A-Z0-9]{1,3}\z"
_REGION_CODE_LABEL = "ISO 3166-2 subdivision code"


class TestCheckRegionCodeViaPattern:
    """Region code validation through check_pattern with label."""

    def test_valid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("US-NY",)], ["v"])
        result = df.select(
            check_pattern(
                F.col("v"), _REGION_CODE_PATTERN, label=_REGION_CODE_LABEL
            ).alias("e")
        )
        assert result.collect()[0]["e"] is None

    def test_valid_numeric(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("CN-11",)], ["v"])
        result = df.select(
            check_pattern(
                F.col("v"), _REGION_CODE_PATTERN, label=_REGION_CODE_LABEL
            ).alias("e")
        )
        assert result.collect()[0]["e"] is None

    def test_no_dash_invalid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("USNY",)], ["v"])
        result = df.select(
            check_pattern(
                F.col("v"), _REGION_CODE_PATTERN, label=_REGION_CODE_LABEL
            ).alias("e")
        )
        err = result.collect()[0]["e"]
        assert f"invalid {_REGION_CODE_LABEL}" in err
        assert "USNY" in err

    def test_null_passes(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([(None,)], schema="v string")
        result = df.select(
            check_pattern(
                F.col("v"), _REGION_CODE_PATTERN, label=_REGION_CODE_LABEL
            ).alias("e")
        )
        assert result.collect()[0]["e"] is None


_SNAKE_CASE_PATTERN = r"^[a-z0-9]+(_[a-z0-9]+)*\z"
_SNAKE_CASE_LABEL = "Category in snake_case format"


class TestCheckSnakeCaseViaPattern:
    """Snake_case validation through check_pattern with label."""

    def test_valid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("hello_world",)], ["v"])
        result = df.select(
            check_pattern(
                F.col("v"), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL
            ).alias("e")
        )
        assert result.collect()[0]["e"] is None

    def test_single_word(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("hello",)], ["v"])
        result = df.select(
            check_pattern(
                F.col("v"), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL
            ).alias("e")
        )
        assert result.collect()[0]["e"] is None

    def test_with_numbers(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("hello_123",)], ["v"])
        result = df.select(
            check_pattern(
                F.col("v"), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL
            ).alias("e")
        )
        assert result.collect()[0]["e"] is None

    def test_uppercase_invalid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("Hello_World",)], ["v"])
        result = df.select(
            check_pattern(
                F.col("v"), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL
            ).alias("e")
        )
        err = result.collect()[0]["e"]
        assert f"invalid {_SNAKE_CASE_LABEL}" in err

    def test_spaces_invalid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("hello world",)], ["v"])
        result = df.select(
            check_pattern(
                F.col("v"), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL
            ).alias("e")
        )
        assert result.collect()[0]["e"] is not None

    def test_null_passes(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([(None,)], schema="v string")
        result = df.select(
            check_pattern(
                F.col("v"), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL
            ).alias("e")
        )
        assert result.collect()[0]["e"] is None


def test_check_url_format_http_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="http://example.com")])
    result = df.select(check_url_format(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_url_format_https_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="https://example.com/path?q=1")])
    result = df.select(check_url_format(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_url_format_uppercase_scheme_valid(spark: SparkSession) -> None:
    """Pydantic HttpUrl lowercases the scheme, so HTTP:// is accepted."""
    df = spark.createDataFrame([Row(val="HTTP://example.com")])
    result = df.select(check_url_format(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_url_format_mixed_case_scheme_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="HtTpS://example.com/path")])
    result = df.select(check_url_format(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_url_format_no_scheme_invalid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="example.com")])
    result = df.select(check_url_format(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_url_format_ftp_scheme_invalid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="ftp://example.com")])
    result = df.select(check_url_format(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_url_format_null_passes(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val=None)], schema="val string")
    result = df.select(check_url_format(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_url_length_exceeds_2083_chars_invalid(spark: SparkSession) -> None:
    long_url = "https://example.com/" + "a" * 2064  # 2084 chars
    df = spark.createDataFrame([Row(val=long_url)])
    result = df.select(check_url_length(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_url_length_exactly_2083_chars_valid(spark: SparkSession) -> None:
    url = "https://example.com/" + "a" * 2063  # 2083 chars
    df = spark.createDataFrame([Row(val=url)])
    result = df.select(check_url_length(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_url_length_null_passes(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val=None)], schema="val string")
    result = df.select(check_url_length(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_email_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="user@example.com")])
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_email_no_at_invalid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="userexample.com")])
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_email_no_domain_invalid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="user@")])
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_email_spaces_invalid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="user @example.com")])
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_email_null_passes(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val=None)], schema="val string")
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_email_trailing_period_invalid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="user@example.com.")])
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_email_leading_period_invalid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val=".user@example.com")])
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_email_period_before_at_invalid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="user.@example.com")])
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_email_period_after_at_invalid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="user@.example.com")])
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_email_double_period_domain_invalid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="user@example..com")])
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_email_dotted_local_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="user.name@example.com")])
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_email_subdomain_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="user@mail.example.co.uk")])
    result = df.select(check_email(F.col("val")).alias("err")).collect()
    assert result[0]["err"] is None


_PHONE_PATTERN = r"^\+\d{1,3}[\s\-\(\)0-9]+\z"
_PHONE_LABEL = "International phone number (+ followed by country code and number)"


class TestCheckPhoneViaPattern:
    """Phone number validation through check_pattern with label."""

    def test_valid_us(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("+1 555-555-5555",)], ["v"])
        result = df.select(
            check_pattern(F.col("v"), _PHONE_PATTERN, label=_PHONE_LABEL).alias("e")
        )
        assert result.collect()[0]["e"] is None

    def test_valid_international(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("+44 20 7946 0958",)], ["v"])
        result = df.select(
            check_pattern(F.col("v"), _PHONE_PATTERN, label=_PHONE_LABEL).alias("e")
        )
        assert result.collect()[0]["e"] is None

    def test_no_plus_invalid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("555-555-5555",)], ["v"])
        result = df.select(
            check_pattern(F.col("v"), _PHONE_PATTERN, label=_PHONE_LABEL).alias("e")
        )
        err = result.collect()[0]["e"]
        assert f"invalid {_PHONE_LABEL}" in err

    def test_letters_invalid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("+1 abc-defg",)], ["v"])
        result = df.select(
            check_pattern(F.col("v"), _PHONE_PATTERN, label=_PHONE_LABEL).alias("e")
        )
        assert result.collect()[0]["e"] is not None

    def test_null_passes(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([(None,)], schema="v string")
        result = df.select(
            check_pattern(F.col("v"), _PHONE_PATTERN, label=_PHONE_LABEL).alias("e")
        )
        assert result.collect()[0]["e"] is None


_WIKIDATA_PATTERN = r"^Q\d+\z"
_WIKIDATA_LABEL = "Wikidata identifier (Q followed by digits)"


class TestCheckWikidataIdViaPattern:
    """Wikidata ID validation through check_pattern with label."""

    def test_valid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("Q42",)], ["v"])
        result = df.select(
            check_pattern(F.col("v"), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL).alias(
                "e"
            )
        )
        assert result.collect()[0]["e"] is None

    def test_large_number(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("Q123456789",)], ["v"])
        result = df.select(
            check_pattern(F.col("v"), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL).alias(
                "e"
            )
        )
        assert result.collect()[0]["e"] is None

    def test_lowercase_q_invalid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("q42",)], ["v"])
        result = df.select(
            check_pattern(F.col("v"), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL).alias(
                "e"
            )
        )
        err = result.collect()[0]["e"]
        assert f"invalid {_WIKIDATA_LABEL}" in err

    def test_no_digits_invalid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("Q",)], ["v"])
        result = df.select(
            check_pattern(F.col("v"), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL).alias(
                "e"
            )
        )
        assert result.collect()[0]["e"] is not None

    def test_p_prefix_invalid(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([("P42",)], ["v"])
        result = df.select(
            check_pattern(F.col("v"), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL).alias(
                "e"
            )
        )
        assert result.collect()[0]["e"] is not None

    def test_null_passes(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([(None,)], schema="v string")
        result = df.select(
            check_pattern(F.col("v"), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL).alias(
                "e"
            )
        )
        assert result.collect()[0]["e"] is None


class TestCheckMinFieldsSet:
    def test_meets_threshold(self, spark: SparkSession) -> None:
        """Count at threshold -> no error."""
        df = spark.createDataFrame(
            [Row(a=1, b=2, c=None)], schema="a int, b int, c int"
        )
        result = df.select(
            check_min_fields_set(
                [F.col("a"), F.col("b"), F.col("c")],
                ["a", "b", "c"],
                2,
            ).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_exceeds_threshold(self, spark: SparkSession) -> None:
        """Count above threshold -> no error."""
        df = spark.createDataFrame([Row(a=1, b=2, c=3)], schema="a int, b int, c int")
        result = df.select(
            check_min_fields_set(
                [F.col("a"), F.col("b"), F.col("c")],
                ["a", "b", "c"],
                2,
            ).alias("err")
        ).collect()
        assert result[0]["err"] is None

    def test_below_threshold(self, spark: SparkSession) -> None:
        """Count below threshold -> error with field names and actual count."""
        df = spark.createDataFrame(
            [Row(a=1, b=None, c=None)], schema="a int, b int, c int"
        )
        result = df.select(
            check_min_fields_set(
                [F.col("a"), F.col("b"), F.col("c")],
                ["a", "b", "c"],
                2,
            ).alias("err")
        ).collect()
        err = result[0]["err"]
        assert err is not None
        assert "at least 2" in err
        assert "a, b, c" in err
        assert "1" in err

    def test_all_null_below_threshold(self, spark: SparkSession) -> None:
        """All null -> error showing 0 non-null."""
        df = spark.createDataFrame([Row(a=None, b=None)], schema="a int, b int")
        result = df.select(
            check_min_fields_set(
                [F.col("a"), F.col("b")],
                ["a", "b"],
                1,
            ).alias("err")
        ).collect()
        err = result[0]["err"]
        assert err is not None
        assert "0" in err

    def test_error_message_format(self, spark: SparkSession) -> None:
        """Error message matches expected format exactly."""
        df = spark.createDataFrame([Row(x=None, y=None)], schema="x int, y int")
        result = df.select(
            check_min_fields_set(
                [F.col("x"), F.col("y")],
                ["x", "y"],
                1,
            ).alias("err")
        ).collect()
        err = result[0]["err"]
        assert err == "at least 1 of x, y required, got 0 non-null"


_BBOX_SCHEMA = StructType(
    [
        StructField(
            "bbox",
            StructType(
                [
                    StructField("xmin", DoubleType(), True),
                    StructField("xmax", DoubleType(), True),
                    StructField("ymin", DoubleType(), True),
                    StructField("ymax", DoubleType(), True),
                ]
            ),
            True,
        ),
    ]
)


def test_check_bbox_completeness_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(bbox=Row(xmin=0.0, xmax=1.0, ymin=0.0, ymax=1.0))],
        schema=_BBOX_SCHEMA,
    )
    result = df.select(check_bbox_completeness(F.col("bbox")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_bbox_completeness_null_bbox_passes(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(bbox=None)], schema=_BBOX_SCHEMA)
    result = df.select(check_bbox_completeness(F.col("bbox")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_bbox_completeness_null_subfield_fails(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(bbox=Row(xmin=None, xmax=1.0, ymin=0.0, ymax=1.0))],
        schema=_BBOX_SCHEMA,
    )
    result = df.select(check_bbox_completeness(F.col("bbox")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_bbox_lat_ordering_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(bbox=Row(xmin=0.0, xmax=1.0, ymin=-10.0, ymax=10.0))],
        schema=_BBOX_SCHEMA,
    )
    result = df.select(check_bbox_lat_ordering(F.col("bbox")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_bbox_lat_ordering_equal_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(bbox=Row(xmin=0.0, xmax=1.0, ymin=5.0, ymax=5.0))],
        schema=_BBOX_SCHEMA,
    )
    result = df.select(check_bbox_lat_ordering(F.col("bbox")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_bbox_lat_ordering_inverted_fails(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(bbox=Row(xmin=0.0, xmax=1.0, ymin=10.0, ymax=-10.0))],
        schema=_BBOX_SCHEMA,
    )
    result = df.select(check_bbox_lat_ordering(F.col("bbox")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_bbox_lat_ordering_null_bbox_passes(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(bbox=None)], schema=_BBOX_SCHEMA)
    result = df.select(check_bbox_lat_ordering(F.col("bbox")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_bbox_lat_range_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(bbox=Row(xmin=0.0, xmax=1.0, ymin=-90.0, ymax=90.0))],
        schema=_BBOX_SCHEMA,
    )
    result = df.select(check_bbox_lat_range(F.col("bbox")).alias("err")).collect()
    assert result[0]["err"] is None


def test_check_bbox_lat_range_ymin_below_fails(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(bbox=Row(xmin=0.0, xmax=1.0, ymin=-91.0, ymax=1.0))],
        schema=_BBOX_SCHEMA,
    )
    result = df.select(check_bbox_lat_range(F.col("bbox")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_bbox_lat_range_ymax_above_fails(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(bbox=Row(xmin=0.0, xmax=1.0, ymin=0.0, ymax=91.0))],
        schema=_BBOX_SCHEMA,
    )
    result = df.select(check_bbox_lat_range(F.col("bbox")).alias("err")).collect()
    assert result[0]["err"] is not None


def test_check_bbox_lat_range_null_bbox_passes(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(bbox=None)], schema=_BBOX_SCHEMA)
    result = df.select(check_bbox_lat_range(F.col("bbox")).alias("err")).collect()
    assert result[0]["err"] is None
