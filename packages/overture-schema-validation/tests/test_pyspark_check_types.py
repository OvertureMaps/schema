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

    session = (
        SparkSession.builder.master("local[1]")
        .appName("overture-test")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.memory", "512m")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="session")
def spark_sedona():
    """Spark session with Sedona JARs on the classpath."""
    sedona_mod = pytest.importorskip("sedona")

    java17 = "/Library/Java/JavaVirtualMachines/java-runtime-17/Contents/Home"
    if os.path.isdir(java17):
        os.environ["JAVA_HOME"] = java17

    try:
        from sedona.spark import SedonaContext

        session = (
            SedonaContext.builder()
            .master("local[1]")
            .appName("overture-sedona-test")
            .config("spark.ui.enabled", "false")
            .config("spark.driver.memory", "512m")
            .getOrCreate()
        )
        session = SedonaContext.create(session)
    except Exception as exc:
        pytest.skip(f"Sedona setup failed: {exc}")

    yield session
    session.stop()
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


# Skip geometry_type — requires Sedona which may not be installed
_CASES_NO_GEOM = {k: v for k, v in CASES.items() if k != "geometry_type"}


@pytest.mark.parametrize("key", _CASES_NO_GEOM)
def test_check_type(key: str, spark: SparkSession) -> None:
    case = CASES[key]
    spec = DatasetSpec(
        name="test",
        rules=case.rules,
    )
    report = _run(spec, case, spark)
    _assert_violations(report, case.violations)


@pytest.mark.parametrize("key", ["geometry_type"])
def test_check_type_geometry(key: str, spark_sedona: SparkSession) -> None:
    """Test geometry_type check (requires Sedona)."""
    case = CASES[key]
    spec = DatasetSpec(
        name="test",
        rules=case.rules,
    )
    report = _run(spec, case, spark_sedona)
    _assert_violations(report, case.violations)
