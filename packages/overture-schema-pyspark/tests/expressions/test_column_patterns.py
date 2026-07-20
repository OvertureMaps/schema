"""Tests for column_patterns — structural PySpark composition helpers."""

from overture.schema.pyspark.expressions.column_patterns import (
    array_check,
    check_struct_unique,
    coalesce_errors,
    error_msg,
    map_keys_check,
    map_values_check,
    nested_array_check,
    nested_map_keys_check,
    nested_map_values_check,
)
from overture.schema.pyspark.expressions.constraint_expressions import (
    check_bounds,
    check_require_any_of,
    check_string_min_length,
)
from pyspark.sql import Row, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    IntegerType,
    MapType,
    StringType,
    StructField,
    StructType,
)


def test_error_msg_concatenates(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(val="bad")])
    result = df.select(error_msg("field: got ", F.col("val")).alias("msg")).collect()
    assert result[0]["msg"] == "field: got bad"


def test_error_msg_multiple_values(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(a="x", b="y")])
    result = df.select(
        error_msg("prefix ", F.col("a"), F.lit(" and "), F.col("b")).alias("msg")
    ).collect()
    assert result[0]["msg"] == "prefix x and y"


def test_error_msg_null_value_does_not_nullify_message(spark: SparkSession) -> None:
    # A NULL interpolated value must not make the whole message NULL: F.concat
    # would, and a NULL message is dropped by array_compact, silently swallowing
    # the violation (e.g. an out-of-bounds linear-reference range [null, 1.5]).
    # The null must render as a literal instead.
    df = spark.createDataFrame([Row(val=None)], schema="val double")
    result = df.select(error_msg("got ", F.col("val")).alias("msg")).collect()
    assert result[0]["msg"] == "got null"


def test_array_check_null_column_returns_null(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(items=None)],
        schema="items array<struct<val:string>>",
    )
    result = df.select(
        array_check("items", lambda el: F.lit("err")).alias("errs")
    ).collect()
    assert result[0]["errs"] is None


def test_array_check_filters_nulls(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(items=[Row(val="ok"), Row(val="bad")])],
        schema="items array<struct<val:string>>",
    )
    result = df.select(
        array_check(
            "items",
            lambda el: F.when(el["val"] == "bad", F.lit("error")),
        ).alias("errs")
    ).collect()
    assert result[0]["errs"] == ["error"]


def test_array_check_empty_when_all_valid(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(items=[Row(val="ok")])],
        schema="items array<struct<val:string>>",
    )
    result = df.select(
        array_check(
            "items",
            lambda el: F.when(el["val"] == "bad", F.lit("error")),
        ).alias("errs")
    ).collect()
    assert result[0]["errs"] == []


def test_struct_unique_no_duplicates(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(items=[Row(id="a"), Row(id="b")])],
        schema="items array<struct<id:string>>",
    )
    result = df.select(check_struct_unique("items").alias("err")).collect()
    assert result[0]["err"] is None


def test_struct_unique_with_duplicates(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(items=[Row(id="a"), Row(id="a")])],
        schema="items array<struct<id:string>>",
    )
    result = df.select(check_struct_unique("items").alias("err")).collect()
    assert result[0]["err"] is not None
    assert "duplicate" in result[0]["err"]


def test_struct_unique_null_column(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(items=None)],
        schema="items array<struct<id:string>>",
    )
    result = df.select(check_struct_unique("items").alias("err")).collect()
    assert result[0]["err"] is None


def test_struct_unique_repeated_value_different_fields(spark: SparkSession) -> None:
    """Structs with same value subfield but different other fields are unique."""
    df = spark.createDataFrame(
        [
            Row(
                items=[
                    Row(value="a", pos=0.0),
                    Row(value="b", pos=0.5),
                    Row(value="a", pos=0.7),
                ]
            )
        ]
    )
    result = df.select(check_struct_unique("items").alias("err")).collect()
    assert result[0]["err"] is None


def test_struct_unique_single_element(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(items=[Row(id="a")])],
        schema="items array<struct<id:string>>",
    )
    result = df.select(check_struct_unique("items").alias("err")).collect()
    assert result[0]["err"] is None


