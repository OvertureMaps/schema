"""Tests for the DuckDB validation backend."""

from __future__ import annotations

import textwrap

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
    each_item: bool | None = None,
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
        each_item=each_item,
        when=when,
        severity=severity,
    )


# ---------------------------------------------------------------------------
# TestCompile — unit tests (no duckdb needed)
# ---------------------------------------------------------------------------


class TestCompile:
    """Verify compile() produces correct SQL strings."""

    def test_cte_structure(self):
        sql = compile(_spec([_rule(CheckType.NOT_NULL)]), "/data/test.parquet")
        assert "WITH src AS MATERIALIZED" in sql
        assert "read_parquet('/data/test.parquet')" in sql

    def test_empty_rules(self):
        sql = compile(_spec([]), "/data/test.parquet")
        assert "WHERE FALSE" in sql
        assert "NULL AS id" in sql
        assert "NULL AS rule_name" in sql

    def test_union_all_multiple_rules(self):
        rules = [
            _rule(CheckType.NOT_NULL, name="r1"),
            _rule(CheckType.IS_NULL, name="r2"),
        ]
        sql = compile(_spec(rules), "/data/test.parquet")
        assert sql.count("UNION ALL") == 1

    def test_parquet_path_escaping(self):
        sql = compile(_spec([_rule(CheckType.NOT_NULL)]), "/data/it's a file.parquet")
        assert "it''s a file.parquet" in sql

    def test_dot_notation_column(self):
        sql = compile(
            _spec([_rule(CheckType.NOT_NULL, column="sources.dataset")]),
            "/data/test.parquet",
        )
        assert '"sources"."dataset"' in sql

    # --- Scalar checks ---

    def test_not_null(self):
        sql = compile(_spec([_rule(CheckType.NOT_NULL)]), "f.parquet")
        assert '"col" IS NULL' in sql

    def test_is_null(self):
        sql = compile(_spec([_rule(CheckType.IS_NULL)]), "f.parquet")
        assert '"col" IS NOT NULL' in sql

    def test_gt(self):
        sql = compile(_spec([_rule(CheckType.GT, value=5)]), "f.parquet")
        assert '"col" IS NOT NULL AND NOT ("col" > 5)' in sql

    def test_gte(self):
        sql = compile(_spec([_rule(CheckType.GTE, value=5)]), "f.parquet")
        assert '"col" IS NOT NULL AND NOT ("col" >= 5)' in sql

    def test_lt(self):
        sql = compile(_spec([_rule(CheckType.LT, value=10)]), "f.parquet")
        assert '"col" IS NOT NULL AND NOT ("col" < 10)' in sql

    def test_lte(self):
        sql = compile(_spec([_rule(CheckType.LTE, value=10)]), "f.parquet")
        assert '"col" IS NOT NULL AND NOT ("col" <= 10)' in sql

    def test_eq(self):
        sql = compile(_spec([_rule(CheckType.EQ, value="abc")]), "f.parquet")
        assert '"col" IS NOT NULL AND NOT ("col" = \'abc\')' in sql

    def test_neq(self):
        sql = compile(_spec([_rule(CheckType.NEQ, value="x")]), "f.parquet")
        assert '"col" IS NOT NULL AND "col" = \'x\'' in sql

    def test_between(self):
        sql = compile(_spec([_rule(CheckType.BETWEEN, value=[1, 10])]), "f.parquet")
        assert '"col" IS NOT NULL AND NOT ("col" BETWEEN 1 AND 10)' in sql

    def test_in(self):
        sql = compile(_spec([_rule(CheckType.IN, value=["a", "b"])]), "f.parquet")
        assert "\"col\" IS NOT NULL AND NOT (\"col\" IN ('a', 'b'))" in sql

    def test_not_in(self):
        sql = compile(_spec([_rule(CheckType.NOT_IN, value=["x"])]), "f.parquet")
        assert "\"col\" IS NOT NULL AND NOT (\"col\" NOT IN ('x'))" in sql

    def test_pattern(self):
        sql = compile(_spec([_rule(CheckType.PATTERN, value="^[A-Z]+$")]), "f.parquet")
        assert "regexp_matches" in sql
        assert "^[A-Z]+$" in sql

    def test_min_length(self):
        sql = compile(_spec([_rule(CheckType.MIN_LENGTH, value=3)]), "f.parquet")
        assert "NOT (len(\"col\") >= 3)" in sql

    def test_max_length(self):
        sql = compile(_spec([_rule(CheckType.MAX_LENGTH, value=100)]), "f.parquet")
        assert "NOT (len(\"col\") <= 100)" in sql

    def test_is_type(self):
        sql = compile(_spec([_rule(CheckType.IS_TYPE, value="integer")]), "f.parquet")
        assert "typeof" in sql
        assert "'INTEGER'" in sql
        assert "'BIGINT'" in sql

    def test_column_lt(self):
        sql = compile(
            _spec([_rule(CheckType.COLUMN_LT, column="a", other_column="b")]),
            "f.parquet",
        )
        assert '"a" IS NOT NULL AND "b" IS NOT NULL' in sql
        assert '"a" < "b"' in sql

    def test_column_lte(self):
        sql = compile(
            _spec([_rule(CheckType.COLUMN_LTE, column="a", other_column="b")]),
            "f.parquet",
        )
        assert '"a" <= "b"' in sql

    def test_column_eq(self):
        sql = compile(
            _spec([_rule(CheckType.COLUMN_EQ, column="a", other_column="b")]),
            "f.parquet",
        )
        assert '"a" = "b"' in sql

    def test_geometry_type(self):
        sql = compile(
            _spec([_rule(CheckType.GEOMETRY_TYPE, value=["Point", "MultiPoint"])]),
            "f.parquet",
        )
        assert "ST_GeometryType" in sql
        assert "ST_GeomFromWKB" in sql
        assert "'POINT'" in sql
        assert "'MULTIPOINT'" in sql

    # --- Multi-field checks ---

    def test_any_of(self):
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

    def test_exactly_one_of(self):
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

    def test_unique_scalar(self):
        rules = [_rule(CheckType.UNIQUE, name="u1")]
        sql = compile(_spec(rules), "f.parquet")
        assert "COUNT(*) OVER (PARTITION BY" in sql
        assert "_cnt > 1" in sql

    def test_unique_list(self):
        # Sibling rule with each_item=True triggers list heuristic
        rules = [
            _rule(CheckType.NOT_NULL, each_item=True, name="r1"),
            _rule(CheckType.UNIQUE, name="u1"),
        ]
        sql = compile(_spec(rules), "f.parquet")
        assert "list_distinct" in sql

    # --- each_item ---

    def test_each_item_not_null(self):
        sql = compile(
            _spec([_rule(CheckType.NOT_NULL, each_item=True)]), "f.parquet"
        )
        assert "list_filter" in sql
        assert "x IS NULL" in sql

    def test_each_item_is_null(self):
        sql = compile(
            _spec([_rule(CheckType.IS_NULL, each_item=True)]), "f.parquet"
        )
        assert "list_filter" in sql
        assert "x IS NOT NULL" in sql

    def test_each_item_gt(self):
        sql = compile(
            _spec([_rule(CheckType.GT, value=0, each_item=True)]), "f.parquet"
        )
        assert "list_filter" in sql
        assert "x IS NOT NULL AND NOT (x > 0)" in sql

    def test_each_item_in(self):
        sql = compile(
            _spec([_rule(CheckType.IN, value=["a", "b"], each_item=True)]),
            "f.parquet",
        )
        assert "list_filter" in sql
        assert "x IN ('a', 'b')" in sql

    def test_each_item_pattern(self):
        sql = compile(
            _spec([_rule(CheckType.PATTERN, value="^\\d+$", each_item=True)]),
            "f.parquet",
        )
        assert "list_filter" in sql
        assert "regexp_matches(x" in sql

    # --- when conditions ---

    def test_when_eq(self):
        cond = Condition(column="country", check=CheckType.EQ, value="US")
        sql = compile(
            _spec([_rule(CheckType.NOT_NULL, when=cond)]), "f.parquet"
        )
        assert "\"country\" = 'US'" in sql
        assert '"col" IS NULL' in sql

    def test_when_not_null(self):
        cond = Condition(column="x", check=CheckType.NOT_NULL)
        sql = compile(
            _spec([_rule(CheckType.GT, value=0, when=cond)]), "f.parquet"
        )
        assert '"x" IS NOT NULL' in sql

    def test_when_in(self):
        cond = Condition(column="type", check=CheckType.IN, value=["a", "b"])
        sql = compile(
            _spec([_rule(CheckType.NOT_NULL, when=cond)]), "f.parquet"
        )
        assert "\"type\" IN ('a', 'b')" in sql

    # --- severity ---

    def test_severity_in_output(self):
        sql = compile(
            _spec([_rule(CheckType.NOT_NULL, severity=Severity.WARNING)]),
            "f.parquet",
        )
        assert "'warning' AS severity" in sql

    # --- SQL string escaping ---

    def test_value_with_quotes(self):
        sql = compile(
            _spec([_rule(CheckType.EQ, value="it's")]), "f.parquet"
        )
        assert "it''s" in sql

    # --- custom id_column ---

    def test_custom_id_column(self):
        sql = compile(
            _spec([_rule(CheckType.NOT_NULL)], id_column="feature_id"),
            "f.parquet",
        )
        assert '"feature_id" AS id' in sql


