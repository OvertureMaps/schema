"""Tests for validation pipeline."""

import re
from collections.abc import Iterator

import pytest
from overture.schema.pyspark._registry import REGISTRY
from overture.schema.pyspark.check import Check, CheckShape
from overture.schema.pyspark.expressions.column_patterns import map_values_check
from overture.schema.pyspark.validate import (
    ValidationResult,
    _normalize_suppress,
    evaluate_checks,
    explain_errors,
    filter_errors,
    model_keys,
    model_names,
    validate_model,
)
from pyspark.sql import DataFrame, Row, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    IntegerType,
    MapType,
    StringType,
    StructField,
    StructType,
)

from ._support.registry import register_model


def _scalar_check(
    field: str, name: str, expr: F.Column, *, read_columns: frozenset[str] | None = None
) -> Check:
    return Check(
        field=field,
        name=name,
        expr=expr,
        shape=CheckShape.SCALAR,
        read_columns=read_columns if read_columns is not None else frozenset({field}),
    )


def _array_check(
    field: str, name: str, expr: F.Column, *, read_columns: frozenset[str] | None = None
) -> Check:
    return Check(
        field=field,
        name=name,
        expr=expr,
        shape=CheckShape.ARRAY,
        read_columns=read_columns if read_columns is not None else frozenset({field}),
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


class TestReservedColumnCollisions:
    """Working/output columns must not collide with user input columns.

    `evaluate_checks` appends `_err_<int>` columns; `explain_errors`
    materializes `_idx`/`_errors` scratch columns and emits its
    `field`/`check`/`message` output. An input column sharing any of
    these names yields duplicate attributes -> AMBIGUOUS_REFERENCE (or
    silent loss via the `_err_<int>` strip), so both entry points reject
    the collision up front with a clear error.
    """

    def test_evaluate_checks_rejects_err_column(self, spark: SparkSession) -> None:
        df = spark.createDataFrame([_row(_err_0="dup")])
        checks = [_scalar_check("value", "required", F.lit("fail"))]
        with pytest.raises(ValueError, match=r"_err_0.*rename or drop"):
            evaluate_checks(df, checks)

    def test_evaluate_checks_allows_non_digit_err_column(
        self, spark: SparkSession
    ) -> None:
        # Only `_err_<digits>` is reserved; `_err_foo` is a user column.
        df = spark.createDataFrame([_row(_err_foo="ok")])
        checks = [_scalar_check("value", "required", F.lit("fail"))]
        evaluated = evaluate_checks(df, checks)
        assert "_err_foo" in evaluated.columns

    def test_evaluate_checks_rejects_reevaluation(self, spark: SparkSession) -> None:
        # The realistic trigger: a persisted `result.evaluated` (which
        # carries `_err_0..N`) fed back through validation.
        df = spark.createDataFrame([_row()])
        checks = [_scalar_check("value", "required", F.lit("fail"))]
        evaluated = evaluate_checks(df, checks)
        with pytest.raises(ValueError, match="_err_0"):
            evaluate_checks(evaluated, checks)

    @pytest.mark.parametrize(
        "reserved", ["_idx", "_errors", "field", "check", "message"]
    )
    def test_explain_errors_rejects_reserved_input_column(
        self, spark: SparkSession, reserved: str
    ) -> None:
        df = spark.createDataFrame([_row(**{reserved: "dup"})])
        checks = [_scalar_check("value", "required", F.lit("fail"))]
        evaluated = evaluate_checks(df, checks)
        with pytest.raises(ValueError, match=re.escape(reserved)):
            explain_errors(evaluated, checks)

    def test_explain_errors_rejects_reserved_with_no_checks(
        self, spark: SparkSession
    ) -> None:
        # The n == 0 branch also emits field/check/message, so the guard
        # must precede it.
        df = spark.createDataFrame([_row(field="dup")])
        with pytest.raises(ValueError, match="field"):
            explain_errors(df, [])


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
            read_columns=frozenset(),
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
            read_columns=frozenset(),
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
def test_model_names_includes_aliases() -> None:
    result = model_names()
    assert isinstance(result, list)
    assert result == sorted(result)
    assert "building" in result
    assert "segment" in result
    assert "overture.schema.buildings:Building" in result


@_requires_generated
def test_model_keys_only_canonical() -> None:
    result = model_keys()
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
_VF_NESTED_TYPE = "_test_validate_nested"
_VF_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField("theme", StringType(), True),
        StructField("type", StringType(), True),
        StructField("value", StringType(), True),
        StructField("sources", StringType(), True),
    ]
)
_VF_NESTED_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField(
            "bbox",
            StructType(
                [
                    StructField("xmin", StringType(), True),
                    StructField("xmax", StringType(), True),
                ]
            ),
            True,
        ),
    ]
)