def test_array_check_accepts_column(spark: SparkSession) -> None:
    """array_check works when passed a Column instead of a string name."""
    df = spark.createDataFrame(
        [Row(items=[Row(val="ok"), Row(val="bad")])],
        schema="items array<struct<val:string>>",
    )
    result = df.select(
        array_check(
            F.col("items"),
            lambda el: F.when(el["val"] == "bad", F.lit("error")),
        ).alias("errs")
    ).collect()
    assert result[0]["errs"] == ["error"]


def test_check_struct_unique_accepts_column(spark: SparkSession) -> None:
    """check_struct_unique works when passed a Column instead of a string name."""
    df = spark.createDataFrame(
        [Row(items=[Row(id="a"), Row(id="a")])],
        schema="items array<struct<id:string>>",
    )
    result = df.select(check_struct_unique(F.col("items")).alias("err")).collect()
    assert result[0]["err"] is not None
    assert "duplicate" in result[0]["err"]


def test_check_struct_unique_column_null(spark: SparkSession) -> None:
    """check_struct_unique with Column input handles null."""
    df = spark.createDataFrame(
        [Row(items=None)], schema="items array<struct<id:string>>"
    )
    result = df.select(check_struct_unique(F.col("items")).alias("err")).collect()
    assert result[0]["err"] is None


def test_nested_array_check_flattens(spark: SparkSession) -> None:
    """Inner array_check per outer element produces flat error list."""
    schema = "items array<struct<tags:array<string>>>"
    df = spark.createDataFrame(
        [
            Row(
                items=[
                    Row(tags=["good", "bad"]),
                    Row(tags=["worse"]),
                ]
            )
        ],
        schema=schema,
    )
    result_col = nested_array_check(
        "items",
        lambda el: array_check(
            el["tags"],
            lambda tag: F.when(tag != "good", F.concat(F.lit("bad: "), tag)),
        ),
    )
    result = df.select(coalesce_errors(result_col).alias("errs")).collect()
    errors = result[0]["errs"]
    assert len(errors) == 2
    assert all(isinstance(e, str) for e in errors)


def test_nested_array_check_null_outer(spark: SparkSession) -> None:
    schema = "items array<struct<tags:array<string>>>"
    df = spark.createDataFrame([Row(items=None)], schema=schema)
    result_col = nested_array_check(
        "items",
        lambda el: array_check(
            el["tags"],
            lambda tag: F.when(tag != "good", F.lit("bad")),
        ),
    )
    result = df.select(coalesce_errors(result_col).alias("errs")).collect()
    assert result[0]["errs"] == []


def test_nested_array_check_mixed_null_inner_with_sibling_errors(
    spark: SparkSession,
) -> None:
    """A null inner array must not nullify sibling errors during flatten.

    `F.flatten` returns NULL whenever any sub-array is NULL.  Without
    guarding inner nulls, the outer transform produces NULL and every
    sibling error is silently dropped.
    """
    schema = "items array<struct<tags:array<string>>>"
    df = spark.createDataFrame(
        [
            Row(
                items=[
                    Row(tags=["good"]),
                    Row(tags=None),
                    Row(tags=["bad"]),
                ]
            )
        ],
        schema=schema,
    )
    result_col = nested_array_check(
        "items",
        lambda el: array_check(
            el["tags"],
            lambda tag: F.when(tag != "good", F.concat(F.lit("bad: "), tag)),
        ),
    )
    result = df.select(coalesce_errors(result_col).alias("errs")).collect()
    assert result[0]["errs"] == ["bad: bad"]


def test_nested_array_check_no_errors(spark: SparkSession) -> None:
    schema = "items array<struct<tags:array<string>>>"
    df = spark.createDataFrame(
        [Row(items=[Row(tags=["good"])])],
        schema=schema,
    )
    result_col = nested_array_check(
        "items",
        lambda el: array_check(
            el["tags"],
            lambda tag: F.when(tag != "good", F.lit("bad")),
        ),
    )
    result = df.select(coalesce_errors(result_col).alias("errs")).collect()
    assert result[0]["errs"] == []


