"""Tests for the DuckDB validation backend."""

from __future__ import annotations

import pytest

from overture.schema.validation.ir import (
    CheckType,
    Condition,
    DatasetSpec,
    Rule,
    Severity,
)
from overture.schema.validation.duckdb import compile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec(rules: list[Rule], id_column: str = "id", name: str = "test") -> DatasetSpec:
    return DatasetSpec(name=name, id_column=id_column, rules=rules)


def _rule(
    check: CheckType,
    column: str | None = "col",
    columns: list[str] | None = None,
    value=None,
    other_column: str | None = None,
    list_columns: list[str] | None = None,
    when: Condition | None = None,
    severity: Severity = Severity.ERROR,
    name: str = "test.rule",
) -> Rule:
    return Rule(
        name=name,
        column=column,
        columns=columns,
        check=check,
        value=value,
        other_column=other_column,
        list_columns=list_columns,
        when=when,
        severity=severity,
    )


# ---------------------------------------------------------------------------
# compile() — unit tests (no duckdb needed)
# ---------------------------------------------------------------------------

# --- Structure ---


def test_compile_cte_structure():
    sql = compile(_spec([_rule(CheckType.NOT_NULL)]), "/data/test.parquet")
    assert "WITH src AS (" in sql
    assert "read_parquet($1)" in sql


def test_compile_empty_rules():
    sql = compile(_spec([]), "/data/test.parquet")
    assert "WHERE FALSE" in sql
    assert "NULL AS id" in sql
    assert "NULL AS name" in sql


def test_compile_unpivot_structure():
    rules = [
        _rule(CheckType.NOT_NULL, name="r1"),
        _rule(CheckType.IS_NULL, name="r2"),
    ]
    sql = compile(_spec(rules), "/data/test.parquet")
    assert "UNPIVOT" in sql
    assert "_meta" in sql
    assert "UNION ALL" not in sql
    assert "_r0" in sql
    assert "_r1" in sql


def test_compile_parquet_path_is_parameterized():
    sql = compile(_spec([_rule(CheckType.NOT_NULL)]), "/data/it's a file.parquet")
    assert "read_parquet($1)" in sql
    assert "it's" not in sql


def test_compile_dot_notation_column():
    sql = compile(
        _spec([_rule(CheckType.NOT_NULL, column="sources.dataset")]),
        "/data/test.parquet",
    )
    assert '"sources"."dataset"' in sql


def test_compile_severity_in_output():
    sql = compile(
        _spec([_rule(CheckType.NOT_NULL, severity=Severity.WARNING)]),
        "f.parquet",
    )
    assert "'warning'" in sql


def test_compile_value_with_quotes():
    sql = compile(
        _spec([_rule(CheckType.EQ, value="it's")]), "f.parquet"
    )
    assert "it''s" in sql


def test_compile_custom_id_column():
    sql = compile(
        _spec([_rule(CheckType.NOT_NULL)], id_column="feature_id"),
        "f.parquet",
    )
    assert '"feature_id" AS id' in sql


# --- Scalar checks ---


def test_compile_not_null():
    sql = compile(_spec([_rule(CheckType.NOT_NULL)]), "f.parquet")
    assert '"col" IS NULL' in sql


def test_compile_is_null():
    sql = compile(_spec([_rule(CheckType.IS_NULL)]), "f.parquet")
    assert '"col" IS NOT NULL' in sql


def test_compile_gt():
    sql = compile(_spec([_rule(CheckType.GT, value=5)]), "f.parquet")
    assert '"col" IS NOT NULL AND NOT ("col" > 5)' in sql


def test_compile_gte():
    sql = compile(_spec([_rule(CheckType.GTE, value=5)]), "f.parquet")
    assert '"col" IS NOT NULL AND NOT ("col" >= 5)' in sql


def test_compile_lt():
    sql = compile(_spec([_rule(CheckType.LT, value=10)]), "f.parquet")
    assert '"col" IS NOT NULL AND NOT ("col" < 10)' in sql


def test_compile_lte():
    sql = compile(_spec([_rule(CheckType.LTE, value=10)]), "f.parquet")
    assert '"col" IS NOT NULL AND NOT ("col" <= 10)' in sql


def test_compile_eq():
    sql = compile(_spec([_rule(CheckType.EQ, value="abc")]), "f.parquet")
    assert '"col" IS NOT NULL AND NOT ("col" = \'abc\')' in sql


def test_compile_neq():
    sql = compile(_spec([_rule(CheckType.NEQ, value="x")]), "f.parquet")
    assert '"col" IS NOT NULL AND "col" = \'x\'' in sql