# ---------------------------------------------------------------------------
# TestValidate — integration tests (require duckdb)
# ---------------------------------------------------------------------------


class TestValidate:
    """Integration tests that create Parquet files and run validate()."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_duckdb(self):
        pytest.importorskip("duckdb")

    @pytest.fixture()
    def conn(self):
        import duckdb

        return duckdb.connect()

    @pytest.fixture()
    def parquet_path(self, tmp_path):
        """Return a helper that creates a Parquet file from SQL."""
        import duckdb

        def _create(create_sql: str, filename: str = "test.parquet") -> str:
            path = str(tmp_path / filename)
            c = duckdb.connect()
            c.execute(create_sql)
            c.execute(f"COPY _tbl TO '{path}' (FORMAT PARQUET)")
            return path

        return _create

    def test_not_null_violations(self, conn, parquet_path):
        from overture.schema.validation.duckdb import validate

        path = parquet_path(
            "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
            "('a', 1), ('b', NULL), ('c', 3), ('d', NULL)"
            ") AS t(id, val)"
        )
        spec = _spec([_rule(CheckType.NOT_NULL, column="val")])
        report = validate(spec, path, conn)
        assert report.total_rows == 4
        assert len(report.results) == 1
        result = report.results[0]
        assert result.violation_count == 2
        assert set(result.violating_ids) == {"b", "d"}

    def test_numeric_range(self, conn, parquet_path):
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
        assert report.total_rows == 4
        # gte violation: c (-1)
        gte_result = report.results[0]
        assert gte_result.violation_count == 1
        assert gte_result.violating_ids == ["c"]
        # lte violation: b (15)
        lte_result = report.results[1]
        assert lte_result.violation_count == 1
        assert lte_result.violating_ids == ["b"]

    def test_in_check(self, conn, parquet_path):
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
        assert report.results[0].violation_count == 1
        assert report.results[0].violating_ids == ["d"]

    def test_not_in_check(self, conn, parquet_path):
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
        assert report.results[0].violation_count == 1
        assert report.results[0].violating_ids == ["a"]

    def test_unique_scalar(self, conn, parquet_path):
        from overture.schema.validation.duckdb import validate

        path = parquet_path(
            "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
            "('a', 'x'), ('b', 'y'), ('c', 'x'), ('d', 'z')"
            ") AS t(id, code)"
        )
        spec = _spec([_rule(CheckType.UNIQUE, column="code")])
        report = validate(spec, path, conn)
        result = report.results[0]
        assert result.violation_count == 2
        assert set(result.violating_ids) == {"a", "c"}

    def test_pattern(self, conn, parquet_path):
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
        assert report.results[0].violation_count == 2
        assert set(report.results[0].violating_ids) == {"b", "c"}

    def test_when_conditional(self, conn, parquet_path):
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
        assert report.results[0].violation_count == 1
        assert report.results[0].violating_ids == ["b"]

    def test_each_item_list(self, conn, parquet_path):
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
            [_rule(CheckType.GT, column="vals", value=0, each_item=True)]
        )
        report = validate(spec, path, conn)
        assert report.results[0].violation_count == 1
        assert report.results[0].violating_ids == ["b"]

    def test_exactly_one_of(self, conn, parquet_path):
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
        assert report.results[0].violation_count == 2
        assert set(report.results[0].violating_ids) == {"c", "d"}

    def test_any_of(self, conn, parquet_path):
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
        assert report.results[0].violation_count == 1
        assert report.results[0].violating_ids == ["b"]

    def test_column_lt(self, conn, parquet_path):
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
        assert report.results[0].violation_count == 2
        assert set(report.results[0].violating_ids) == {"b", "c"}

    def test_zero_violations(self, conn, parquet_path):
        from overture.schema.validation.duckdb import validate

        path = parquet_path(
            "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
            "('a', 1), ('b', 2), ('c', 3)"
            ") AS t(id, val)"
        )
        spec = _spec([_rule(CheckType.NOT_NULL, column="val")])
        report = validate(spec, path, conn)
        assert report.results[0].violation_count == 0
        assert report.results[0].violating_ids == []

    def test_custom_id_column(self, conn, parquet_path):
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
        assert report.results[0].violating_ids == [100]

    def test_multiple_rules_combined(self, conn, parquet_path):
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
        assert len(report.results) == 3
        # not_null: b violates
        assert report.results[0].violating_ids == ["b"]
        # lte: b violates (15)
        assert report.results[1].violating_ids == ["b"]
        # min_length: c violates ("hi" has len 2)
        assert report.results[2].violating_ids == ["c"]

    def test_validate_no_conn(self, parquet_path):
        """validate() creates its own connection if none provided."""
        from overture.schema.validation.duckdb import validate

        path = parquet_path(
            "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
            "('a', 1), ('b', NULL)"
            ") AS t(id, val)"
        )
        spec = _spec([_rule(CheckType.NOT_NULL, column="val")])
        report = validate(spec, path)
        assert report.results[0].violation_count == 1

    def test_report_metadata(self, conn, parquet_path):
        from overture.schema.validation.duckdb import validate

        path = parquet_path(
            "CREATE TABLE _tbl AS SELECT * FROM (VALUES "
            "('a', 1), ('b', 2)"
            ") AS t(id, val)"
        )
        spec = _spec(
            [_rule(CheckType.NOT_NULL, column="val", name="my.rule")],
            name="MyDataset",
        )
        report = validate(spec, path, conn)
        assert report.dataset == "MyDataset"
        assert report.total_rows == 2
        assert report.results[0].rule_name == "my.rule"
        assert report.results[0].severity == Severity.ERROR