# `_VF_ARRAY_*` exercises a missing field *inside* an array element struct.
# `compare_schemas` encodes the array step as `sources[].confidence`; the
# root-derivation in validate_model must strip the `[]` marker so the
# dropped-check root matches the check's read column (`sources`).
_VF_ARRAY_TYPE = "_test_validate_array_nested"
_VF_ARRAY_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField(
            "sources",
            ArrayType(
                StructType(
                    [
                        StructField("dataset", StringType(), True),
                        StructField("confidence", DoubleType(), True),
                    ]
                )
            ),
            True,
        ),
    ]
)


def _vf_array_checks() -> list[Check]:
    return [
        Check(
            field="sources",
            name="confidence_bounds",
            expr=F.transform(
                "sources",
                lambda el: F.when(el["confidence"] > 1.0, F.lit("confidence too high")),
            ),
            shape=CheckShape.ARRAY,
            read_columns=frozenset({"sources"}),
        ),
    ]


# `_VF_MODEL_*` exercises a model-level constraint that reads several columns
# directly. When any column it reads is skipped/absent, the exclusion filter
# must drop the model check too.
_VF_MODEL_TYPE = "_test_validate_model_constraint"
_VF_MODEL_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField("primary_name", StringType(), True),
        StructField("alt_name", StringType(), True),
    ]
)


def _vf_model_checks() -> list[Check]:
    return [
        Check(
            field="require_any_of",
            name="require_any_of",
            expr=F.when(
                F.col("primary_name").isNull() & F.col("alt_name").isNull(),
                F.lit("at least one name required"),
            ),
            shape=CheckShape.SCALAR,
            read_columns=frozenset({"primary_name", "alt_name"}),
        ),
    ]


# `_VF_MAP_*` exercises a map key/value check, whose expression dereferences
# the map column by name (`map_values_check("license_priority", ...)`). Skipping
# or omitting that column must drop the check, mirroring the array path, rather
# than leaving an unresolvable map projection behind.
_VF_MAP_TYPE = "_test_validate_map_check"
_VF_MAP_SCHEMA = StructType(
    [
        StructField("id", StringType(), True),
        StructField("license_priority", MapType(StringType(), IntegerType()), True),
    ]
)


def _vf_map_checks() -> list[Check]:
    return [
        Check(
            field="license_priority{value}",
            name="bounds",
            expr=map_values_check(
                "license_priority", lambda v: F.when(v < 0, F.lit("negative"))
            ),
            shape=CheckShape.ARRAY,
            read_columns=frozenset({"license_priority"}),
        ),
    ]


def _vf_checks() -> list[Check]:
    return [
        Check(
            field="theme",
            name="enum",
            expr=F.when(F.col("theme") != "test", F.lit("bad theme")),
            shape=CheckShape.SCALAR,
            read_columns=frozenset({"theme"}),
        ),
        Check(
            field="value",
            name="required",
            expr=F.when(F.col("value").isNull(), F.lit("missing")),
            shape=CheckShape.SCALAR,
            read_columns=frozenset({"value"}),
        ),
        Check(
            field="sources_min_length",
            name="min_length",
            expr=F.when(F.length("sources") < 1, F.lit("too short")),
            shape=CheckShape.SCALAR,
            read_columns=frozenset({"sources"}),
        ),
    ]


