"""Tests for constraint_expressions -- constraint type to Column translation.

Each constraint is exercised as a `_Case`: a uniquely-named input column, the
check built over it, and a predicate on the collected result. The `results`
fixture packs every case's input into one wide single-row DataFrame, applies
every check in one `select`, and collects once -- so the whole file pays for a
single `createDataFrame` + `collect` instead of one pair per test (the same
batch-once pattern the generated conformance harness uses). Cases needing both
a violating and a clean input (or a valid/invalid pair of geometries) carry
separate entries.

Column DDL types are load-bearing: `double` vs `int` changes NaN behavior, and
multi-field checks (require_if / forbid_if / radio_group / min_fields_set) pack
their inputs into a struct column so the check can reference each field.
"""

import struct
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from overture.schema.pyspark.expressions.constraint_expressions import (
    check_array_max_length,
    check_array_min_length,
    check_bbox_completeness,
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
    check_multiple_of,
    check_pattern,
    check_radio_group,
    check_require_any_of,
    check_require_any_true,
    check_require_if,
    check_required,
    check_string_max_length,
    check_string_min_length,
    check_stripped,
    check_url_format,
    check_url_length,
    except_literals,
)
from overture.schema.system.geometric import GeometryType
from pyspark.sql import Column, SparkSession
from pyspark.sql import functions as F
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

# PySpark 3.4's collect() leaves its result socket for the GC to finalize; under
# -W error that ResourceWarning fails the batched `results` fixture. conftest's
# unraisablehook catches the finalizer path, but this fixture emits it
# synchronously -- and a filterwarnings mark is the only filter outranking the
# command-line -W error.
pytestmark = pytest.mark.filterwarnings("ignore::ResourceWarning")

# Pattern/label pairs shared between a case's check and its expect predicate.
_COUNTRY_CODE_PATTERN = r"^[A-Z]{2}\z"
_COUNTRY_CODE_LABEL = "ISO 3166-1 alpha-2 country code"
_REGION_CODE_PATTERN = r"^[A-Z]{2}-[A-Z0-9]{1,3}\z"
_REGION_CODE_LABEL = "ISO 3166-2 subdivision code"
_SNAKE_CASE_PATTERN = r"^[a-z0-9]+(_[a-z0-9]+)*\z"
_SNAKE_CASE_LABEL = "Category in snake_case format"
_PHONE_PATTERN = r"^\+\d{1,3}[\s\-\(\)0-9]+\z"
_PHONE_LABEL = "International phone number (+ followed by country code and number)"
_WIKIDATA_PATTERN = r"^Q\d+\z"
_WIKIDATA_LABEL = "Wikidata identifier (Q followed by digits)"


@dataclass(frozen=True)
class _Case:
    """One constraint_expressions assertion driven off the shared wide row.

    `check(field)` builds the constraint check over the case's input column;
    `expect(result)` is a predicate on that column's single collected value.
    """

    id: str
    ddl: str
    value: Any
    check: Callable[[str], Column]
    expect: Callable[[Any], bool]


