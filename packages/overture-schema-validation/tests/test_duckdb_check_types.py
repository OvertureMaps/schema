"""Per-CheckType end-to-end validation tests using the DuckDB backend."""

from __future__ import annotations

from pathlib import Path

import pytest
from check_type_cases import CASES
from overture.schema.validation.extract import extract
from overture.schema.validation.ir import DatasetSpec
from overture.schema.validation.report import ValidationReport

duckdb = pytest.importorskip("duckdb")


def _run(spec: DatasetSpec, create_sql: str, tmp_path: Path) -> ValidationReport:
    """Create a parquet file from SQL and validate it against the spec."""
    from overture.schema.validation.duckdb import validate

    path = str(tmp_path / "test.parquet")
    c = duckdb.connect()
    for stmt in create_sql.split(";"):
        stmt = stmt.strip()
        if stmt:
            c.execute(stmt)
    c.execute(f"COPY _tbl TO '{path}' (FORMAT PARQUET)")
    return validate(spec, path, duckdb.connect())


def _assert_violations(
    report: ValidationReport, expected: dict[str, list[int]]
) -> None:
    """Assert that only the expected rules have violations, with matching IDs."""
    actual: dict[str, list] = {}
    for r in report.results:
        actual.setdefault(r.name, []).append(r.violating_id)
    actual_sorted = {k: sorted(v) for k, v in actual.items()}
    expected_sorted = {k: sorted(v) for k, v in expected.items()}
    assert actual_sorted == expected_sorted


@pytest.mark.parametrize("key", CASES)
def test_check_type(key: str, tmp_path: Path) -> None:
    case = CASES[key]
    spec = DatasetSpec(
        name="test",
        rules=case.rules,
    )
    report = _run(spec, case.create_sql, tmp_path)
    _assert_violations(report, case.violations)