def test_compile_between():
    sql = compile(_spec([_rule(CheckType.BETWEEN, value=[1, 10])]), "f.parquet")
    assert '"col" IS NOT NULL AND NOT ("col" BETWEEN 1 AND 10)' in sql


def test_compile_in():
    sql = compile(_spec([_rule(CheckType.IN, value=["a", "b"])]), "f.parquet")
    assert "\"col\" IS NOT NULL AND NOT (\"col\" IN ('a', 'b'))" in sql


def test_compile_not_in():
    sql = compile(_spec([_rule(CheckType.NOT_IN, value=["x"])]), "f.parquet")
    assert "\"col\" IS NOT NULL AND NOT (\"col\" NOT IN ('x'))" in sql


def test_compile_pattern():
    sql = compile(_spec([_rule(CheckType.PATTERN, value="^[A-Z]+$")]), "f.parquet")
    assert "regexp_matches" in sql
    assert "^[A-Z]+$" in sql


def test_compile_min_length():
    sql = compile(_spec([_rule(CheckType.MIN_LENGTH, value=3)]), "f.parquet")
    assert "NOT (len(\"col\") >= 3)" in sql


def test_compile_max_length():
    sql = compile(_spec([_rule(CheckType.MAX_LENGTH, value=100)]), "f.parquet")
    assert "NOT (len(\"col\") <= 100)" in sql


def test_compile_is_type():
    sql = compile(_spec([_rule(CheckType.IS_TYPE, value="integer")]), "f.parquet")
    assert "typeof" in sql
    assert "'INTEGER'" in sql
    assert "'BIGINT'" in sql


def test_compile_column_lt():
    sql = compile(
        _spec([_rule(CheckType.COLUMN_LT, column="a", other_column="b")]),
        "f.parquet",
    )
    assert '"a" IS NOT NULL AND "b" IS NOT NULL' in sql
    assert '"a" < "b"' in sql


def test_compile_column_lte():
    sql = compile(
        _spec([_rule(CheckType.COLUMN_LTE, column="a", other_column="b")]),
        "f.parquet",
    )
    assert '"a" <= "b"' in sql


def test_compile_column_eq():
    sql = compile(
        _spec([_rule(CheckType.COLUMN_EQ, column="a", other_column="b")]),
        "f.parquet",
    )
    assert '"a" = "b"' in sql


def test_compile_geometry_type():
    sql = compile(
        _spec([_rule(CheckType.GEOMETRY_TYPE, value=["Point", "MultiPoint"])]),
        "f.parquet",
    )
    assert "ST_GeometryType" in sql
    assert "ST_GeomFromWKB" in sql
    assert "'POINT'" in sql
    assert "'MULTIPOINT'" in sql


# --- Multi-field checks ---


def test_compile_any_of():
    sql = compile(
        _spec(
            [
                _rule(
                    CheckType.ANY_OF,
                    column=None,
                    columns=["a", "b", "c"],
                )
            ]
        ),
        "f.parquet",
    )
    assert '"a" IS NULL AND "b" IS NULL AND "c" IS NULL' in sql


def test_compile_exactly_one_of():
    sql = compile(
        _spec(
            [
                _rule(
                    CheckType.EXACTLY_ONE_OF,
                    column=None,
                    columns=["x", "y"],
                )
            ]
        ),
        "f.parquet",
    )
    assert "CASE WHEN" in sql
    assert "!= 1" in sql


# --- Unique ---


def test_compile_unique_scalar():
    rules = [_rule(CheckType.UNIQUE, name="u1")]
    sql = compile(_spec(rules), "f.parquet")
    assert "list_distinct" in sql


def test_compile_unique_list():
    # Unique checks intra-row list uniqueness via list_distinct
    rules = [
        _rule(CheckType.NOT_NULL, list_columns=["col"], name="r1"),
        _rule(CheckType.UNIQUE, name="u1"),
    ]
    sql = compile(_spec(rules), "f.parquet")
    assert "list_distinct" in sql


# --- list_columns ---


def test_compile_list_columns_not_null():
    sql = compile(
        _spec([_rule(CheckType.NOT_NULL, list_columns=["col"])]), "f.parquet"
    )
    assert "list_filter" in sql
    assert "x0 IS NULL" in sql


def test_compile_list_columns_is_null():
    sql = compile(
        _spec([_rule(CheckType.IS_NULL, list_columns=["col"])]), "f.parquet"
    )
    assert "list_filter" in sql
    assert "x0 IS NOT NULL" in sql


