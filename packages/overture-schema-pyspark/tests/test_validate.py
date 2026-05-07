"""Tests for validation pipeline."""

from collections.abc import Iterator

import pytest
from overture.schema.pyspark._registry import REGISTRY
from overture.schema.pyspark.check import Check, CheckShape, FeatureValidation
from overture.schema.pyspark.validate import (
    ValidationResult,
    _normalize_suppress,
    evaluate_checks,
    explain_errors,
    feature_keys,
    feature_names,
    filter_errors,
    validate_feature,
)
from pyspark.sql import DataFrame, Row, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType


def _scalar_check(
    field: str, name: str, expr: F.Column, *, root_field: str | None = None
) -> Check:
    return Check(
        field=field,
        name=name,
        expr=expr,
        shape=CheckShape.SCALAR,
        root_field=root_field if root_field is not None else field,
    )


def _array_check(
    field: str, name: str, expr: F.Column, *, root_field: str | None = None
) -> Check:
    return Check(
        field=field,
        name=name,
        expr=expr,
        shape=CheckShape.ARRAY,
        root_field=root_field if root_field is not None else field,
    )


def _row(**kwargs: object) -> Row:
    """Build a row with convenience id/theme/type defaults."""
    defaults: dict[str, object] = {"id": "id1", "theme": "t", "type": "f"}
    defaults.update(kwargs)
    return Row(**defaults)


class TestEvaluateChecks:
    """Tests for evaluate_checks()."""

    def test_appends_error_columns(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("value", "required", F.lit("fail"))]
        evaluated = evaluate_checks(df, checks)
        assert "_err_0" in evaluated.columns
        assert set(df.columns) < set(evaluated.columns)

    def test_multiple_checks(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [
            _scalar_check("a", "c1", F.lit("e1")),
            _scalar_check("b", "c2", F.lit("e2")),
        ]
        evaluated = evaluate_checks(df, checks)
        assert "_err_0" in evaluated.columns
        assert "_err_1" in evaluated.columns

    def test_error_column_is_array_string(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("value", "required", F.lit("fail"))]
        evaluated = evaluate_checks(df, checks)
        row = evaluated.collect()[0]
        assert row["_err_0"] == ["fail"]

    def test_null_error_for_passing_check(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("value", "ok", F.lit(None).cast("string"))]
        evaluated = evaluate_checks(df, checks)
        row = evaluated.collect()[0]
        assert row["_err_0"] == []


class TestFilterErrors:
    """Tests for filter_errors()."""

    def test_keeps_failing_rows(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("value", "required", F.lit("fail"))]
        evaluated = evaluate_checks(df, checks)
        result = filter_errors(evaluated, checks)
        assert result.count() == 1

    def test_removes_passing_rows(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("value", "ok", F.lit(None).cast("string"))]
        evaluated = evaluate_checks(df, checks)
        result = filter_errors(evaluated, checks)
        assert result.count() == 0

    def test_strips_error_columns(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("value", "required", F.lit("fail"))]
        evaluated = evaluate_checks(df, checks)
        result = filter_errors(evaluated, checks)
        assert not any(c.startswith("_err_") for c in result.columns)
        assert set(result.columns) == set(df.columns)

    def test_preserves_schema(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("value", "required", F.lit("fail"))]
        evaluated = evaluate_checks(df, checks)
        result = filter_errors(evaluated, checks)
        assert result.schema == df.schema

    def test_mixed_rows(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row(id="pass"), _row(id="fail")])
        checks = [
            _scalar_check(
                "id",
                "not_fail",
                F.when(F.col("id") == "fail", F.lit("bad")),
            ),
        ]
        evaluated = evaluate_checks(df, checks)
        result = filter_errors(evaluated, checks)
        assert result.count() == 1
        assert result.collect()[0]["id"] == "fail"