def test_map_keys_check_flags_bad_key(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(tags={"good": "v", "bad": "v"})],
        schema="tags map<string,string>",
    )
    result = df.select(
        map_keys_check("tags", lambda k: F.when(k == "bad", F.lit("bad key"))).alias(
            "errs"
        )
    ).collect()
    assert result[0]["errs"] == ["bad key"]


def test_map_values_check_flags_bad_value(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(tags={"a": "ok", "b": "bad"})],
        schema="tags map<string,string>",
    )
    result = df.select(
        map_values_check(
            "tags", lambda v: F.when(v == "bad", F.lit("bad value"))
        ).alias("errs")
    ).collect()
    assert result[0]["errs"] == ["bad value"]


def test_map_values_check_descends_into_value_struct_field(
    spark: SparkSession,
) -> None:
    # A field check on a `dict[str, Model]` value navigates into the value
    # struct: map_values_check over a struct-navigating lambda, the exact
    # composition the renderer emits for a map-of-model value field.
    df = spark.createDataFrame(
        [Row(items={"a": Row(label="")})],
        schema="items map<string,struct<label:string>>",
    )
    result = df.select(
        map_values_check(
            "items", lambda v: check_string_min_length(v["label"], 1)
        ).alias("errs")
    ).collect()
    assert result[0]["errs"] == ["minimum length 1, got 0"]


def test_map_values_check_passes_valid_value_struct_field(
    spark: SparkSession,
) -> None:
    df = spark.createDataFrame(
        [Row(items={"a": Row(label="ok")})],
        schema="items map<string,struct<label:string>>",
    )
    result = df.select(
        map_values_check(
            "items", lambda v: check_string_min_length(v["label"], 1)
        ).alias("errs")
    ).collect()
    assert result[0]["errs"] == []


def test_map_values_check_enforces_value_model_constraint(
    spark: SparkSession,
) -> None:
    # A model-level constraint on a `dict[str, Model]` value: map_values_check
    # wrapping check_require_any_of over the value struct's fields, the exact
    # composition the renderer emits for a map-of-model value-model constraint.
    df = spark.createDataFrame(
        [Row(subs={"a": Row(foo=None, bar=None)})],
        schema="subs map<string,struct<foo:int,bar:string>>",
    )
    result = df.select(
        map_values_check(
            "subs",
            lambda v: check_require_any_of([v["foo"], v["bar"]], ["foo", "bar"]),
        ).alias("errs")
    ).collect()
    assert result[0]["errs"] == ["requires at least one of foo, bar"]


def test_map_values_check_passes_satisfied_value_model_constraint(
    spark: SparkSession,
) -> None:
    df = spark.createDataFrame(
        [Row(subs={"a": Row(foo=1, bar=None)})],
        schema="subs map<string,struct<foo:int,bar:string>>",
    )
    result = df.select(
        map_values_check(
            "subs",
            lambda v: check_require_any_of([v["foo"], v["bar"]], ["foo", "bar"]),
        ).alias("errs")
    ).collect()
    assert result[0]["errs"] == []


def test_map_keys_check_null_column_returns_null(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(tags=None)], schema="tags map<string,string>")
    result = df.select(
        map_keys_check("tags", lambda k: F.lit("err")).alias("errs")
    ).collect()
    assert result[0]["errs"] is None


def test_map_values_check_all_valid_empty(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(tags={"a": "ok"})], schema="tags map<string,string>"
    )
    result = df.select(
        map_values_check("tags", lambda v: F.when(v == "bad", F.lit("err"))).alias(
            "errs"
        )
    ).collect()
    assert result[0]["errs"] == []


def test_map_keys_check_accepts_column(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(tags={"bad": "v"})], schema="tags map<string,string>"
    )
    result = df.select(
        map_keys_check(F.col("tags"), lambda k: F.when(k == "bad", F.lit("err"))).alias(
            "errs"
        )
    ).collect()
    assert result[0]["errs"] == ["err"]