def test_compile_list_columns_gt():
    sql = compile(
        _spec([_rule(CheckType.GT, value=0, list_columns=["col"])]), "f.parquet"
    )
    assert "list_filter" in sql
    assert "x0 IS NOT NULL AND NOT (x0 > 0)" in sql


def test_compile_list_columns_in():
    sql = compile(
        _spec([_rule(CheckType.IN, value=["a", "b"], list_columns=["col"])]),
        "f.parquet",
    )
    assert "list_filter" in sql
    assert "x0 IN ('a', 'b')" in sql


def test_compile_list_columns_pattern():
    sql = compile(
        _spec([_rule(CheckType.PATTERN, value="^\\d+$", list_columns=["col"])]),
        "f.parquet",
    )
    assert "list_filter" in sql
    assert "regexp_matches(x0" in sql


# --- list_columns with struct access (list-of-structs) ---


def test_compile_list_columns_struct_not_null():
    """list_columns with struct access inside list_filter."""
    sql = compile(
        _spec([_rule(CheckType.NOT_NULL, column="items.value",
                      list_columns=["items"])]),
        "f.parquet",
    )
    assert 'list_filter("items"' in sql
    assert 'x0."value" IS NULL' in sql
    assert '"items" IS NOT NULL' in sql


def test_compile_list_columns_struct_gt():
    """list_columns with a value check uses struct access."""
    sql = compile(
        _spec([_rule(CheckType.GT, column="items.score", value=0,
                      list_columns=["items"])]),
        "f.parquet",
    )
    assert 'list_filter("items"' in sql
    assert 'x0."score" IS NOT NULL AND NOT (x0."score" > 0)' in sql


def test_compile_list_columns_struct_nested():
    """Deeply nested struct path works: items.details.name -> x0."details"."name"."""
    sql = compile(
        _spec([_rule(CheckType.NOT_NULL, column="items.details.name",
                      list_columns=["items"])]),
        "f.parquet",
    )
    assert 'list_filter("items"' in sql
    assert 'x0."details"."name" IS NULL' in sql


def test_compile_list_columns_struct_in():
    """list_columns with IN check uses struct access."""
    sql = compile(
        _spec([_rule(CheckType.IN, column="items.tag", value=["a", "b"],
                      list_columns=["items"])]),
        "f.parquet",
    )
    assert 'list_filter("items"' in sql
    assert "x0.\"tag\" IN ('a', 'b')" in sql


def test_compile_list_columns_struct_dot_source():
    """list_columns with dot-notation source column."""
    sql = compile(
        _spec([_rule(CheckType.NOT_NULL, column="names.rules.value",
                      list_columns=["names.rules"])]),
        "f.parquet",
    )
    assert 'list_filter("names"."rules"' in sql
    assert 'x0."value" IS NULL' in sql


def test_compile_list_columns_when_folded_into_lambda():
    """when condition referencing a field inside the list gets folded into list_filter."""
    cond = Condition(column="items.parent", check=CheckType.NOT_NULL)
    sql = compile(
        _spec([_rule(CheckType.NOT_NULL, column="items.parent.child",
                      list_columns=["items"],
                      when=cond)]),
        "f.parquet",
    )
    # The when must be inside the lambda, not as an outer WHERE clause
    assert '"items"."parent" IS NOT NULL' not in sql
    assert 'x0."parent" IS NOT NULL AND x0."parent"."child" IS NULL' in sql
    assert 'list_filter("items"' in sql


def test_compile_list_columns_when_on_source_skipped():
    """when condition checking the source column itself is redundant and skipped."""
    cond = Condition(column="items", check=CheckType.NOT_NULL)
    sql = compile(
        _spec([_rule(CheckType.NOT_NULL, column="items.value",
                      list_columns=["items"],
                      when=cond)]),
        "f.parquet",
    )
    # The when is redundant — source_col IS NOT NULL is already in the predicate
    # Should not appear as a separate outer guard — only one occurrence total
    assert sql.count('"items" IS NOT NULL') == 1


def test_compile_list_columns_nested_lists():
    """Nested list_columns produces nested list_filter for ["a", "a.b"]."""
    sql = compile(
        _spec([_rule(CheckType.PATTERN, column="a.b", value="^\\d+$",
                      list_columns=["a", "a.b"])]),
        "f.parquet",
    )
    assert 'list_filter("a"' in sql
    assert "list_filter(x0" in sql
    assert "regexp_matches(x1" in sql


# --- when conditions ---