class TestExplainErrors:
    """Tests for explain_errors()."""

    def test_scalar_violation(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("value", "required", F.lit("missing"))]
        evaluated = evaluate_checks(df, checks)
        result = explain_errors(evaluated, checks)
        rows = result.collect()
        assert len(rows) == 1
        assert rows[0]["field"] == "value"
        assert rows[0]["check"] == "required"
        assert rows[0]["message"] == "missing"

    def test_array_violation(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_array_check("arr", "elem", F.array(F.lit("e1"), F.lit("e2")))]
        evaluated = evaluate_checks(df, checks)
        result = explain_errors(evaluated, checks)
        messages = sorted(r["message"] for r in result.collect())
        assert messages == ["e1", "e2"]

    def test_no_violations(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("value", "ok", F.lit(None).cast("string"))]
        evaluated = evaluate_checks(df, checks)
        result = explain_errors(evaluated, checks)
        assert result.count() == 0

    def test_preserves_original_columns(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("value", "required", F.lit("fail"))]
        evaluated = evaluate_checks(df, checks)
        result = explain_errors(evaluated, checks)
        rows = result.collect()
        assert rows[0]["id"] == "id1"
        assert set(result.columns) == {*df.columns, "field", "check", "message"}

    def test_output_columns(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("x", "required", F.lit("err"))]
        evaluated = evaluate_checks(df, checks)
        result = explain_errors(evaluated, checks)
        expected_cols = {*df.columns, "field", "check", "message"}
        assert set(result.columns) == expected_cols

    def test_empty_checks_returns_empty_dataframe_with_schema(
        self, spark: SparkSession
    ) -> None:
        # Regression: explain_errors([]) on rows with no checks must
        # return a typed empty DataFrame, not invoke `stack(0, ...)`
        # (which Spark rejects). Consumers expect the standard
        # `field/check/message` columns even when nothing fired.
        df = spark.createDataFrame([_row()])
        result = explain_errors(df, [])
        assert result.count() == 0
        assert set(result.columns) == {*df.columns, "field", "check", "message"}


class TestUserErrColumn:
    """`_err_<int>` is reserved; user `_err_*` names are passed through."""

    def test_user_err_named_column_preserved(self, spark: SparkSession) -> None:
        # Regression: `_orig_columns` strips only `_err_<digits>`. A
        # user-supplied column like `_err_foo` must survive
        # filter_errors / explain_errors round-trips.
        df = spark.createDataFrame([_row(_err_foo="custom-data")])
        checks = [_scalar_check("value", "required", F.lit("fail"))]
        evaluated = evaluate_checks(df, checks)
        filtered = filter_errors(evaluated, checks)
        assert "_err_foo" in filtered.columns
        assert filtered.collect()[0]["_err_foo"] == "custom-data"

        explained = explain_errors(evaluated, checks)
        assert "_err_foo" in explained.columns
        assert explained.collect()[0]["_err_foo"] == "custom-data"


class TestSinglePassPipeline:
    """Tests for the evaluate-once pattern used by the CLI."""

    def test_shared_evaluated_gives_same_results(self, spark: SparkSession) -> None:
        """filter_errors + explain_errors from the same evaluated DataFrame."""
        df = spark.createDataFrame([_row(id="ok"), _row(id="bad")])
        checks = [
            _scalar_check(
                "id",
                "not_bad",
                F.when(F.col("id") == "bad", F.lit("is bad")),
            ),
        ]
        evaluated = evaluate_checks(df, checks)
        filtered = filter_errors(evaluated, checks)
        explained = explain_errors(evaluated, checks)
        assert filtered.count() == 1
        assert filtered.collect()[0]["id"] == "bad"
        assert explained.count() == 1
        assert explained.collect()[0]["field"] == "id"


class TestNormalizeSuppress:
    def test_empty(self) -> None:
        roots, pairs = _normalize_suppress(())
        assert roots == set()
        assert pairs == set()

    def test_bare_strings(self) -> None:
        roots, pairs = _normalize_suppress(["sources", "theme"])
        assert roots == {"sources", "theme"}
        assert pairs == set()

    def test_tuples(self) -> None:
        roots, pairs = _normalize_suppress([("sources[].confidence", "bounds")])
        assert roots == set()
        assert pairs == {("sources[].confidence", "bounds")}

    def test_check_objects(self, spark: SparkSession) -> None:
        check = Check(
            field="radio_group",
            name="radio_group",
            expr=F.lit(None),
            shape=CheckShape.SCALAR,
            root_field=None,
        )
        roots, pairs = _normalize_suppress([check])
        assert roots == set()
        assert pairs == {("radio_group", "radio_group")}

    def test_mixed(self, spark: SparkSession) -> None:
        check = Check(
            field="radio_group",
            name="radio_group",
            expr=F.lit(None),
            shape=CheckShape.SCALAR,
            root_field=None,
        )
        roots, pairs = _normalize_suppress(
            [
                "sources",
                ("theme", "enum"),
                check,
            ]
        )
        assert roots == {"sources"}
        assert pairs == {("theme", "enum"), ("radio_group", "radio_group")}