def test_coalesce_errors_null_becomes_empty(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(x=1)])
    result = df.select(
        coalesce_errors(F.lit(None).cast("array<string>")).alias("errs")
    ).collect()
    assert result[0]["errs"] == []


def test_coalesce_errors_preserves_array(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(x=1)])
    result = df.select(coalesce_errors(F.array(F.lit("err"))).alias("errs")).collect()
    assert result[0]["errs"] == ["err"]


def test_nested_map_values_check_flattens_inner_array_errors(
    spark: SparkSession,
) -> None:
    # column `m`: map<string, array<int>>; flag any element == 0 in any value list.
    schema = StructType(
        [StructField("m", MapType(StringType(), ArrayType(IntegerType())))]
    )
    df = spark.createDataFrame(
        [({"a": [1, 0], "b": [2]},), ({"a": [1], "b": [3]},)],
        schema,
    )
    check = nested_map_values_check(
        "m",
        lambda v: array_check(v, lambda e: F.when(e == 0, F.lit("zero not allowed"))),
    )
    rows = df.select(check.alias("errors")).collect()
    # Row 0 has one zero -> one flattened error; row 1 has none -> empty.
    assert rows[0]["errors"] == ["zero not allowed"]
    assert rows[1]["errors"] == []


def test_nested_map_keys_check_flattens_inner_array_errors(
    spark: SparkSession,
) -> None:
    # column `m`: map<string, int>; split each key into char array and flag 'x'.
    df = spark.createDataFrame(
        [({"ax": 1, "b": 2},), ({"cd": 1},)],
        schema="m map<string,int>",
    )
    check = nested_map_keys_check(
        "m",
        lambda k: array_check(
            F.split(k, ""), lambda ch: F.when(ch == "x", F.lit("x not allowed"))
        ),
    )
    rows = df.select(check.alias("errors")).collect()
    # Row 0 has key "ax" with 'x' -> one flattened error; row 1 has no 'x' -> empty.
    assert rows[0]["errors"] == ["x not allowed"]
    assert rows[1]["errors"] == []


def test_nested_array_check_wraps_map_values_check(spark: SparkSession) -> None:
    # column `items`: array<struct<tags: map<string,string>>>; flag any map value
    # shorter than 3 chars in any element -- the `items[].tags{value}` pairing the
    # generated `nested_array_check(... map_values_check ...)` folds.
    schema = StructType(
        [
            StructField(
                "items",
                ArrayType(
                    StructType(
                        [StructField("tags", MapType(StringType(), StringType()))]
                    )
                ),
            )
        ]
    )
    df = spark.createDataFrame(
        [
            ([{"tags": {"k": "ab"}}],),
            ([{"tags": {"k": "abc"}}, {"tags": {"k2": "wxyz"}}],),
        ],
        schema,
    )
    check = nested_array_check(
        "items",
        lambda el: map_values_check(
            el["tags"], lambda v: check_string_min_length(v, 3)
        ),
    )
    rows = df.select(check.alias("errors")).collect()
    # Row 0's "ab" is too short -> one flattened error; row 1 is clean -> empty.
    assert rows[0]["errors"] != []
    assert rows[1]["errors"] == []


def test_nested_map_values_check_wraps_map_values_check(spark: SparkSession) -> None:
    # column `subs`: map<string, map<string,int>>; flag any inner value < 0 -- the
    # `subs{value}{value}` pairing the generated
    # `nested_map_values_check(... map_values_check ...)` folds.
    schema = StructType(
        [
            StructField(
                "subs", MapType(StringType(), MapType(StringType(), IntegerType()))
            )
        ]
    )
    df = spark.createDataFrame(
        [({"k": {"a": -2}},), ({"k": {"a": 0, "b": 1}},)],
        schema,
    )
    check = nested_map_values_check(
        "subs",
        lambda v: map_values_check(v, lambda w: check_bounds(w, ge=0, check_nan=False)),
    )
    rows = df.select(check.alias("errors")).collect()
    # Row 0's -2 violates ge=0 -> one flattened error; row 1 is clean -> empty.
    assert rows[0]["errors"] != []
    assert rows[1]["errors"] == []
