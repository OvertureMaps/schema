"""Tests for column_patterns — structural PySpark composition helpers."""

from overture.schema.pyspark.expressions.column_patterns import (
    array_check,
    check_struct_unique,
    coalesce_errors,
    error_msg,
    nested_array_check,
)
from pyspark.sql import Row, SparkSession
from pyspark.sql import functions as F


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