# These exercise the populated REGISTRY built by runtime discovery, so they
# require generated expression modules to be present on disk. When the
# generated tree is absent (e.g. a fresh checkout before `make
# generate-pyspark`), the registry is empty and these assertions can't hold.
_requires_generated = pytest.mark.skipif(
    not REGISTRY, reason="requires generated expression modules"
)


@_requires_generated
def test_feature_names_includes_aliases() -> None:
    result = feature_names()
    assert isinstance(result, list)
    assert result == sorted(result)
    assert "building" in result
    assert "segment" in result
    assert "overture.schema.buildings:Building" in result


@_requires_generated
def test_feature_keys_only_canonical() -> None:
    result = feature_keys()
    assert isinstance(result, list)
    assert result == sorted(result)
    assert "overture.schema.buildings:Building" in result
    assert "building" not in result


class TestValidationResult:
    def test_error_rows_delegates_to_filter_errors(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row(id="ok"), _row(id="bad")])
        checks = [
            _scalar_check(
                "id",
                "not_bad",
                F.when(F.col("id") == "bad", F.lit("is bad")),
            ),
        ]
        evaluated = evaluate_checks(df, checks)
        result = ValidationResult(
            evaluated=evaluated,
            checks=checks,
            schema_mismatches=[],
            suppressed_checks=[],
        )
        error_rows = result.error_rows()
        assert error_rows.count() == 1
        assert error_rows.collect()[0]["id"] == "bad"
        assert not any(c.startswith("_err_") for c in error_rows.columns)

    def test_frozen(self) -> None:
        result = ValidationResult(
            evaluated=None,  # type: ignore[arg-type]
            checks=[],
            schema_mismatches=[],
            suppressed_checks=[],
        )
        with pytest.raises(AttributeError):
            result.checks = []  # type: ignore[misc]


_VF_TYPE = "_test_validate_feature"
_VF_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField("theme", StringType(), True),
        StructField("type", StringType(), True),
        StructField("value", StringType(), True),
        StructField("sources", StringType(), True),
    ]
)


def _vf_checks() -> list[Check]:
    return [
        Check(
            field="theme",
            name="enum",
            expr=F.when(F.col("theme") != "test", F.lit("bad theme")),
            shape=CheckShape.SCALAR,
            root_field="theme",
        ),
        Check(
            field="value",
            name="required",
            expr=F.when(F.col("value").isNull(), F.lit("missing")),
            shape=CheckShape.SCALAR,
            root_field="value",
        ),
        Check(
            field="sources_min_length",
            name="min_length",
            expr=F.when(F.length("sources") < 1, F.lit("too short")),
            shape=CheckShape.SCALAR,
            root_field="sources",
        ),
    ]