_CASES: list[_Case] = [
    # --- except_literals: suppress an allowed literal, pass real violations ----
    # "" is an allowed literal alternative -> the url_format error is suppressed.
    _Case(
        "el_suppress",
        "string",
        "",
        lambda f: except_literals(F.col(f), check_url_format(F.col(f)), [""]),
        lambda r: r is None,
    ),
    # A non-literal invalid value still surfaces the inner check's error.
    _Case(
        "el_violation",
        "string",
        "not a url",
        lambda f: except_literals(F.col(f), check_url_format(F.col(f)), [""]),
        lambda r: r is not None,
    ),
    _Case(
        "el_valid",
        "string",
        "https://example.com/x",
        lambda f: except_literals(F.col(f), check_url_format(F.col(f)), [""]),
        lambda r: r is None,
    ),
    _Case(
        "el_null",
        "string",
        None,
        lambda f: except_literals(F.col(f), check_url_format(F.col(f)), [""]),
        lambda r: r is None,
    ),
    # --- check_multiple_of ----------------------------------------------------
    _Case(
        "multiple_of_integral_float_passes",
        "double",
        2.0,
        lambda f: check_multiple_of(F.col(f), 1),
        lambda r: r is None,
    ),
    _Case(
        "multiple_of_negative_integral_float_passes",
        "double",
        -3.0,
        lambda f: check_multiple_of(F.col(f), 1),
        lambda r: r is None,
    ),
    _Case(
        "multiple_of_fractional_float_violation",
        "double",
        2.5,
        lambda f: check_multiple_of(F.col(f), 1),
        lambda r: r is not None and "multiple of" in r,
    ),
    _Case(
        "multiple_of_null_passthrough",
        "double",
        None,
        lambda f: check_multiple_of(F.col(f), 1),
        lambda r: r is None,
    ),
    # Integral doubles beyond 2^63 are whole numbers Pydantic accepts
    # ((1e30).is_integer() is True). A floor-based check would saturate the
    # LongType cast and wrongly fire; the remainder check passes them.
    _Case(
        "multiple_of_large_integral_double_passes",
        "double",
        1e30,
        lambda f: check_multiple_of(F.col(f), 1),
        lambda r: r is None,
    ),
    _Case(
        "multiple_of_nan_violation",
        "double",
        float("nan"),
        lambda f: check_multiple_of(F.col(f), 1),
        lambda r: r is not None and "multiple of" in r,
    ),
    _Case(
        "multiple_of_positive_infinity_violation",
        "double",
        float("inf"),
        lambda f: check_multiple_of(F.col(f), 1),
        lambda r: r is not None and "multiple of" in r,
    ),
    _Case(
        "multiple_of_negative_infinity_violation",
        "double",
        float("-inf"),
        lambda f: check_multiple_of(F.col(f), 1),
        lambda r: r is not None and "multiple of" in r,
    ),
    # Divisor need not be 1: 1.5 is a multiple of 0.5, 1.75 is not.
    _Case(
        "multiple_of_non_unit_divisor_valid",
        "double",
        1.5,
        lambda f: check_multiple_of(F.col(f), 0.5),
        lambda r: r is None,
    ),
    _Case(
        "multiple_of_non_unit_divisor_violation",
        "double",
        1.75,
        lambda f: check_multiple_of(F.col(f), 0.5),
        lambda r: r is not None,
    ),
    # --- check_bounds ---------------------------------------------------------
    _Case(
        "bounds_ge_le_valid",
        "int",
        5,
        lambda f: check_bounds(F.col(f), ge=1, le=10),
        lambda r: r is None,
    ),
    _Case(
        "bounds_ge_violation",
        "int",
        0,
        lambda f: check_bounds(F.col(f), ge=1),
        lambda r: r is not None and ">= 1" in r,
    ),
    _Case(
        "bounds_gt_violation",
        "int",
        0,
        lambda f: check_bounds(F.col(f), gt=0),
        lambda r: r is not None and "> 0" in r,
    ),
    _Case(
        "bounds_le_violation",
        "int",
        100,
        lambda f: check_bounds(F.col(f), le=50),
        lambda r: r is not None,
    ),
    _Case(
        "bounds_null_passthrough",
        "int",
        None,
        lambda f: check_bounds(F.col(f), ge=1),
        lambda r: r is None,
    ),
    # NaN satisfies no Pydantic bound, but Spark sorts NaN above all values, so a
    # lower bound (NaN < v) never fires. check_bounds must reject it explicitly.
    _Case(
        "bounds_nan_ge_violation",
        "double",
        float("nan"),
        lambda f: check_bounds(F.col(f), ge=0),
        lambda r: r is not None and "NaN" in r,
    ),
    # Same lower-bound leak, via the strict-greater comparison.
    _Case(
        "bounds_nan_gt_violation",
        "double",
        float("nan"),
        lambda f: check_bounds(F.col(f), gt=0),
        lambda r: r is not None and "NaN" in r,
    ),
    # An upper bound already rejects NaN in Spark (NaN > v is true); the explicit
    # NaN check keeps that behavior.
    _Case(
        "bounds_nan_le_violation",
        "double",
        float("nan"),
        lambda f: check_bounds(F.col(f), le=1),
        lambda r: r is not None,
    ),
    # With no bounds there is nothing to violate; NaN passes, matching Pydantic's
    # allow_inf_nan default for unconstrained floats.
    _Case(
        "bounds_nan_no_bounds_passes",
        "double",
        float("nan"),
        lambda f: check_bounds(F.col(f)),
        lambda r: r is None,
    ),
    # A finite in-range float is unaffected by the NaN guard.
    _Case(
        "bounds_valid_float_passes",
        "double",
        0.5,
        lambda f: check_bounds(F.col(f), ge=0, le=1),
        lambda r: r is None,
    ),
    # With check_nan=False the NaN guard is absent; NaN slips past a lower bound.
    _Case(
        "bounds_nan_guard_off_passes",
        "double",
        float("nan"),
        lambda f: check_bounds(F.col(f), ge=0, check_nan=False),
        lambda r: r is None,
    ),
    # With check_nan=True (default) NaN is rejected even with a lower bound.
    _Case(
        "bounds_nan_guard_on_rejects",
        "double",
        float("nan"),
        lambda f: check_bounds(F.col(f), ge=0, check_nan=True),
        lambda r: r is not None and "NaN" in r,
    ),
    # check_nan=False is safe for integer columns; bound violations still fire.
    _Case(
        "bounds_int_rejects_violation",
        "int",
        0,
        lambda f: check_bounds(F.col(f), ge=1, check_nan=False),
        lambda r: r is not None,
    ),
    _Case(
        "bounds_int_accepts_valid",
        "int",
        5,
        lambda f: check_bounds(F.col(f), ge=1, le=10, check_nan=False),
        lambda r: r is None,
    ),
    # --- check_enum -----------------------------------------------------------
    _Case(
        "enum_valid",
        "string",
        "road",
        lambda f: check_enum(F.col(f), ["road", "rail", "water"]),
        lambda r: r is None,
    ),
    _Case(
        "enum_invalid",
        "string",
        "sky",
        lambda f: check_enum(F.col(f), ["road", "rail", "water"]),
        lambda r: r is not None and "sky" in r,
    ),
    # --- check_pattern (generic) ----------------------------------------------
    _Case(
        "pat_valid",
        "string",
        "AB",
        lambda f: check_pattern(F.col(f), r"^[A-Z]{2}$", label="test pattern"),
        lambda r: r is None,
    ),
    _Case(
        "pat_invalid",
        "string",
        "abc",
        lambda f: check_pattern(F.col(f), r"^[A-Z]{2}$", label="test pattern"),
        lambda r: r is not None and "invalid test pattern" in r and "abc" in r,
    ),
    _Case(
        "pat_null_passes",
        "string",
        None,
        lambda f: check_pattern(F.col(f), r"^[A-Z]{2}$", label="test pattern"),
        lambda r: r is None,
    ),
    # --- check_array_min_length -----------------------------------------------
    _Case(
        "amin_at_limit",
        "array<string>",
        ["a", "b"],
        lambda f: check_array_min_length(F.col(f), 2),
        lambda r: r is None,
    ),
    _Case(
        "amin_below_limit",
        "array<string>",
        ["a"],
        lambda f: check_array_min_length(F.col(f), 2),
        lambda r: r is not None and "minimum length 2" in r,
    ),
    _Case(
        "amin_null_passthrough",
        "array<string>",
        None,
        lambda f: check_array_min_length(F.col(f), 2),
        lambda r: r is None,
    ),
    # --- check_array_max_length -----------------------------------------------
    _Case(
        "amax_within_limit",
        "array<string>",
        ["a", "b"],
        lambda f: check_array_max_length(F.col(f), 3),
        lambda r: r is None,
    ),
    _Case(
        "amax_at_limit",
        "array<string>",
        ["a", "b"],
        lambda f: check_array_max_length(F.col(f), 2),
        lambda r: r is None,
    ),
    _Case(
        "amax_exceeds_limit",
        "array<string>",
        ["a", "b", "c"],
        lambda f: check_array_max_length(F.col(f), 2),
        lambda r: r is not None and "maximum length 2" in r,
    ),
    _Case(
        "amax_null_passthrough",
        "array<string>",
        None,
        lambda f: check_array_max_length(F.col(f), 2),
        lambda r: r is None,
    ),
    # --- check_require_any_of (multi-field -> struct column) ------------------
    _Case(
        "rao_satisfied",
        "struct<a:int,b:int>",
        {"a": 1, "b": None},
        lambda f: check_require_any_of([F.col(f)["a"], F.col(f)["b"]], ["a", "b"]),
        lambda r: r is None,
    ),
    _Case(
        "rao_all_null",
        "struct<a:int,b:int>",
        {"a": None, "b": None},
        lambda f: check_require_any_of([F.col(f)["a"], F.col(f)["b"]], ["a", "b"]),
        lambda r: r is not None and "a" in r and "b" in r,
    ),
    # --- check_require_any_true (multi-field -> struct column) ----------------
    # At least one condition true -> no error.
    _Case(
        "rat_one_true",
        "struct<is_land:boolean,is_territorial:boolean>",
        {"is_land": True, "is_territorial": False},
        lambda f: check_require_any_true(
            [
                F.col(f)["is_land"] == F.lit(True),
                F.col(f)["is_territorial"] == F.lit(True),
            ],
            ["is_land", "is_territorial"],
        ),
        lambda r: r is None,
    ),
    # No condition true -> error naming the fields.
    _Case(
        "rat_all_false",
        "struct<is_land:boolean,is_territorial:boolean>",
        {"is_land": False, "is_territorial": False},
        lambda f: check_require_any_true(
            [
                F.col(f)["is_land"] == F.lit(True),
                F.col(f)["is_territorial"] == F.lit(True),
            ],
            ["is_land", "is_territorial"],
        ),
        lambda r: r is not None and "is_land" in r and "is_territorial" in r,
    ),
    # Null fields mirror Python's `None == True` -> False: an all-null row violates.
    _Case(
        "rat_all_null",
        "struct<is_land:boolean,is_territorial:boolean>",
        {"is_land": None, "is_territorial": None},
        lambda f: check_require_any_true(
            [
                F.col(f)["is_land"] == F.lit(True),
                F.col(f)["is_territorial"] == F.lit(True),
            ],
            ["is_land", "is_territorial"],
        ),
        lambda r: r is not None,
    ),
    # --- check_require_if (multi-field -> struct column) ----------------------
    # Target present when condition true -> no error.
    _Case(
        "rif_present",
        "struct<subtype:string,road_class:string>",
        {"subtype": "road", "road_class": "primary"},
        lambda f: check_require_if(
            F.col(f)["road_class"],
            F.col(f)["subtype"].isin(["road", "rail"]),
            "subtype in [road, rail]",
        ),
        lambda r: r is None,
    ),
    # Target null when condition true -> error.
    _Case(
        "rif_absent",
        "struct<subtype:string,road_class:string>",
        {"subtype": "road", "road_class": None},
        lambda f: check_require_if(
            F.col(f)["road_class"],
            F.col(f)["subtype"].isin(["road", "rail"]),
            "subtype in [road, rail]",
        ),
        lambda r: r is not None and "required" in r,
    ),
    # Target null but condition false -> no error.
    _Case(
        "rif_condition_false",
        "struct<subtype:string,road_class:string>",
        {"subtype": "water", "road_class": None},
        lambda f: check_require_if(
            F.col(f)["road_class"],
            F.col(f)["subtype"].isin(["road", "rail"]),
            "subtype in [road, rail]",
        ),
        lambda r: r is None,
    ),
    # Error message includes the actual discriminator value.
    _Case(
        "rif_value_cols",
        "struct<subtype:string,road_class:string>",
        {"subtype": "road", "road_class": None},
        lambda f: check_require_if(
            F.col(f)["road_class"],
            F.col(f)["subtype"].isin(["road", "rail"]),
            "subtype in [road, rail]",
            F.col(f)["subtype"],
        ),
        lambda r: r is not None and "road" in r,
    ),
    # --- check_forbid_if (multi-field -> struct column) -----------------------
    # Target null when condition true -> no error.
    _Case(
        "fif_absent",
        "struct<subtype:string,parent:string>",
        {"subtype": "country", "parent": None},
        lambda f: check_forbid_if(
            F.col(f)["parent"],
            F.col(f)["subtype"] == "country",
            "subtype = country",
        ),
        lambda r: r is None,
    ),
    # Target present when condition true -> error.
    _Case(
        "fif_present",
        "struct<subtype:string,parent:string>",
        {"subtype": "country", "parent": "abc"},
        lambda f: check_forbid_if(
            F.col(f)["parent"],
            F.col(f)["subtype"] == "country",
            "subtype = country",
        ),
        lambda r: r is not None and "forbidden" in r,
    ),
    # Target present but condition false -> no error.
    _Case(
        "fif_condition_false",
        "struct<subtype:string,parent:string>",
        {"subtype": "region", "parent": "abc"},
        lambda f: check_forbid_if(
            F.col(f)["parent"],
            F.col(f)["subtype"] == "country",
            "subtype = country",
        ),
        lambda r: r is None,
    ),
    # Error message includes the actual discriminator value.
    _Case(
        "fif_value_cols",
        "struct<subtype:string,parent:string>",
        {"subtype": "country", "parent": "abc"},
        lambda f: check_forbid_if(
            F.col(f)["parent"],
            F.col(f)["subtype"] == "country",
            "subtype = country",
            F.col(f)["subtype"],
        ),
        lambda r: r is not None and "country" in r,
    ),
    # --- check_string_min_length ----------------------------------------------
    _Case(
        "smin_valid",
        "string",
        "abc",
        lambda f: check_string_min_length(F.col(f), 1),
        lambda r: r is None,
    ),
    _Case(
        "smin_empty_violation",
        "string",
        "",
        lambda f: check_string_min_length(F.col(f), 1),
        lambda r: r is not None and "minimum length" in r,
    ),
    _Case(
        "smin_null_passthrough",
        "string",
        None,
        lambda f: check_string_min_length(F.col(f), 1),
        lambda r: r is None,
    ),
    _Case(
        "smin_exact",
        "string",
        "ab",
        lambda f: check_string_min_length(F.col(f), 2),
        lambda r: r is None,
    ),
    _Case(
        "smin_below",
        "string",
        "a",
        lambda f: check_string_min_length(F.col(f), 2),
        lambda r: r is not None,
    ),
    # --- check_string_max_length ----------------------------------------------
    _Case(
        "smax_valid",
        "string",
        "abc",
        lambda f: check_string_max_length(F.col(f), 5),
        lambda r: r is None,
    ),
    _Case(
        "smax_above",
        "string",
        "abcdef",
        lambda f: check_string_max_length(F.col(f), 5),
        lambda r: r is not None and "maximum length" in r,
    ),
    _Case(
        "smax_null_passthrough",
        "string",
        None,
        lambda f: check_string_max_length(F.col(f), 5),
        lambda r: r is None,
    ),
    _Case(
        "smax_exact",
        "string",
        "abcde",
        lambda f: check_string_max_length(F.col(f), 5),
        lambda r: r is None,
    ),
    # --- check_radio_group (multi-field -> struct column) ---------------------
    _Case(
        "rg_exactly_one",
        "struct<is_land:boolean,is_territorial:boolean>",
        {"is_land": True, "is_territorial": False},
        lambda f: check_radio_group(
            [F.col(f)["is_land"], F.col(f)["is_territorial"]],
            ["is_land", "is_territorial"],
        ),
        lambda r: r is None,
    ),
    _Case(
        "rg_none_true",
        "struct<is_land:boolean,is_territorial:boolean>",
        {"is_land": False, "is_territorial": False},
        lambda f: check_radio_group(
            [F.col(f)["is_land"], F.col(f)["is_territorial"]],
            ["is_land", "is_territorial"],
        ),
        lambda r: r is not None and "exactly one" in r and "0" in r,
    ),
    _Case(
        "rg_both_true",
        "struct<is_land:boolean,is_territorial:boolean>",
        {"is_land": True, "is_territorial": True},
        lambda f: check_radio_group(
            [F.col(f)["is_land"], F.col(f)["is_territorial"]],
            ["is_land", "is_territorial"],
        ),
        lambda r: r is not None and "2" in r,
    ),
    # Null booleans count as not-true (0 toward the count).
    _Case(
        "rg_null_as_false",
        "struct<is_land:boolean,is_territorial:boolean>",
        {"is_land": True, "is_territorial": None},
        lambda f: check_radio_group(
            [F.col(f)["is_land"], F.col(f)["is_territorial"]],
            ["is_land", "is_territorial"],
        ),
        lambda r: r is None,
    ),
    # --- check_geometry_type (WKB in a binary column) -------------------------
    _Case(
        "geom_point_matches",
        "binary",
        bytearray(Point(0, 0).wkb),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is None,
    ),
    _Case(
        "geom_point_rejects_line",
        "binary",
        bytearray(LineString([(0, 0), (1, 1)]).wkb),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is not None and "Point" in r,
    ),
    # Multiple allowed types: a polygon and a multipolygon both pass (one row each).
    _Case(
        "geom_multi_polygon_ok",
        "binary",
        bytearray(Polygon([(0, 0), (1, 0), (1, 1), (0, 0)]).wkb),
        lambda f: check_geometry_type(
            F.col(f), GeometryType.POLYGON, GeometryType.MULTI_POLYGON
        ),
        lambda r: r is None,
    ),
    _Case(
        "geom_multi_multipolygon_ok",
        "binary",
        bytearray(MultiPolygon([Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])]).wkb),
        lambda f: check_geometry_type(
            F.col(f), GeometryType.POLYGON, GeometryType.MULTI_POLYGON
        ),
        lambda r: r is None,
    ),
    _Case(
        "geom_multi_rejects_point",
        "binary",
        bytearray(Point(0, 0).wkb),
        lambda f: check_geometry_type(
            F.col(f), GeometryType.POLYGON, GeometryType.MULTI_POLYGON
        ),
        lambda r: r is not None,
    ),
    _Case(
        "geom_null_passthrough",
        "binary",
        None,
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is None,
    ),
    # BE byte order: byte_order=0x00, type=0x00000001, x=0.0, y=0.0.
    _Case(
        "geom_big_endian",
        "binary",
        bytearray(struct.pack(">bIdd", 0, 1, 0.0, 0.0)),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is None,
    ),
    # ISO WKB encodes Z by offsetting the type (PointZ=1001); must validate by base type.
    _Case(
        "geom_iso_z_point",
        "binary",
        bytearray(struct.pack("<bIddd", 1, 1001, 0.0, 0.0, 5.0)),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is None,
    ),
    _Case(
        "geom_iso_z_point_be",
        "binary",
        bytearray(struct.pack(">bIddd", 0, 1001, 0.0, 0.0, 5.0)),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is None,
    ),
    # EWKB encodes Z as a high flag bit (0x80000001), leaving the low byte at 0x01.
    _Case(
        "geom_ewkb_z_point",
        "binary",
        bytearray(struct.pack("<bIddd", 1, 0x80000001, 0.0, 0.0, 5.0)),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is None,
    ),
    # shapely's native 3D WKB output validates as POINT.
    _Case(
        "geom_shapely_3d_point",
        "binary",
        bytearray(Point(0, 0, 5).wkb),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is None,
    ),
    # A 3D LineString (ISO 1002) is still rejected when POINT is expected.
    _Case(
        "geom_iso_z_wrong_type",
        "binary",
        bytearray(struct.pack("<bI", 1, 1002)),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is not None and "Point" in r,
    ),
    # A non-null WKB blob too short to contain a type word is flagged.
    _Case(
        "geom_truncated",
        "binary",
        bytearray(b"\x01"),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is not None,
    ),
    # A partial WKB header (1-4 bytes) is flagged even when conv() yields a
    # non-null type: `b"\x01\x01"` reads as type 1 (Point) and would otherwise
    # silently validate. A length gate, not a null check, closes the hole.
    _Case(
        "geom_partial_1",
        "binary",
        bytearray(b"\x01" * 1),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is not None,
    ),
    _Case(
        "geom_partial_2",
        "binary",
        bytearray(b"\x01" * 2),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is not None,
    ),
    _Case(
        "geom_partial_3",
        "binary",
        bytearray(b"\x01" * 3),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is not None,
    ),
    _Case(
        "geom_partial_4",
        "binary",
        bytearray(b"\x01" * 4),
        lambda f: check_geometry_type(F.col(f), GeometryType.POINT),
        lambda r: r is not None,
    ),
    # --- check_stripped -------------------------------------------------------
    _Case(
        "strip_clean",
        "string",
        "hello world",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "strip_single_char",
        "string",
        "x",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "strip_leading_space",
        "string",
        " hello",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is not None and "whitespace" in r,
    ),
    _Case(
        "strip_trailing_space",
        "string",
        "hello ",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is not None and "whitespace" in r,
    ),
    # Tab is Unicode whitespace -- must be caught (not just ASCII space).
    _Case(
        "strip_leading_tab",
        "string",
        "\thello",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is not None,
    ),
    # Trailing newline requires \z anchor -- $ matches before it in Java regex.
    _Case(
        "strip_trailing_newline",
        "string",
        "hello\n",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "strip_null_passthrough",
        "string",
        None,
        lambda f: check_stripped(F.col(f)),
        lambda r: r is None,
    ),
    # Empty string has no leading/trailing whitespace -- passes.
    _Case(
        "strip_empty",
        "string",
        "",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is None,
    ),
    # U+001F (unit separator) -- Python strips it, Java \S with (?U) does not.
    _Case(
        "strip_trailing_unit_sep",
        "string",
        "Main St \x1f",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is not None,
    ),
    # U+001C (file separator) -- C0 control char Python treats as whitespace.
    _Case(
        "strip_leading_file_sep",
        "string",
        "\x1chello",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is not None,
    ),
    # U+0001 (SOH) -- C0 control char that even Python's strip() misses.
    _Case(
        "strip_trailing_soh",
        "string",
        "hello\x01",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is not None,
    ),
    # U+007F (DEL) -- control char outside C0 range.
    _Case(
        "strip_trailing_del",
        "string",
        "hello\x7f",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is not None,
    ),
    # U+009F (APC) -- C1 control char.
    _Case(
        "strip_trailing_c1",
        "string",
        "hello\x9f",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is not None,
    ),
    # Control chars in the middle of a string are not a stripped concern.
    _Case(
        "strip_control_middle",
        "string",
        "hel\x1flo",
        lambda f: check_stripped(F.col(f)),
        lambda r: r is None,
    ),
    # --- check_json_pointer ---------------------------------------------------
    _Case(
        "jp_valid",
        "string",
        "/properties/name",
        lambda f: check_json_pointer(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "jp_root",
        "string",
        "/",
        lambda f: check_json_pointer(F.col(f)),
        lambda r: r is None,
    ),
    # Empty string is valid per RFC 6901 (references whole document).
    _Case(
        "jp_empty",
        "string",
        "",
        lambda f: check_json_pointer(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "jp_missing_slash",
        "string",
        "properties/name",
        lambda f: check_json_pointer(F.col(f)),
        lambda r: r is not None and "JSON pointer" in r and "properties/name" in r,
    ),
    _Case(
        "jp_null_passthrough",
        "string",
        None,
        lambda f: check_json_pointer(F.col(f)),
        lambda r: r is None,
    ),
    # --- check_linear_range_length --------------------------------------------
    _Case(
        "lrl_valid",
        "array<double>",
        [0.0, 1.0],
        lambda f: check_linear_range_length(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "lrl_one",
        "array<double>",
        [0.5],
        lambda f: check_linear_range_length(F.col(f)),
        lambda r: r is not None and "2 elements" in r,
    ),
    _Case(
        "lrl_three",
        "array<double>",
        [0.0, 0.5, 1.0],
        lambda f: check_linear_range_length(F.col(f)),
        lambda r: r is not None and "2 elements" in r,
    ),
    _Case(
        "lrl_empty",
        "array<double>",
        [],
        lambda f: check_linear_range_length(F.col(f)),
        lambda r: r is not None and "2 elements" in r,
    ),
    _Case(
        "lrl_null",
        "array<double>",
        None,
        lambda f: check_linear_range_length(F.col(f)),
        lambda r: r is None,
    ),
    # --- check_linear_range_bounds --------------------------------------------
    _Case(
        "lrb_valid",
        "array<double>",
        [0.2, 0.8],
        lambda f: check_linear_range_bounds(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "lrb_below_zero",
        "array<double>",
        [-0.1, 0.5],
        lambda f: check_linear_range_bounds(F.col(f)),
        lambda r: r is not None and "[0.0, 1.0]" in r,
    ),
    _Case(
        "lrb_above_one",
        "array<double>",
        [0.0, 1.1],
        lambda f: check_linear_range_bounds(F.col(f)),
        lambda r: r is not None and "[0.0, 1.0]" in r,
    ),
    # Wrong-length arrays are not this function's concern.
    _Case(
        "lrb_wrong_length_passthrough",
        "array<double>",
        [0.5],
        lambda f: check_linear_range_bounds(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "lrb_null",
        "array<double>",
        None,
        lambda f: check_linear_range_bounds(F.col(f)),
        lambda r: r is None,
    ),
    # --- check_linear_range_order ---------------------------------------------
    _Case(
        "lro_valid",
        "array<double>",
        [0.2, 0.8],
        lambda f: check_linear_range_order(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "lro_equal",
        "array<double>",
        [0.5, 0.5],
        lambda f: check_linear_range_order(F.col(f)),
        lambda r: r is not None and "start must be < end" in r,
    ),
    _Case(
        "lro_after",
        "array<double>",
        [0.8, 0.2],
        lambda f: check_linear_range_order(F.col(f)),
        lambda r: r is not None and "start must be < end" in r,
    ),
    # Wrong-length arrays are not this function's concern.
    _Case(
        "lro_wrong_length_passthrough",
        "array<double>",
        [0.5],
        lambda f: check_linear_range_order(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "lro_null",
        "array<double>",
        None,
        lambda f: check_linear_range_order(F.col(f)),
        lambda r: r is None,
    ),
    # --- check_required -------------------------------------------------------
    _Case(
        "req_null_is_error",
        "string",
        None,
        lambda f: check_required(F.col(f)),
        lambda r: r is not None and "missing" in r,
    ),
    _Case(
        "req_non_null_passes",
        "string",
        "hello",
        lambda f: check_required(F.col(f)),
        lambda r: r is None,
    ),
    # check_required + check_enum via F.coalesce catches both null and invalid.
    _Case(
        "req_composes_with_enum",
        "string",
        None,
        lambda f: F.coalesce(
            check_required(F.col(f)), check_enum(F.col(f), ["a", "b"])
        ),
        lambda r: r is not None and "missing" in r,
    ),
    # --- country code via check_pattern ---------------------------------------
    _Case(
        "cc_valid",
        "string",
        "US",
        lambda f: check_pattern(
            F.col(f), _COUNTRY_CODE_PATTERN, label=_COUNTRY_CODE_LABEL
        ),
        lambda r: r is None,
    ),
    _Case(
        "cc_lowercase_invalid",
        "string",
        "us",
        lambda f: check_pattern(
            F.col(f), _COUNTRY_CODE_PATTERN, label=_COUNTRY_CODE_LABEL
        ),
        lambda r: r is not None and f"invalid {_COUNTRY_CODE_LABEL}" in r and "us" in r,
    ),
    _Case(
        "cc_three_chars_invalid",
        "string",
        "USA",
        lambda f: check_pattern(
            F.col(f), _COUNTRY_CODE_PATTERN, label=_COUNTRY_CODE_LABEL
        ),
        lambda r: r is not None,
    ),
    _Case(
        "cc_null_passes",
        "string",
        None,
        lambda f: check_pattern(
            F.col(f), _COUNTRY_CODE_PATTERN, label=_COUNTRY_CODE_LABEL
        ),
        lambda r: r is None,
    ),
    # --- region code via check_pattern ----------------------------------------
    _Case(
        "rc_valid",
        "string",
        "US-NY",
        lambda f: check_pattern(
            F.col(f), _REGION_CODE_PATTERN, label=_REGION_CODE_LABEL
        ),
        lambda r: r is None,
    ),
    _Case(
        "rc_valid_numeric",
        "string",
        "CN-11",
        lambda f: check_pattern(
            F.col(f), _REGION_CODE_PATTERN, label=_REGION_CODE_LABEL
        ),
        lambda r: r is None,
    ),
    _Case(
        "rc_no_dash_invalid",
        "string",
        "USNY",
        lambda f: check_pattern(
            F.col(f), _REGION_CODE_PATTERN, label=_REGION_CODE_LABEL
        ),
        lambda r: (
            r is not None and f"invalid {_REGION_CODE_LABEL}" in r and "USNY" in r
        ),
    ),
    _Case(
        "rc_null_passes",
        "string",
        None,
        lambda f: check_pattern(
            F.col(f), _REGION_CODE_PATTERN, label=_REGION_CODE_LABEL
        ),
        lambda r: r is None,
    ),
    # --- snake_case via check_pattern -----------------------------------------
    _Case(
        "sc_valid",
        "string",
        "hello_world",
        lambda f: check_pattern(F.col(f), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL),
        lambda r: r is None,
    ),
    _Case(
        "sc_single_word",
        "string",
        "hello",
        lambda f: check_pattern(F.col(f), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL),
        lambda r: r is None,
    ),
    _Case(
        "sc_with_numbers",
        "string",
        "hello_123",
        lambda f: check_pattern(F.col(f), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL),
        lambda r: r is None,
    ),
    _Case(
        "sc_uppercase_invalid",
        "string",
        "Hello_World",
        lambda f: check_pattern(F.col(f), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL),
        lambda r: r is not None and f"invalid {_SNAKE_CASE_LABEL}" in r,
    ),
    _Case(
        "sc_spaces_invalid",
        "string",
        "hello world",
        lambda f: check_pattern(F.col(f), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL),
        lambda r: r is not None,
    ),
    _Case(
        "sc_null_passes",
        "string",
        None,
        lambda f: check_pattern(F.col(f), _SNAKE_CASE_PATTERN, label=_SNAKE_CASE_LABEL),
        lambda r: r is None,
    ),
    # --- check_url_format -----------------------------------------------------
    _Case(
        "url_http_valid",
        "string",
        "http://example.com",
        lambda f: check_url_format(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "url_https_valid",
        "string",
        "https://example.com/path?q=1",
        lambda f: check_url_format(F.col(f)),
        lambda r: r is None,
    ),
    # Pydantic HttpUrl lowercases the scheme, so HTTP:// is accepted.
    _Case(
        "url_uppercase_scheme",
        "string",
        "HTTP://example.com",
        lambda f: check_url_format(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "url_mixed_case_scheme",
        "string",
        "HtTpS://example.com/path",
        lambda f: check_url_format(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "url_no_scheme_invalid",
        "string",
        "example.com",
        lambda f: check_url_format(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "url_ftp_scheme_invalid",
        "string",
        "ftp://example.com",
        lambda f: check_url_format(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "url_null_passes",
        "string",
        None,
        lambda f: check_url_format(F.col(f)),
        lambda r: r is None,
    ),
    # --- check_url_length -----------------------------------------------------
    _Case(
        "urllen_exceeds",
        "string",
        "https://example.com/" + "a" * 2064,  # 2084 chars
        lambda f: check_url_length(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "urllen_exactly_2083",
        "string",
        "https://example.com/" + "a" * 2063,  # 2083 chars
        lambda f: check_url_length(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "urllen_null_passes",
        "string",
        None,
        lambda f: check_url_length(F.col(f)),
        lambda r: r is None,
    ),
    # --- check_email ----------------------------------------------------------
    _Case(
        "email_valid",
        "string",
        "user@example.com",
        lambda f: check_email(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "email_no_at",
        "string",
        "userexample.com",
        lambda f: check_email(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "email_no_domain",
        "string",
        "user@",
        lambda f: check_email(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "email_spaces",
        "string",
        "user @example.com",
        lambda f: check_email(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "email_null",
        "string",
        None,
        lambda f: check_email(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "email_trailing_period",
        "string",
        "user@example.com.",
        lambda f: check_email(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "email_leading_period",
        "string",
        ".user@example.com",
        lambda f: check_email(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "email_period_before_at",
        "string",
        "user.@example.com",
        lambda f: check_email(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "email_period_after_at",
        "string",
        "user@.example.com",
        lambda f: check_email(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "email_double_period_domain",
        "string",
        "user@example..com",
        lambda f: check_email(F.col(f)),
        lambda r: r is not None,
    ),
    _Case(
        "email_dotted_local_valid",
        "string",
        "user.name@example.com",
        lambda f: check_email(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "email_subdomain_valid",
        "string",
        "user@mail.example.co.uk",
        lambda f: check_email(F.col(f)),
        lambda r: r is None,
    ),
    # --- phone via check_pattern ----------------------------------------------
    _Case(
        "phone_valid_us",
        "string",
        "+1 555-555-5555",
        lambda f: check_pattern(F.col(f), _PHONE_PATTERN, label=_PHONE_LABEL),
        lambda r: r is None,
    ),
    _Case(
        "phone_valid_international",
        "string",
        "+44 20 7946 0958",
        lambda f: check_pattern(F.col(f), _PHONE_PATTERN, label=_PHONE_LABEL),
        lambda r: r is None,
    ),
    _Case(
        "phone_no_plus_invalid",
        "string",
        "555-555-5555",
        lambda f: check_pattern(F.col(f), _PHONE_PATTERN, label=_PHONE_LABEL),
        lambda r: r is not None and f"invalid {_PHONE_LABEL}" in r,
    ),
    _Case(
        "phone_letters_invalid",
        "string",
        "+1 abc-defg",
        lambda f: check_pattern(F.col(f), _PHONE_PATTERN, label=_PHONE_LABEL),
        lambda r: r is not None,
    ),
    _Case(
        "phone_null_passes",
        "string",
        None,
        lambda f: check_pattern(F.col(f), _PHONE_PATTERN, label=_PHONE_LABEL),
        lambda r: r is None,
    ),
    # --- wikidata id via check_pattern ----------------------------------------
    _Case(
        "wd_valid",
        "string",
        "Q42",
        lambda f: check_pattern(F.col(f), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL),
        lambda r: r is None,
    ),
    _Case(
        "wd_large_number",
        "string",
        "Q123456789",
        lambda f: check_pattern(F.col(f), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL),
        lambda r: r is None,
    ),
    _Case(
        "wd_lowercase_q_invalid",
        "string",
        "q42",
        lambda f: check_pattern(F.col(f), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL),
        lambda r: r is not None and f"invalid {_WIKIDATA_LABEL}" in r,
    ),
    _Case(
        "wd_no_digits_invalid",
        "string",
        "Q",
        lambda f: check_pattern(F.col(f), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL),
        lambda r: r is not None,
    ),
    _Case(
        "wd_p_prefix_invalid",
        "string",
        "P42",
        lambda f: check_pattern(F.col(f), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL),
        lambda r: r is not None,
    ),
    _Case(
        "wd_null_passes",
        "string",
        None,
        lambda f: check_pattern(F.col(f), _WIKIDATA_PATTERN, label=_WIKIDATA_LABEL),
        lambda r: r is None,
    ),
    # --- check_min_fields_set (multi-field -> struct column) ------------------
    # Count at threshold -> no error.
    _Case(
        "mfs_meets_threshold",
        "struct<a:int,b:int,c:int>",
        {"a": 1, "b": 2, "c": None},
        lambda f: check_min_fields_set(
            [F.col(f)["a"], F.col(f)["b"], F.col(f)["c"]], ["a", "b", "c"], 2
        ),
        lambda r: r is None,
    ),
    # Count above threshold -> no error.
    _Case(
        "mfs_exceeds_threshold",
        "struct<a:int,b:int,c:int>",
        {"a": 1, "b": 2, "c": 3},
        lambda f: check_min_fields_set(
            [F.col(f)["a"], F.col(f)["b"], F.col(f)["c"]], ["a", "b", "c"], 2
        ),
        lambda r: r is None,
    ),
    # Count below threshold -> error with field names and actual count.
    _Case(
        "mfs_below_threshold",
        "struct<a:int,b:int,c:int>",
        {"a": 1, "b": None, "c": None},
        lambda f: check_min_fields_set(
            [F.col(f)["a"], F.col(f)["b"], F.col(f)["c"]], ["a", "b", "c"], 2
        ),
        lambda r: r is not None and "at least 2" in r and "a, b, c" in r and "1" in r,
    ),
    # All null -> error showing 0 non-null.
    _Case(
        "mfs_all_null",
        "struct<a:int,b:int>",
        {"a": None, "b": None},
        lambda f: check_min_fields_set([F.col(f)["a"], F.col(f)["b"]], ["a", "b"], 1),
        lambda r: r is not None and "0" in r,
    ),
    # Error message matches the expected format exactly.
    _Case(
        "mfs_message_format",
        "struct<x:int,y:int>",
        {"x": None, "y": None},
        lambda f: check_min_fields_set([F.col(f)["x"], F.col(f)["y"]], ["x", "y"], 1),
        lambda r: r == "at least 1 of x, y required, got 0 non-null",
    ),
    # --- check_bbox_completeness (bbox struct column) -------------------------
    _Case(
        "bbox_valid",
        "struct<xmin:double,xmax:double,ymin:double,ymax:double>",
        {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0},
        lambda f: check_bbox_completeness(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "bbox_null_passes",
        "struct<xmin:double,xmax:double,ymin:double,ymax:double>",
        None,
        lambda f: check_bbox_completeness(F.col(f)),
        lambda r: r is None,
    ),
    _Case(
        "bbox_null_subfield_fails",
        "struct<xmin:double,xmax:double,ymin:double,ymax:double>",
        {"xmin": None, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0},
        lambda f: check_bbox_completeness(F.col(f)),
        lambda r: r is not None,
    ),
]


@pytest.fixture(scope="module")
def results(spark: SparkSession) -> Any:
    """Pack every case's input into one row, apply every check, collect once."""
    # A DDL schema string, not StructType.fromDDL -- fromDDL landed in PySpark
    # 3.5, and createDataFrame parses the string itself on the >=3.4 floor.
    schema = ", ".join(f"`{c.id}` {c.ddl}" for c in _CASES)
    row = {c.id: c.value for c in _CASES}
    # dict rows are read by field name against the explicit schema, a form the
    # createDataFrame stubs don't model (they want tuple/Row for RowLike).
    df = spark.createDataFrame([row], schema=schema, verifySchema=False)  # type: ignore[call-overload]
    return df.select(*[c.check(c.id).alias(c.id) for c in _CASES]).collect()[0]


@pytest.mark.parametrize("case", _CASES, ids=lambda c: c.id)
def test_constraint_expression(case: _Case, results: Any) -> None:
    value = results[case.id]
    assert case.expect(value), f"{case.id}: got {value!r}"