class TestValidateFeature:
    @pytest.fixture(autouse=True)
    def _register_vf_type(self) -> Iterator[None]:
        with register_model(_VF_TYPE, _VF_SCHEMA, _vf_checks):
            yield

    @pytest.fixture()
    def _register_nested_type(self) -> Iterator[None]:
        with register_model(_VF_NESTED_TYPE, _VF_NESTED_SCHEMA, lambda: []):
            yield

    @pytest.fixture()
    def _register_map_type(self) -> Iterator[None]:
        with register_model(_VF_MAP_TYPE, _VF_MAP_SCHEMA, _vf_map_checks):
            yield

    @pytest.fixture()
    def _register_array_type(self) -> Iterator[None]:
        with register_model(_VF_ARRAY_TYPE, _VF_ARRAY_SCHEMA, _vf_array_checks):
            yield

    @pytest.fixture()
    def _register_model_type(self) -> Iterator[None]:
        with register_model(_VF_MODEL_TYPE, _VF_MODEL_SCHEMA, _vf_model_checks):
            yield

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
            validate_model(df, "nonexistent_type_xyz")

    def test_basic_validation(self, vf_df: DataFrame) -> None:
        result = validate_model(vf_df, _VF_TYPE)
        assert isinstance(result, ValidationResult)
        assert result.schema_mismatches == []
        assert len(result.checks) == 3
        assert result.error_rows().count() == 0

    def test_skip_columns_errors_if_present(self, vf_df: DataFrame) -> None:
        with pytest.raises(ValueError, match="skip_columns.*theme.*present"):
            validate_model(vf_df, _VF_TYPE, skip_columns=["theme"])

    def test_skip_columns_filters_checks(self, spark: SparkSession) -> None:
        schema_no_theme = StructType(
            [f for f in _VF_SCHEMA.fields if f.name != "theme"]
        )
        df = spark.createDataFrame(
            [Row(id="1", type=_VF_TYPE, value="ok", sources="s")],
            schema=schema_no_theme,
        )
        result = validate_model(df, _VF_TYPE, skip_columns=["theme"])
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
        result = validate_model(df, _VF_TYPE, skip_columns=["theme"])
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
        result = validate_model(df, _VF_TYPE, ignore_extra_columns=["extra_score"])
        mismatch_paths = [m.path for m in result.schema_mismatches]
        assert "extra_score" not in mismatch_paths

    def test_suppress_unknown_root_raises(self, vf_df: DataFrame) -> None:
        with pytest.raises(ValueError, match="unknown root fields.*typo_field"):
            validate_model(vf_df, _VF_TYPE, suppress=["typo_field"])

    def test_suppress_unknown_pair_raises(self, vf_df: DataFrame) -> None:
        with pytest.raises(ValueError, match=r"unknown \(field, name\) pairs"):
            validate_model(vf_df, _VF_TYPE, suppress=[("theme", "wrong_name")])

    def test_suppress_mixed_unknown_lists_both(self, vf_df: DataFrame) -> None:
        with pytest.raises(ValueError, match="unknown root fields.*unknown"):
            validate_model(
                vf_df,
                _VF_TYPE,
                suppress=["typo_field", ("theme", "wrong_name")],
            )

    def test_suppress_bare_string(self, vf_df: DataFrame) -> None:
        result = validate_model(vf_df, _VF_TYPE, suppress=["sources"])
        check_fields = [c.field for c in result.checks]
        assert not any(f.startswith("sources") for f in check_fields)
        assert len(result.suppressed_checks) == 1
        assert result.suppressed_checks[0].field == "sources_min_length"

    def test_suppress_tuple(self, vf_df: DataFrame) -> None:
        result = validate_model(vf_df, _VF_TYPE, suppress=[("value", "required")])
        check_fields_names = [(c.field, c.name) for c in result.checks]
        assert ("value", "required") not in check_fields_names
        assert len(result.suppressed_checks) == 1

    def test_suppress_check_object(self, vf_df: DataFrame) -> None:
        initial = validate_model(vf_df, _VF_TYPE)
        target = [c for c in initial.checks if c.name == "required"][0]
        result = validate_model(vf_df, _VF_TYPE, suppress=[target])
        # Column objects can't be compared with ==, so compare by (field, name)
        result_pairs = [(c.field, c.name) for c in result.checks]
        suppressed_pairs = [(c.field, c.name) for c in result.suppressed_checks]
        assert (target.field, target.name) not in result_pairs
        assert (target.field, target.name) in suppressed_pairs

    def test_evaluated_has_err_columns(self, vf_df: DataFrame) -> None:
        result = validate_model(vf_df, _VF_TYPE)
        err_cols = [c for c in result.evaluated.columns if c.startswith("_err_")]
        assert len(err_cols) == len(result.checks)

    def test_suppressed_checks_not_in_checks(self, vf_df: DataFrame) -> None:
        result = validate_model(vf_df, _VF_TYPE, suppress=[("theme", "enum")])
        for sc in result.suppressed_checks:
            assert sc not in result.checks

    def test_all_checks_suppressed(self, vf_df: DataFrame) -> None:
        result = validate_model(
            vf_df,
            _VF_TYPE,
            suppress=["theme", "value", "sources"],
        )
        assert result.checks == []
        assert result.error_rows().count() == 0

    def test_missing_column_does_not_raise(self, spark: SparkSession) -> None:
        # A DataFrame missing a required column causes AnalysisException when
        # evaluate_checks references that column.  validate_model must detect
        # structurally absent columns via schema_mismatches and silently drop
        # the corresponding checks before calling evaluate_checks -- mirroring
        # the skip_columns path.
        schema_no_theme = StructType(
            [f for f in _VF_SCHEMA.fields if f.name != "theme"]
        )
        df = spark.createDataFrame(
            [Row(id="1", type=_VF_TYPE, value="ok", sources="s")],
            schema=schema_no_theme,
        )
        result = validate_model(df, _VF_TYPE)
        # Must not raise -- returns normally
        assert isinstance(result, ValidationResult)
        # Missing column is reported as a schema mismatch
        mismatch_paths = [m.path for m in result.schema_mismatches]
        assert "theme" in mismatch_paths
        # No kept check may read the absent column
        assert all("theme" not in c.read_columns for c in result.checks)
        # Absent-column checks are silently dropped, not tracked in suppressed
        assert all("theme" not in c.read_columns for c in result.suppressed_checks)

    def test_absent_columns_exposed_on_result(self, spark: SparkSession) -> None:
        # validate_model must expose absent_columns as an ordered tuple so
        # callers (e.g. CLI) don't need to re-derive it from schema_mismatches.
        schema_no_theme = StructType(
            [f for f in _VF_SCHEMA.fields if f.name != "theme"]
        )
        df = spark.createDataFrame(
            [Row(id="1", type=_VF_TYPE, value="ok", sources="s")],
            schema=schema_no_theme,
        )
        result = validate_model(df, _VF_TYPE)
        assert result.absent_columns == ("theme",)

    def test_absent_columns_empty_when_schema_matches(self, vf_df: DataFrame) -> None:
        result = validate_model(vf_df, _VF_TYPE)
        assert result.absent_columns == ()

    def test_absent_columns_ordered(self, spark: SparkSession) -> None:
        # compare_schemas iterates actual fields first, then expected-only fields
        # appended in their expected schema order.  value precedes sources in
        # _VF_SCHEMA, so absent_columns must be exactly ("value", "sources").
        schema_no_value_no_sources = StructType(
            [f for f in _VF_SCHEMA.fields if f.name not in {"value", "sources"}]
        )
        df = spark.createDataFrame(
            [Row(id="1", theme="test", type=_VF_TYPE)],
            schema=schema_no_value_no_sources,
        )
        result = validate_model(df, _VF_TYPE)
        assert result.absent_columns == ("value", "sources")

    def test_absent_columns_deduplicated(
        self, spark: SparkSession, _register_nested_type: None
    ) -> None:
        # A nested struct column with multiple missing sub-fields must produce
        # exactly one root entry in absent_columns, not one per sub-field.
        # Schema: id + bbox(xmin, xmax) in the expected schema.
        # Data:   id + bbox(id) -- both xmin and xmax are absent sub-fields,
        # so compare_schemas emits bbox.xmin and bbox.xmax as missing; both
        # share root "bbox" and must collapse to a single entry.
        bbox_partial = StructType([StructField("id", StringType(), True)])
        data_schema = StructType(
            [
                StructField("id", StringType(), True),
                StructField("bbox", bbox_partial, True),
            ]
        )
        df = spark.createDataFrame(
            [Row(id="1", bbox=Row(id="x"))],
            schema=data_schema,
        )
        result = validate_model(df, _VF_NESTED_TYPE)
        # Two sub-field mismatches (bbox.xmin, bbox.xmax) collapse to one root
        assert result.absent_columns == ("bbox",)

    def test_missing_array_nested_field_does_not_raise(
        self, spark: SparkSession, _register_array_type: None
    ) -> None:
        # A field absent from an array element struct yields a mismatch path
        # carrying the array step marker (`sources[].confidence`).  The absent
        # root must be derived by stripping that marker so it matches the
        # top-level column (`sources`); the column's checks are then dropped,
        # mirroring the top-level graceful-degradation path, rather than
        # evaluating an expression that dereferences the absent sub-field.
        data_schema = StructType(
            [
                StructField("id", StringType(), True),
                StructField(
                    "sources",
                    ArrayType(StructType([StructField("dataset", StringType(), True)])),
                    True,
                ),
            ]
        )
        df = spark.createDataFrame(
            [Row(id="1", sources=[Row(dataset="osm")])],
            schema=data_schema,
        )
        result = validate_model(df, _VF_ARRAY_TYPE)
        result.row_counts()  # forces evaluation; raises if the check is kept
        assert result.absent_columns == ("sources",)
        assert all("sources" not in c.read_columns for c in result.checks)

    def test_skip_columns_with_map_check_does_not_raise(
        self, spark: SparkSession, _register_map_type: None
    ) -> None:
        # A map key/value check dereferences its map column by name, exactly
        # like an array check. Skipping that column must drop the check so
        # validation degrades gracefully instead of leaving an unresolvable
        # map projection (`map_values_check("license_priority", ...)`) behind.
        data_schema = StructType(
            [f for f in _VF_MAP_SCHEMA.fields if f.name != "license_priority"]
        )
        df = spark.createDataFrame([Row(id="1")], schema=data_schema)
        result = validate_model(df, _VF_MAP_TYPE, skip_columns=["license_priority"])
        result.row_counts()  # forces evaluation; raises if the map check is kept
        assert all("license_priority" not in c.read_columns for c in result.checks)

    def test_suppress_by_model_only_column(
        self, spark: SparkSession, _register_model_type: None
    ) -> None:
        # A column read only by a model-level check is still a valid suppress
        # target: suppression is symmetric with absence -- a column droppable
        # when absent is suppressible by name.  Suppressing it drops the model
        # check (and records it as suppressed, not silently absent).
        df = spark.createDataFrame(
            [Row(id="1", primary_name="p", alt_name="a")],
            schema=_VF_MODEL_SCHEMA,
        )
        result = validate_model(df, _VF_MODEL_TYPE, suppress=["primary_name"])
        assert all(c.name != "require_any_of" for c in result.checks)
        assert any(c.name == "require_any_of" for c in result.suppressed_checks)

    def test_skip_columns_with_model_constraint_does_not_raise(
        self, spark: SparkSession, _register_model_type: None
    ) -> None:
        # Model-level checks read several columns directly.  Skipping a column a
        # model constraint reads must drop the model check too, so validation
        # degrades gracefully instead of leaving an unresolvable column
        # reference behind.
        data_schema = StructType(
            [f for f in _VF_MODEL_SCHEMA.fields if f.name != "primary_name"]
        )
        df = spark.createDataFrame(
            [Row(id="1", alt_name="x")],
            schema=data_schema,
        )
        result = validate_model(df, _VF_MODEL_TYPE, skip_columns=["primary_name"])
        result.row_counts()  # forces evaluation; raises if the model check is kept
        assert all(c.name != "require_any_of" for c in result.checks)