class TestValidateFeature:
    @pytest.fixture(autouse=True)
    def _register_vf_type(self) -> Iterator[None]:
        REGISTRY[_VF_TYPE] = FeatureValidation(schema=_VF_SCHEMA, checks=_vf_checks)
        yield
        del REGISTRY[_VF_TYPE]

    @pytest.fixture()
    def vf_df(self, spark: SparkSession) -> DataFrame:
        return spark.createDataFrame(
            [Row(id="1", theme="test", type=_VF_TYPE, value="ok", sources="s")],
            schema=_VF_SCHEMA,
        )

    def test_unknown_type_raises_value_error(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row()])
        with pytest.raises(
            ValueError, match="Unknown entry-point alias.*nonexistent_type_xyz"
        ):
            validate_feature(df, "nonexistent_type_xyz")

    def test_basic_validation(self, vf_df: DataFrame) -> None:
        result = validate_feature(vf_df, _VF_TYPE)
        assert isinstance(result, ValidationResult)
        assert result.schema_mismatches == []
        assert len(result.checks) == 3
        assert result.error_rows().count() == 0

    def test_skip_columns_errors_if_present(self, vf_df: DataFrame) -> None:
        with pytest.raises(ValueError, match="skip_columns.*theme.*present"):
            validate_feature(vf_df, _VF_TYPE, skip_columns=["theme"])

    def test_skip_columns_filters_checks(self, spark: SparkSession) -> None:
        schema_no_theme = StructType(
            [f for f in _VF_SCHEMA.fields if f.name != "theme"]
        )
        df = spark.createDataFrame(
            [Row(id="1", type=_VF_TYPE, value="ok", sources="s")],
            schema=schema_no_theme,
        )
        result = validate_feature(df, _VF_TYPE, skip_columns=["theme"])
        check_fields = [c.field for c in result.checks]
        assert "theme" not in check_fields
        assert "value" in check_fields

    def test_skip_columns_filters_schema_mismatches(self, spark: SparkSession) -> None:
        schema_no_theme = StructType(
            [f for f in _VF_SCHEMA.fields if f.name != "theme"]
        )
        df = spark.createDataFrame(
            [Row(id="1", type=_VF_TYPE, value="ok", sources="s")],
            schema=schema_no_theme,
        )
        result = validate_feature(df, _VF_TYPE, skip_columns=["theme"])
        mismatch_fields = [m.path for m in result.schema_mismatches]
        assert "theme" not in mismatch_fields

    def test_ignore_extra_columns(self, spark: SparkSession) -> None:
        schema_extra = StructType(
            _VF_SCHEMA.fields + [StructField("extra_score", StringType(), True)]
        )
        df = spark.createDataFrame(
            [
                Row(
                    id="1",
                    theme="test",
                    type=_VF_TYPE,
                    value="ok",
                    sources="s",
                    extra_score="9",
                )
            ],
            schema=schema_extra,
        )
        result = validate_feature(df, _VF_TYPE, ignore_extra_columns=["extra_score"])
        mismatch_paths = [m.path for m in result.schema_mismatches]
        assert "extra_score" not in mismatch_paths

    def test_suppress_unknown_root_raises(self, vf_df: DataFrame) -> None:
        with pytest.raises(ValueError, match="unknown root fields.*typo_field"):
            validate_feature(vf_df, _VF_TYPE, suppress=["typo_field"])

    def test_suppress_unknown_pair_raises(self, vf_df: DataFrame) -> None:
        with pytest.raises(ValueError, match=r"unknown \(field, name\) pairs"):
            validate_feature(vf_df, _VF_TYPE, suppress=[("theme", "wrong_name")])

    def test_suppress_mixed_unknown_lists_both(self, vf_df: DataFrame) -> None:
        with pytest.raises(ValueError, match="unknown root fields.*unknown"):
            validate_feature(
                vf_df,
                _VF_TYPE,
                suppress=["typo_field", ("theme", "wrong_name")],
            )

    def test_suppress_bare_string(self, vf_df: DataFrame) -> None:
        result = validate_feature(vf_df, _VF_TYPE, suppress=["sources"])
        check_fields = [c.field for c in result.checks]
        assert not any(f.startswith("sources") for f in check_fields)
        assert len(result.suppressed_checks) == 1
        assert result.suppressed_checks[0].field == "sources_min_length"

    def test_suppress_tuple(self, vf_df: DataFrame) -> None:
        result = validate_feature(vf_df, _VF_TYPE, suppress=[("value", "required")])
        check_fields_names = [(c.field, c.name) for c in result.checks]
        assert ("value", "required") not in check_fields_names
        assert len(result.suppressed_checks) == 1

    def test_suppress_check_object(self, vf_df: DataFrame) -> None:
        initial = validate_feature(vf_df, _VF_TYPE)
        target = [c for c in initial.checks if c.name == "required"][0]
        result = validate_feature(vf_df, _VF_TYPE, suppress=[target])
        # Column objects can't be compared with ==, so compare by (field, name)
        result_pairs = [(c.field, c.name) for c in result.checks]
        suppressed_pairs = [(c.field, c.name) for c in result.suppressed_checks]
        assert (target.field, target.name) not in result_pairs
        assert (target.field, target.name) in suppressed_pairs

    def test_evaluated_has_err_columns(self, vf_df: DataFrame) -> None:
        result = validate_feature(vf_df, _VF_TYPE)
        err_cols = [c for c in result.evaluated.columns if c.startswith("_err_")]
        assert len(err_cols) == len(result.checks)

    def test_suppressed_checks_not_in_checks(self, vf_df: DataFrame) -> None:
        result = validate_feature(vf_df, _VF_TYPE, suppress=[("theme", "enum")])
        for sc in result.suppressed_checks:
            assert sc not in result.checks

    def test_all_checks_suppressed(self, vf_df: DataFrame) -> None:
        result = validate_feature(
            vf_df,
            _VF_TYPE,
            suppress=["theme", "value", "sources"],
        )
        assert result.checks == []
        assert result.error_rows().count() == 0
