"""Tests for CLI entry points."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner
from overture.schema.pyspark._registry import REGISTRY
from overture.schema.pyspark.check import Check, CheckShape
from overture.schema.pyspark.cli import (
    ReadSpec,
    _spark_config,
    absent_column,
    read_feature,
    resolve_read,
    validate_cli,
)
from pyspark.errors import AnalysisException
from pyspark.sql import Row, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from ._support.registry import register_model

_TEST_TYPE = "_test_cli"

# Shared schema for all test registrations that need the four base columns.
_BASE_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField("theme", StringType(), True),
        StructField("type", StringType(), True),
        StructField("value", StringType(), True),
    ]
)

# Tests that branch on registered geometry types require the runtime registry
# to be populated (i.e. generated expression modules present).
_requires_generated = pytest.mark.skipif(
    not REGISTRY, reason="requires generated expression modules"
)


class TestSparkConfig:
    """Tests for S3A auto-configuration."""

    @_requires_generated
    def test_large_geometry_disables_vectorized_reader(self) -> None:
        config = _spark_config(
            "samples/segment.parquet", (), "overture.schema.transportation:Segment"
        )
        assert config["spark.sql.parquet.enableVectorizedReader"] == "false"

    @_requires_generated
    def test_point_geometry_keeps_vectorized_reader(self) -> None:
        config = _spark_config(
            "samples/place.parquet", (), "overture.schema.places:Place"
        )
        assert "spark.sql.parquet.enableVectorizedReader" not in config

    def test_unspecified_geometry_disables_vectorized_reader(self) -> None:
        # _TEST_TYPE registers no geometry_types -- safe default disables the reader
        config = _spark_config("samples/test.parquet", (), _TEST_TYPE)
        assert config["spark.sql.parquet.enableVectorizedReader"] == "false"

    def test_s3a_path_applies_defaults(self) -> None:
        config = _spark_config("s3a://bucket/path", (), _TEST_TYPE)
        assert "org.apache.hadoop:hadoop-aws" in config["spark.jars.packages"]
        assert "S3AFileSystem" in config["spark.hadoop.fs.s3a.impl"]
        assert (
            "AnonymousAWSCredentialsProvider"
            in config["spark.hadoop.fs.s3a.aws.credentials.provider"]
        )

    def test_user_conf_overrides_s3a_defaults(self) -> None:
        config = _spark_config(
            "s3a://bucket/path",
            (
                "spark.hadoop.fs.s3a.aws.credentials.provider="
                "software.amazon.awssdk.auth.credentials.ProfileCredentialsProvider",
            ),
            _TEST_TYPE,
        )
        assert (
            "ProfileCredentialsProvider"
            in config["spark.hadoop.fs.s3a.aws.credentials.provider"]
        )

    def test_user_conf_merges_with_s3a_defaults(self) -> None:
        config = _spark_config(
            "s3a://bucket/path", ("spark.master=local[4]",), _TEST_TYPE
        )
        assert config["spark.master"] == "local[4]"
        assert "spark.jars.packages" in config

    def test_local_path_passes_user_conf(self) -> None:
        config = _spark_config(
            "samples/test.parquet", ("spark.master=local[4]",), _TEST_TYPE
        )
        assert config["spark.master"] == "local[4]"
        assert config["spark.sql.parquet.enableVectorizedReader"] == "false"


def _test_checks() -> list[Check]:
    """Minimal checks for CLI testing: value must be 'good'."""
    return [
        Check(
            field="value",
            name="enum",
            expr=F.when(F.col("value") != "good", F.lit("not good")),
            shape=CheckShape.SCALAR,
            read_columns=frozenset({"value"}),
        ),
    ]


@pytest.fixture(autouse=True)
def _register_test_checks() -> Iterator[None]:
    with register_model(_TEST_TYPE, _BASE_SCHEMA, _test_checks):
        yield


def test_validate_missing_args() -> None:
    runner = CliRunner()
    result = runner.invoke(validate_cli, [])
    assert result.exit_code != 0


def test_validate_unknown_type() -> None:
    runner = CliRunner()
    result = runner.invoke(validate_cli, ["nonexistent", "/dev/null"])
    assert result.exit_code != 0
    assert "nonexistent" in result.output


def test_validate_clean_data(spark: SparkSession, tmp_path: Path) -> None:
    """Valid data exits 0, no output file written."""
    input_path = str(tmp_path / "input.parquet")
    output_path = str(tmp_path / "output.parquet")

    spark.createDataFrame(
        [Row(id="r1", theme="test", type="test_cli", value="good")]
    ).write.parquet(input_path)

    runner = CliRunner()
    result = runner.invoke(validate_cli, [_TEST_TYPE, input_path, "-o", output_path])
    assert result.exit_code == 0, result.output
    assert "0 / 1 rows with errors" in result.output
    assert not Path(output_path).exists()


def test_validate_error_count(spark: SparkSession, tmp_path: Path) -> None:
    """Rows with errors are counted in summary."""
    input_path = str(tmp_path / "input.parquet")
    output_path = str(tmp_path / "output.parquet")

    spark.createDataFrame(
        [Row(id="r1", theme="test", type="test_cli", value="bad")]
    ).write.parquet(input_path)

    runner = CliRunner()
    result = runner.invoke(validate_cli, [_TEST_TYPE, input_path, "-o", output_path])
    assert result.exit_code != 0
    assert "1 / 1 rows with errors" in result.output


def test_validate_shows_error_rows(spark: SparkSession, tmp_path: Path) -> None:
    """Error rows are displayed with violation columns."""
    input_path = str(tmp_path / "input.parquet")
    output_path = str(tmp_path / "output.parquet")

    spark.createDataFrame(
        [Row(id="row1", theme="test", type="test_cli", value="bad")]
    ).write.parquet(input_path)

    runner = CliRunner()
    result = runner.invoke(validate_cli, [_TEST_TYPE, input_path, "-o", output_path])
    assert result.exit_code != 0
    assert "row1" in result.output
    assert "value" in result.output


def test_validate_head_zero(spark: SparkSession, tmp_path: Path) -> None:
    """--head 0 suppresses the error row table."""
    input_path = str(tmp_path / "input.parquet")
    output_path = str(tmp_path / "output.parquet")

    spark.createDataFrame(
        [Row(id="row1", theme="test", type="test_cli", value="bad")]
    ).write.parquet(input_path)

    runner = CliRunner()
    result = runner.invoke(
        validate_cli, [_TEST_TYPE, input_path, "-o", output_path, "--head", "0"]
    )
    assert result.exit_code != 0
    assert "1 / 1 rows with errors" in result.output
    assert "row1" not in result.output


def test_validate_schema_mismatch_exits(spark: SparkSession, tmp_path: Path) -> None:
    """Schema mismatch prints diff and exits before validation."""
    input_path = str(tmp_path / "input.parquet")
    output_path = str(tmp_path / "output.parquet")

    # Write data with wrong schema (IntegerType where StringType expected)
    spark.createDataFrame(
        [Row(id="r1", value=42)], schema="id string, value int"
    ).write.parquet(input_path)

    runner = CliRunner()
    result = runner.invoke(validate_cli, [_TEST_TYPE, input_path, "-o", output_path])
    assert result.exit_code != 0
    assert "Schema mismatch" in result.output
    assert "value" in result.output


def test_validate_skip_schema_check(spark: SparkSession, tmp_path: Path) -> None:
    """--skip-schema-check warns on mismatches but continues validation."""
    input_path = str(tmp_path / "input.parquet")

    # Extra column causes a mismatch but doesn't break check evaluation
    spark.createDataFrame(
        [Row(id="r1", theme="test", type="test_cli", value="good", extra="x")]
    ).write.parquet(input_path)

    runner = CliRunner()
    result = runner.invoke(
        validate_cli, [_TEST_TYPE, input_path, "--skip-schema-check"]
    )
    assert "Schema mismatch" in result.output
    assert "rows with errors" in result.output


def test_validate_skip_columns(spark: SparkSession, tmp_path: Path) -> None:
    """--skip-columns skips checks for absent columns."""
    input_path = str(tmp_path / "input.parquet")

    # Data missing 'value' column — declare it absent via --skip-columns
    spark.createDataFrame([Row(id="r1", theme="test", type="test_cli")]).write.parquet(
        input_path
    )

    runner = CliRunner()
    result = runner.invoke(
        validate_cli,
        [_TEST_TYPE, input_path, "--skip-columns", "value", "--skip-schema-check"],
    )
    assert result.exit_code == 0, result.output
    assert "0 / 1 rows with errors" in result.output


def test_validate_missing_column_suggests_skip_columns(
    spark: SparkSession, tmp_path: Path
) -> None:
    """A column absent from the data hints the --skip-columns flag."""
    input_path = str(tmp_path / "input.parquet")

    # Data missing the 'value' column the schema expects
    spark.createDataFrame([Row(id="r1", theme="test", type="test_cli")]).write.parquet(
        input_path
    )

    runner = CliRunner()
    result = runner.invoke(validate_cli, [_TEST_TYPE, input_path])
    assert result.exit_code != 0
    assert "Schema mismatch" in result.output
    assert "--skip-columns value" in result.output


def _unresolved(object_name: str, *, suggestion: bool = True) -> AnalysisException:
    """An UNRESOLVED_COLUMN AnalysisException naming `object_name`."""
    suffix = "WITH_SUGGESTION" if suggestion else "WITHOUT_SUGGESTION"
    return AnalysisException(
        f"column {object_name} cannot be resolved",
        errorClass=f"UNRESOLVED_COLUMN.{suffix}",
        messageParameters={"objectName": object_name},
    )


class TestAbsentColumn:
    """Classification of AnalysisExceptions into absent-column vs. bug."""

    def test_absent_top_level_column_is_named(self) -> None:
        assert absent_column(_unresolved("`phantom`"), ["id", "value"]) == "phantom"

    def test_without_suggestion_is_also_named(self) -> None:
        exc = _unresolved("`phantom`", suggestion=False)
        assert absent_column(exc, ["id", "value"]) == "phantom"

    def test_dotted_reference_yields_top_level_column(self) -> None:
        assert absent_column(_unresolved("`bbox`.`xmin`"), ["id"]) == "bbox"

    def test_present_column_is_not_named(self) -> None:
        # An unresolved-column error naming a column that *is* present is not
        # the missing-data case --skip-columns resolves; treat it as a bug.
        assert absent_column(_unresolved("`value`"), ["id", "value"]) is None

    def test_non_unresolved_condition_is_a_bug(self) -> None:
        exc = AnalysisException(
            "cannot extract field from scalar",
            errorClass="INVALID_EXTRACT_BASE_FIELD_TYPE",
            messageParameters={"base": '"value"', "other": '"STRING"'},
        )
        assert absent_column(exc, ["id", "value"]) is None

    def test_missing_condition_is_a_bug(self) -> None:
        assert absent_column(AnalysisException("opaque failure"), ["id"]) is None

    def test_missing_object_name_is_a_bug(self) -> None:
        exc = AnalysisException(
            "unresolved with no objectName",
            errorClass="UNRESOLVED_COLUMN.WITHOUT_SUGGESTION",
            messageParameters={},
        )
        assert absent_column(exc, ["id"]) is None


def test_validate_unresolvable_check_names_absent_column(
    spark: SparkSession, tmp_path: Path
) -> None:
    """An unresolved-column check names the absent column and hints --skip-columns."""
    unresolvable_type = "_test_cli_unresolvable"
    # A check reading a column in neither the data nor the expected schema
    # is invisible to absence detection (which only flags expected-but-
    # missing columns), so it survives the read_columns drop, reaches
    # evaluation, and raises UNRESOLVED_COLUMN -- the backstop the CLI
    # must catch and convert into a column-named hint.
    with register_model(
        unresolvable_type,
        _BASE_SCHEMA,
        checks=lambda: [
            Check(
                field="phantom",
                name="present",
                expr=F.when(F.col("phantom").isNull(), F.lit("missing phantom")),
                shape=CheckShape.SCALAR,
                read_columns=frozenset({"phantom"}),
            )
        ],
    ):
        input_path = str(tmp_path / "input.parquet")
        spark.createDataFrame(
            [Row(id="r1", theme="test", type="x", value="good")]
        ).write.parquet(input_path)
        runner = CliRunner()
        result = runner.invoke(validate_cli, [unresolvable_type, input_path])
        assert result.exit_code != 0
        assert "phantom" in result.output
        assert "--skip-columns phantom" in result.output


def test_validate_planning_bug_propagates(spark: SparkSession, tmp_path: Path) -> None:
    """A non-column planning error surfaces as a bug, not a --skip-columns hint."""
    buggy_type = "_test_cli_planning_bug"
    # `value` is a present string column, so the check survives the
    # read_columns drop, but extracting a struct field from a string is a
    # generator bug: it raises an AnalysisException that is *not*
    # UNRESOLVED_COLUMN. `--skip-columns value` would not fix it, so the
    # backstop must let it propagate rather than masking it.
    with register_model(
        buggy_type,
        _BASE_SCHEMA,
        checks=lambda: [
            Check(
                field="value",
                name="struct_field",
                expr=F.when(F.col("value").getField("missing").isNull(), F.lit("bad")),
                shape=CheckShape.SCALAR,
                read_columns=frozenset({"value"}),
            )
        ],
    ):
        input_path = str(tmp_path / "input.parquet")
        spark.createDataFrame(
            [Row(id="r1", theme="test", type="x", value="good")]
        ).write.parquet(input_path)
        runner = CliRunner()
        result = runner.invoke(validate_cli, [buggy_type, input_path])
        assert result.exit_code != 0
        assert isinstance(result.exception, AnalysisException)
        assert "--skip-columns" not in result.output


def test_validate_ignore_extra_columns(spark: SparkSession, tmp_path: Path) -> None:
    """--ignore-extra-columns suppresses 'expected missing' schema mismatches."""
    input_path = str(tmp_path / "input.parquet")

    spark.createDataFrame(
        [Row(id="r1", theme="test", type="test_cli", value="good", extra="x")]
    ).write.parquet(input_path)

    runner = CliRunner()
    # Without the flag, schema mismatch exits
    result = runner.invoke(validate_cli, [_TEST_TYPE, input_path])
    assert result.exit_code != 0
    assert "Schema mismatch" in result.output

    # With the flag, extra column is tolerated
    result = runner.invoke(
        validate_cli, [_TEST_TYPE, input_path, "--ignore-extra-columns", "extra"]
    )
    assert result.exit_code == 0, result.output
    assert "0 / 1 rows with errors" in result.output


def test_validate_suppress_field(spark: SparkSession, tmp_path: Path) -> None:
    """--suppress FIELD removes all checks on that field."""
    input_path = str(tmp_path / "input.parquet")

    spark.createDataFrame(
        [Row(id="r1", theme="test", type="test_cli", value="bad")]
    ).write.parquet(input_path)

    runner = CliRunner()
    result = runner.invoke(
        validate_cli, [_TEST_TYPE, input_path, "--suppress", "value"]
    )
    assert result.exit_code == 0, result.output
    assert "0 / 1 rows with errors" in result.output


def test_validate_suppress_field_check(spark: SparkSession, tmp_path: Path) -> None:
    """--suppress FIELD:CHECK removes a specific check."""
    input_path = str(tmp_path / "input.parquet")

    spark.createDataFrame(
        [Row(id="r1", theme="test", type="test_cli", value="bad")]
    ).write.parquet(input_path)

    runner = CliRunner()
    result = runner.invoke(
        validate_cli, [_TEST_TYPE, input_path, "--suppress", "value:enum"]
    )
    assert result.exit_code == 0, result.output
    assert "0 / 1 rows with errors" in result.output


def test_validate_output_contains_explained_violations(
    spark: SparkSession, tmp_path: Path
) -> None:
    """Output Parquet contains explain() violations with field/check/message."""
    input_path = str(tmp_path / "input.parquet")
    output_path = str(tmp_path / "output.parquet")

    spark.createDataFrame(
        [
            Row(id="r1", theme="test", type="test_cli", value="good"),
            Row(id="r2", theme="test", type="test_cli", value="bad"),
        ]
    ).write.parquet(input_path)

    runner = CliRunner()
    runner.invoke(validate_cli, [_TEST_TYPE, input_path, "-o", output_path])

    result_df = spark.read.parquet(output_path)
    assert {"field", "check", "message"} <= set(result_df.columns)
    assert result_df.count() == 1  # one violation from r2


_BATHYMETRY_PARTITIONS = {"theme": "base", "type": "bathymetry"}
_SEGMENT_PARTITIONS = {"theme": "transportation", "type": "segment"}


class TestResolveRead:
    """Pure-function tests for path resolution logic."""

    def test_release_root(self) -> None:
        spec = resolve_read("/data/release/2026-02-18.0/", _BATHYMETRY_PARTITIONS)
        assert spec == ReadSpec(
            data_path="/data/release/2026-02-18.0/theme=base/type=bathymetry",
            base_path="/data/release/2026-02-18.0",
        )

    def test_release_root_no_trailing_slash(self) -> None:
        spec = resolve_read("/data/release/2026-02-18.0", _BATHYMETRY_PARTITIONS)
        assert spec == ReadSpec(
            data_path="/data/release/2026-02-18.0/theme=base/type=bathymetry",
            base_path="/data/release/2026-02-18.0",
        )

    def test_leaf_partition(self) -> None:
        spec = resolve_read(
            "/data/release/2026-02-18.0/theme=base/type=bathymetry/",
            _BATHYMETRY_PARTITIONS,
        )
        assert spec == ReadSpec(
            data_path="/data/release/2026-02-18.0/theme=base/type=bathymetry/",
            base_path="/data/release/2026-02-18.0",
        )

    def test_theme_partition_appends_type_leaf(self) -> None:
        # A theme-level path is missing the `type=` leaf; resolve_read must
        # append it so a single feature's checks aren't run against every
        # type sharing the theme directory.
        spec = resolve_read(
            "/data/release/2026-02-18.0/theme=base/", _BATHYMETRY_PARTITIONS
        )
        assert spec == ReadSpec(
            data_path="/data/release/2026-02-18.0/theme=base/type=bathymetry",
            base_path="/data/release/2026-02-18.0",
        )

    def test_individual_file(self) -> None:
        spec = resolve_read("/tmp/bathymetry.parquet", _BATHYMETRY_PARTITIONS)
        assert spec == ReadSpec(data_path="/tmp/bathymetry.parquet")

    def test_individual_file_no_partitions(self) -> None:
        spec = resolve_read("/tmp/data.parquet", None)
        assert spec == ReadSpec(data_path="/tmp/data.parquet")

    def test_plain_directory_no_partitions(self) -> None:
        spec = resolve_read("/tmp/data/", None)
        assert spec == ReadSpec(data_path="/tmp/data/")

    def test_s3a_release_root(self) -> None:
        spec = resolve_read("s3a://bucket/release/2026-02-18.0/", _SEGMENT_PARTITIONS)
        assert spec == ReadSpec(
            data_path="s3a://bucket/release/2026-02-18.0/theme=transportation/type=segment",
            base_path="s3a://bucket/release/2026-02-18.0",
        )

    def test_s3a_leaf_partition(self) -> None:
        spec = resolve_read(
            "s3a://bucket/release/2026-02-18.0/theme=transportation/type=segment/",
            _SEGMENT_PARTITIONS,
        )
        assert spec == ReadSpec(
            data_path="s3a://bucket/release/2026-02-18.0/theme=transportation/type=segment/",
            base_path="s3a://bucket/release/2026-02-18.0",
        )


def _write_partitioned(spark: SparkSession, base_dir: Path, rows: list[Row]) -> None:
    """Write test rows as Hive-partitioned Parquet under *base_dir*."""
    spark.createDataFrame(rows).write.partitionBy("theme", "type").parquet(
        str(base_dir)
    )


class TestReadFeature:
    """Integration tests: resolve_read + read_feature against local Parquet."""

    def test_read_from_release_root(self, spark: SparkSession, tmp_path: Path) -> None:
        base = tmp_path / "release"
        _write_partitioned(
            spark,
            base,
            [Row(id="r1", value="good", theme="test", type=_TEST_TYPE)],
        )
        spec = resolve_read(str(base), {"theme": "test", "type": _TEST_TYPE})
        df = read_feature(spark, spec)
        assert df.count() == 1
        assert set(df.columns) >= {"id", "theme", "type", "value"}

    def test_read_from_leaf_partition(
        self, spark: SparkSession, tmp_path: Path
    ) -> None:
        base = tmp_path / "release"
        _write_partitioned(
            spark,
            base,
            [Row(id="r1", value="good", theme="test", type=_TEST_TYPE)],
        )
        leaf = str(base / f"theme=test/type={_TEST_TYPE}")
        spec = resolve_read(leaf, {"theme": "test", "type": _TEST_TYPE})
        df = read_feature(spark, spec)
        assert df.count() == 1
        assert set(df.columns) >= {"id", "theme", "type", "value"}

    def test_read_from_individual_file(
        self, spark: SparkSession, tmp_path: Path
    ) -> None:
        file_path = str(tmp_path / "data.parquet")
        spark.createDataFrame(
            [Row(id="r1", theme="test", type=_TEST_TYPE, value="good")]
        ).write.parquet(file_path)
        spec = resolve_read(file_path, {"theme": "test", "type": _TEST_TYPE})
        df = read_feature(spark, spec)
        assert df.count() == 1
        assert set(df.columns) >= {"id", "theme", "type", "value"}

    def test_release_root_filters_to_type(
        self, spark: SparkSession, tmp_path: Path
    ) -> None:
        """Only the target type's rows are returned from a multi-type release."""
        base = tmp_path / "release"
        _write_partitioned(
            spark,
            base,
            [
                Row(id="r1", value="good", theme="test", type=_TEST_TYPE),
                Row(id="r2", value="good", theme="test", type="other"),
            ],
        )
        spec = resolve_read(str(base), {"theme": "test", "type": _TEST_TYPE})
        df = read_feature(spark, spec)
        assert df.count() == 1
        assert df.collect()[0]["id"] == "r1"

    def test_theme_partition_filters_to_type(
        self, spark: SparkSession, tmp_path: Path
    ) -> None:
        """A theme-level path returns only the target type, not its siblings."""
        base = tmp_path / "release"
        _write_partitioned(
            spark,
            base,
            [
                Row(id="r1", value="good", theme="test", type=_TEST_TYPE),
                Row(id="r2", value="good", theme="test", type="other"),
            ],
        )
        theme_path = str(base / "theme=test")
        spec = resolve_read(theme_path, {"theme": "test", "type": _TEST_TYPE})
        df = read_feature(spark, spec)
        assert df.count() == 1
        assert df.collect()[0]["id"] == "r1"


def test_validate_from_partitioned_release(spark: SparkSession, tmp_path: Path) -> None:
    """Full CLI round-trip reading from a Hive-partitioned release root."""
    base = tmp_path / "release"
    _write_partitioned(
        spark,
        base,
        [Row(id="r1", value="good", theme="test", type=_TEST_TYPE)],
    )
    runner = CliRunner()
    result = runner.invoke(validate_cli, [_TEST_TYPE, str(base)])
    assert result.exit_code == 0, result.output
    assert "0 / 1 rows with errors" in result.output