def test_compile_when_eq():
    cond = Condition(column="country", check=CheckType.EQ, value="US")
    sql = compile(
        _spec([_rule(CheckType.NOT_NULL, when=cond)]), "f.parquet"
    )
    assert "\"country\" = 'US'" in sql
    assert '"col" IS NULL' in sql


def test_compile_when_not_null():
    cond = Condition(column="x", check=CheckType.NOT_NULL)
    sql = compile(
        _spec([_rule(CheckType.GT, value=0, when=cond)]), "f.parquet"
    )
    assert '"x" IS NOT NULL' in sql


def test_compile_when_in():
    cond = Condition(column="type", check=CheckType.IN, value=["a", "b"])
    sql = compile(
        _spec([_rule(CheckType.NOT_NULL, when=cond)]), "f.parquet"
    )
    assert "\"type\" IN ('a', 'b')" in sql


# ---------------------------------------------------------------------------
# validate() — integration tests (require duckdb)
# ---------------------------------------------------------------------------

duckdb = pytest.importorskip("duckdb")


@pytest.fixture()
def conn():
    return duckdb.connect()


@pytest.fixture()
def parquet_path(tmp_path):
    """Return a helper that creates a Parquet file from SQL."""

    def _create(create_sql: str, filename: str = "test.parquet") -> str:
        path = str(tmp_path / filename)
        c = duckdb.connect()
        c.execute(create_sql)
        c.execute(f"COPY _tbl TO '{path}' (FORMAT PARQUET)")
        return path

    return _create


def test_validate_not_null_violations(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 1), ('b', NULL), ('c', 3), ('d', NULL)"
        ") AS t(id, val)"
    )
    spec = _spec([_rule(CheckType.NOT_NULL, column="val")])
    report = validate(spec, path, conn)
    assert len(report.results) == 2
    assert {r.violating_id for r in report.results} == {"b", "d"}


def test_validate_numeric_range(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 5), ('b', 15), ('c', -1), ('d', 10)"
        ") AS t(id, val)"
    )
    spec = _spec(
        [
            _rule(CheckType.GTE, column="val", value=0, name="r.gte"),
            _rule(CheckType.LTE, column="val", value=10, name="r.lte"),
        ]
    )
    report = validate(spec, path, conn)
    gte_violations = [r.violating_id for r in report.results if r.name == "r.gte"]
    assert gte_violations == ["c"]
    lte_violations = [r.violating_id for r in report.results if r.name == "r.lte"]
    assert lte_violations == ["b"]


def test_validate_in_check(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 'red'), ('b', 'blue'), ('c', 'green'), ('d', 'yellow')"
        ") AS t(id, color)"
    )
    spec = _spec(
        [_rule(CheckType.IN, column="color", value=["red", "blue", "green"])]
    )
    report = validate(spec, path, conn)
    assert len(report.results) == 1
    assert report.results[0].violating_id == "d"


def test_validate_not_in_check(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 'admin'), ('b', 'user'), ('c', 'guest')"
        ") AS t(id, role)"
    )
    spec = _spec(
        [_rule(CheckType.NOT_IN, column="role", value=["admin"])]
    )
    report = validate(spec, path, conn)
    assert len(report.results) == 1
    assert report.results[0].violating_id == "a"


def test_validate_unique_list_intra_row(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS "
        "SELECT 'a' AS id, ['x', 'y', 'z'] AS code "
        "UNION ALL "
        "SELECT 'b' AS id, ['x', 'x', 'y'] AS code "
        "UNION ALL "
        "SELECT 'c' AS id, ['p', 'q'] AS code"
    )
    spec = _spec([_rule(CheckType.UNIQUE, column="code")])
    report = validate(spec, path, conn)
    assert len(report.results) == 1
    assert report.results[0].violating_id == "b"


def test_validate_pattern(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 'ABC'), ('b', 'abc'), ('c', '123')"
        ") AS t(id, val)"
    )
    spec = _spec(
        [_rule(CheckType.PATTERN, column="val", value="^[A-Z]+$")]
    )
    report = validate(spec, path, conn)
    assert len(report.results) == 2
    assert {r.violating_id for r in report.results} == {"b", "c"}


def test_validate_when_conditional(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 'US', '12345'), ('b', 'US', NULL), "
        "('c', 'UK', NULL), ('d', 'UK', 'SW1')"
        ") AS t(id, country, zip)"
    )
    cond = Condition(column="country", check=CheckType.EQ, value="US")
    spec = _spec(
        [_rule(CheckType.NOT_NULL, column="zip", when=cond)]
    )
    report = validate(spec, path, conn)
    # Only US rows are checked; b is the violation
    assert len(report.results) == 1
    assert report.results[0].violating_id == "b"


