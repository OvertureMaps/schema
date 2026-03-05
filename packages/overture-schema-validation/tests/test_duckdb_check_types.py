"""Per-CheckType end-to-end validation tests using the DuckDB backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from check_type_cases import CASES, ExampleData
from overture.schema.validation.extract import extract
from overture.schema.validation.ir import DatasetSpec
from overture.schema.validation.report import ValidationReport

duckdb = pytest.importorskip("duckdb")

from overture.schema.validation.duckdb import connect as duckdb_connect


def _sql_value(value: Any, col_type: type | None) -> str:
    """Convert a Python value to a DuckDB SQL literal."""
    if value is None:
        if col_type is None:
            return "NULL"
        if col_type is bool:
            return "CAST(NULL AS BOOLEAN)"
        if col_type is int:
            return "CAST(NULL AS INTEGER)"
        if col_type is float:
            return "CAST(NULL AS DOUBLE)"
        if col_type is bytes:
            return "CAST(NULL AS BLOB)"
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    if isinstance(value, bytes):
        hex_per_byte = "".join(f"\\x{b:02x}" for b in value)
        return f"'{hex_per_byte}'::BLOB"
    if isinstance(value, list):
        inner = ", ".join(_sql_value(v, type(v) if v is not None else None) for v in value)
        return f"[{inner}]"
    return str(value)


def _infer_col_type(data: ExampleData, col_idx: int) -> type | None:
    """Infer the Python type for a column from its non-None values."""
    for row in data.rows:
        v = row[col_idx]
        if v is not None:
            return type(v)
    return None


def _to_duckdb_sql(data: ExampleData) -> str:
    """Generate CREATE TABLE SQL from ExampleData."""
    col_types = [_infer_col_type(data, i) for i in range(len(data.columns))]

    selects = []
    for row in data.rows:
        cols = []
        for i, val in enumerate(row):
            cols.append(f"{_sql_value(val, col_types[i])} AS {data.columns[i]}")
        selects.append("SELECT " + ", ".join(cols))

    return "CREATE TABLE _tbl AS " + "\nUNION ALL ".join(selects)


def _run(spec: DatasetSpec, case, tmp_path: Path) -> ValidationReport:
    """Create a parquet file from ExampleData and validate it against the spec."""
    from overture.schema.validation.duckdb import validate

    sql = _to_duckdb_sql(case.data)
    has_blob = any(
        isinstance(val, bytes)
        for row in case.data.rows
        for val in row
    )

    path = str(tmp_path / "test.parquet")
    c = duckdb_connect()
    if has_blob:
        c.execute("INSTALL spatial; LOAD spatial;")
    c.execute(sql)
    c.execute(f"COPY _tbl TO '{path}' (FORMAT PARQUET)")
    return validate(spec, path, duckdb_connect())


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
    report = _run(spec, case, tmp_path)
    _assert_violations(report, case.violations)
