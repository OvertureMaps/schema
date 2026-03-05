"""Per-CheckType end-to-end validation tests using the PySpark backend."""

from __future__ import annotations

import os

import pytest
from check_type_cases import CASES
from overture.schema.validation.ir import DatasetSpec
from overture.schema.validation.report import ValidationReport

pyspark = pytest.importorskip("pyspark")

from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    # PySpark 3.5 requires Java <= 21; prefer 17 if available
    java17 = "/Library/Java/JavaVirtualMachines/java-runtime-17/Contents/Home"
    if os.path.isdir(java17):
        os.environ["JAVA_HOME"] = java17

    from overture.schema.validation.pyspark import create_spark_session

    try:
        session = create_spark_session(
            app_name="overture-test",
            **{
                "spark.master": "local[1]",
                "spark.ui.enabled": "false",
                "spark.driver.memory": "512m",
            },
        )
    except Exception as exc:
        pytest.skip(f"Spark session setup failed: {exc}")

    yield session
    session.stop()


def _run(spec: DatasetSpec, case, spark: SparkSession) -> ValidationReport:
    """Create a DataFrame from ExampleData and validate it against the spec."""
    from overture.schema.validation.pyspark import validate

    df = spark.createDataFrame(case.data.rows, case.data.columns)
    return validate(spec, df, spark)


def _assert_violations(
    report: ValidationReport, expected: dict[str, list[str]]
) -> None:
    """Assert that only the expected rules have violations, with matching IDs."""
    actual: dict[str, list] = {}
    for r in report.results:
        actual.setdefault(r.name, []).append(r.violating_id)
    actual_sorted = {k: sorted(v) for k, v in actual.items()}
    expected_sorted = {k: sorted(v) for k, v in expected.items()}
    assert actual_sorted == expected_sorted


@pytest.mark.parametrize("key", CASES)
def test_check_type(key: str, spark: SparkSession) -> None:
    case = CASES[key]
    spec = DatasetSpec(
        name="test",
        rules=case.rules,
    )
    report = _run(spec, case, spark)
    _assert_violations(report, case.violations)