def test_validate_list_columns_list(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS "
        "SELECT 'a' AS id, [1, 2, 3] AS vals "
        "UNION ALL "
        "SELECT 'b' AS id, [1, -1, 3] AS vals "
        "UNION ALL "
        "SELECT 'c' AS id, [5, 6] AS vals"
    )
    spec = _spec(
        [_rule(CheckType.GT, column="vals", value=0, list_columns=["vals"])]
    )
    report = validate(spec, path, conn)
    assert len(report.results) == 1
    assert report.results[0].violating_id == "b"


def test_validate_exactly_one_of(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 'x', NULL), ('b', NULL, 'y'), "
        "('c', 'x', 'y'), ('d', NULL, NULL)"
        ") AS t(id, opt1, opt2)"
    )
    spec = _spec(
        [
            _rule(
                CheckType.EXACTLY_ONE_OF,
                column=None,
                columns=["opt1", "opt2"],
            )
        ]
    )
    report = validate(spec, path, conn)
    # c has both, d has neither — both violate
    assert len(report.results) == 2
    assert {r.violating_id for r in report.results} == {"c", "d"}


def test_validate_any_of(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 'x', NULL), ('b', NULL, NULL), "
        "('c', NULL, 'y')"
        ") AS t(id, opt1, opt2)"
    )
    spec = _spec(
        [
            _rule(
                CheckType.ANY_OF,
                column=None,
                columns=["opt1", "opt2"],
            )
        ]
    )
    report = validate(spec, path, conn)
    assert len(report.results) == 1
    assert report.results[0].violating_id == "b"


def test_validate_column_lt(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 1, 5), ('b', 5, 3), ('c', 2, 2)"
        ") AS t(id, lo, hi)"
    )
    spec = _spec(
        [_rule(CheckType.COLUMN_LT, column="lo", other_column="hi")]
    )
    report = validate(spec, path, conn)
    # b: 5 < 3 fails, c: 2 < 2 fails
    assert len(report.results) == 2
    assert {r.violating_id for r in report.results} == {"b", "c"}


def test_validate_zero_violations(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 1), ('b', 2), ('c', 3)"
        ") AS t(id, val)"
    )
    spec = _spec([_rule(CheckType.NOT_NULL, column="val")])
    report = validate(spec, path, conn)
    assert len(report.results) == 0


def test_validate_custom_id_column(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "(100, NULL), (200, 'ok')"
        ") AS t(fid, val)"
    )
    spec = _spec(
        [_rule(CheckType.NOT_NULL, column="val")],
        id_column="fid",
    )
    report = validate(spec, path, conn)
    assert len(report.results) == 1
    assert report.results[0].violating_id == 100


def test_validate_multiple_rules_combined(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 'hello', 5), ('b', NULL, 15), ('c', 'hi', 3)"
        ") AS t(id, name, score)"
    )
    spec = _spec(
        [
            _rule(CheckType.NOT_NULL, column="name", name="r.nn"),
            _rule(CheckType.LTE, column="score", value=10, name="r.lte"),
            _rule(CheckType.MIN_LENGTH, column="name", value=3, name="r.ml"),
        ]
    )
    report = validate(spec, path, conn)
    nn = [r.violating_id for r in report.results if r.name == "r.nn"]
    lte = [r.violating_id for r in report.results if r.name == "r.lte"]
    ml = [r.violating_id for r in report.results if r.name == "r.ml"]
    assert nn == ["b"]
    assert lte == ["b"]
    assert ml == ["c"]


def test_validate_no_conn(parquet_path):
    """validate() creates its own connection if none provided."""
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 1), ('b', NULL)"
        ") AS t(id, val)"
    )
    spec = _spec([_rule(CheckType.NOT_NULL, column="val")])
    report = validate(spec, path)
    assert len(report.results) == 1


def test_validate_report_metadata(conn, parquet_path):
    from overture.schema.validation.duckdb import validate

    path = parquet_path(
        "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
        "('a', 1), ('b', NULL)"
        ") AS t(id, val)"
    )
    spec = _spec(
        [_rule(CheckType.NOT_NULL, column="val", name="my.rule")],
        name="MyDataset",
    )
    report = validate(spec, path, conn)
    assert report.dataset == "MyDataset"
    assert len(report.results) == 1
    assert report.results[0].name == "my.rule"
    assert report.results[0].severity == Severity.ERROR
