"""DuckDB validation backend.

Compiles validation IR rules into SQL queries and optionally executes
them against Parquet files, returning a ``ValidationReport``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .ir import CheckType, Condition, DatasetSpec, Rule, Severity
from .report import RuleResult, ValidationReport

# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

_GEOM_TYPE_MAP: dict[str, str] = {
    "Point": "POINT",
    "MultiPoint": "MULTIPOINT",
    "LineString": "LINESTRING",
    "MultiLineString": "MULTILINESTRING",
    "Polygon": "POLYGON",
    "MultiPolygon": "MULTIPOLYGON",
    "GeometryCollection": "GEOMETRYCOLLECTION",
}

_TYPE_MAP: dict[str, list[str]] = {
    "boolean": ["BOOLEAN"],
    "integer": [
        "INTEGER",
        "BIGINT",
        "SMALLINT",
        "TINYINT",
        "HUGEINT",
        "UBIGINT",
        "UINTEGER",
        "USMALLINT",
        "UTINYINT",
    ],
    "float": ["FLOAT", "DOUBLE"],
    "string": ["VARCHAR"],
    "date": ["DATE"],
    "datetime": ["TIMESTAMP", "TIMESTAMP WITH TIME ZONE"],
}


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------


def _escape_sql(s: str) -> str:
    """Escape single quotes for SQL string literals."""
    return s.replace("'", "''")


def _sql_literal(value: Any) -> str:
    """Convert a Python value to a SQL literal string."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return f"'{_escape_sql(value)}'"
    if isinstance(value, (list, tuple)):
        return ", ".join(_sql_literal(v) for v in value)
    return f"'{_escape_sql(str(value))}'"


def _quote_col(col: str) -> str:
    """Quote a column name, handling dot-notation with struct access."""
    parts = col.split(".")
    # Quote each part individually and join with dots for struct access
    return ".".join(f'"{p}"' for p in parts)


# ---------------------------------------------------------------------------
# Check expression generation
# ---------------------------------------------------------------------------


def _check_expr(
    check: CheckType,
    expr: str,
    value: Any = None,
    other_column: str | None = None,
) -> str:
    """Return the *positive* (passing) SQL expression for a check.

    Parameters
    ----------
    check
        The check type.
    expr
        The SQL expression to check (column name or lambda variable).
    value
        The check value (if applicable).
    other_column
        The other column for column comparison checks.
    """
    if check == CheckType.GT:
        return f"{expr} > {_sql_literal(value)}"
    if check == CheckType.GTE:
        return f"{expr} >= {_sql_literal(value)}"
    if check == CheckType.LT:
        return f"{expr} < {_sql_literal(value)}"
    if check == CheckType.LTE:
        return f"{expr} <= {_sql_literal(value)}"
    if check == CheckType.EQ:
        return f"{expr} = {_sql_literal(value)}"
    if check == CheckType.NEQ:
        return f"{expr} != {_sql_literal(value)}"
    if check == CheckType.BETWEEN:
        lo, hi = value
        return f"{expr} BETWEEN {_sql_literal(lo)} AND {_sql_literal(hi)}"
    if check == CheckType.IN:
        return f"{expr} IN ({_sql_literal(value)})"
    if check == CheckType.NOT_IN:
        return f"{expr} NOT IN ({_sql_literal(value)})"
    if check == CheckType.PATTERN:
        return f"regexp_matches({expr}, {_sql_literal(value)})"
    if check == CheckType.MIN_LENGTH:
        return f"len({expr}) >= {_sql_literal(value)}"
    if check == CheckType.MAX_LENGTH:
        return f"len({expr}) <= {_sql_literal(value)}"
    if check == CheckType.IS_TYPE:
        types = _TYPE_MAP.get(value, [value])
        type_list = ", ".join(f"'{t}'" for t in types)
        return f"typeof({expr}) IN ({type_list})"
    if check == CheckType.COLUMN_LT:
        other = _quote_col(other_column)  # type: ignore[arg-type]
        return f"{expr} < {other}"
    if check == CheckType.COLUMN_LTE:
        other = _quote_col(other_column)  # type: ignore[arg-type]
        return f"{expr} <= {other}"
    if check == CheckType.COLUMN_EQ:
        other = _quote_col(other_column)  # type: ignore[arg-type]
        return f"{expr} = {other}"
    if check == CheckType.GEOMETRY_TYPE:
        types = value if isinstance(value, list) else [value]
        mapped = [_GEOM_TYPE_MAP.get(t, t) for t in types]
        type_list = ", ".join(f"'{t}'" for t in mapped)
        return f"ST_GeometryType(ST_GeomFromWKB({expr})) IN ({type_list})"

    msg = f"unsupported check type: {check}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Violation predicate generation
# ---------------------------------------------------------------------------


def _is_list_column(rule: Rule, all_rules: list[Rule]) -> bool:
    """Heuristic: if any sibling rule on the same column has each_item=True,
    treat the column as a list column."""
    if rule.column is None:
        return False
    return any(
        r.column == rule.column and r.each_item
        for r in all_rules
        if r is not rule
    )


def _violation_predicate(rule: Rule, all_rules: list[Rule]) -> str:
    """Build the WHERE clause predicate that selects *violating* rows."""
    check = rule.check
    col = _quote_col(rule.column) if rule.column else None

    # --- Multi-field checks ---
    if check == CheckType.ANY_OF:
        parts = [f"{_quote_col(c)} IS NULL" for c in rule.columns]  # type: ignore[union-attr]
        return " AND ".join(parts)

    if check == CheckType.EXACTLY_ONE_OF:
        cases = [
            f"CASE WHEN {_quote_col(c)} IS NOT NULL THEN 1 ELSE 0 END"
            for c in rule.columns  # type: ignore[union-attr]
        ]
        return f"({' + '.join(cases)}) != 1"

    # --- Unique ---
    if check == CheckType.UNIQUE:
        # Handled specially in _rule_select; this shouldn't be called directly
        # for unique, but provide a fallback for list columns
        return f"len({col}) != len(list_distinct({col}))"

    # --- each_item ---
    if rule.each_item:
        x = "x"
        if check == CheckType.NOT_NULL:
            inner_violation = f"{x} IS NULL"
        elif check == CheckType.IS_NULL:
            inner_violation = f"{x} IS NOT NULL"
        else:
            positive = _check_expr(check, x, rule.value, rule.other_column)
            inner_violation = f"{x} IS NOT NULL AND NOT ({positive})"
        return (
            f"{col} IS NOT NULL AND "
            f"len(list_filter({col}, {x} -> {inner_violation})) > 0"
        )

    # --- not_null / is_null ---
    if check == CheckType.NOT_NULL:
        return f"{col} IS NULL"

    if check == CheckType.IS_NULL:
        return f"{col} IS NOT NULL"

    # --- neq special case (simpler negation) ---
    if check == CheckType.NEQ:
        return f"{col} IS NOT NULL AND {col} = {_sql_literal(rule.value)}"

    # --- column comparison checks ---
    if check in (CheckType.COLUMN_LT, CheckType.COLUMN_LTE, CheckType.COLUMN_EQ):
        other = _quote_col(rule.other_column)  # type: ignore[arg-type]
        positive = _check_expr(check, col, rule.value, rule.other_column)  # type: ignore[arg-type]
        return f"{col} IS NOT NULL AND {other} IS NOT NULL AND NOT ({positive})"

    # --- All other scalar checks ---
    positive = _check_expr(check, col, rule.value, rule.other_column)  # type: ignore[arg-type]
    return f"{col} IS NOT NULL AND NOT ({positive})"


# ---------------------------------------------------------------------------
# When condition
# ---------------------------------------------------------------------------


def _when_sql(condition: Condition) -> str:
    """Return the *positive* predicate for a when guard condition."""
    col = _quote_col(condition.column)

    if condition.check == CheckType.NOT_NULL:
        return f"{col} IS NOT NULL"
    if condition.check == CheckType.IS_NULL:
        return f"{col} IS NULL"

    return _check_expr(condition.check, col, condition.value)


# ---------------------------------------------------------------------------
# SELECT generation
# ---------------------------------------------------------------------------


def _rule_select(
    rule: Rule,
    id_column: str,
    all_rules: list[Rule],
) -> str:
    """Generate the complete SELECT statement for one rule."""
    if rule.check == CheckType.UNIQUE:
        return _unique_select(rule, id_column, all_rules)

    id_col = _quote_col(id_column)
    name = _escape_sql(rule.name)
    severity = rule.severity.value

    predicate = _violation_predicate(rule, all_rules)

    when_clause = ""
    if rule.when is not None:
        when_pred = _when_sql(rule.when)
        when_clause = f"({when_pred}) AND "

    return (
        f"SELECT {id_col} AS id, '{name}' AS rule_name, "
        f"'{severity}' AS severity\n"
        f"FROM src\n"
        f"WHERE {when_clause}{predicate}"
    )


def _unique_select(
    rule: Rule,
    id_column: str,
    all_rules: list[Rule],
) -> str:
    """Generate SELECT for unique check — scalar or list variant."""
    col = _quote_col(rule.column)  # type: ignore[arg-type]
    id_col = _quote_col(id_column)
    name = _escape_sql(rule.name)
    severity = rule.severity.value

    # Determine if list column
    is_list = _is_list_column(rule, all_rules)

    when_clause = ""
    when_where = ""
    if rule.when is not None:
        when_pred = _when_sql(rule.when)
        when_clause = f"({when_pred}) AND "
        when_where = f"({when_pred}) AND "

    if is_list:
        # Intra-row uniqueness for list columns
        predicate = f"{col} IS NOT NULL AND len({col}) != len(list_distinct({col}))"
        return (
            f"SELECT {id_col} AS id, '{name}' AS rule_name, "
            f"'{severity}' AS severity\n"
            f"FROM src\n"
            f"WHERE {when_clause}{predicate}"
        )

    # Scalar: cross-row uniqueness using window function
    return (
        f"SELECT id, rule_name, severity FROM (\n"
        f"  SELECT {id_col} AS id, '{name}' AS rule_name, "
        f"'{severity}' AS severity,\n"
        f"    COUNT(*) OVER (PARTITION BY {col}) AS _cnt\n"
        f"  FROM src\n"
        f"  WHERE {when_where}{col} IS NOT NULL\n"
        f") _uq\n"
        f"WHERE _cnt > 1"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compile(spec: DatasetSpec, parquet_path: str) -> str:
    """Compile a DatasetSpec into a self-contained DuckDB SQL query.

    Returns SQL that finds all rule violations. No duckdb dependency needed.
    """
    path = _escape_sql(parquet_path)
    cte = (
        f"WITH src AS MATERIALIZED (\n"
        f"    SELECT * FROM read_parquet('{path}')\n"
        f")"
    )

    if not spec.rules:
        return (
            f"{cte}\n"
            f"SELECT NULL AS id, NULL AS rule_name, "
            f"NULL AS severity WHERE FALSE"
        )

    selects = [
        _rule_select(rule, spec.id_column, spec.rules)
        for rule in spec.rules
    ]

    body = "\nUNION ALL\n".join(selects)
    return f"{cte}\n{body}"


def validate(
    spec: DatasetSpec,
    parquet_path: str,
    conn: Any = None,
) -> ValidationReport:
    """Execute validation rules against a Parquet file.

    Requires the ``duckdb`` package. Creates an in-memory connection if
    none provided. Installs/loads the spatial extension if
    ``geometry_type`` rules are present.
    """
    try:
        import duckdb as _duckdb
    except ImportError as exc:
        msg = (
            "duckdb is required for validate(). "
            "Install it with: pip install overture-schema-validation[duckdb]"
        )
        raise ImportError(msg) from exc

    if conn is None:
        conn = _duckdb.connect()

    # Install/load spatial extension if needed
    has_geom = any(r.check == CheckType.GEOMETRY_TYPE for r in spec.rules)
    if has_geom:
        conn.execute("INSTALL spatial; LOAD spatial;")

    # Execute the compiled query
    sql = compile(spec, parquet_path)
    violations_raw = conn.execute(sql).fetchall()

    # Get total row count
    path = _escape_sql(parquet_path)
    total_rows: int = conn.execute(
        f"SELECT COUNT(*) FROM read_parquet('{path}')"
    ).fetchone()[0]

    # Group violations by rule_name, preserving order and deduplicating IDs
    violations_by_rule: dict[str, list[Any]] = defaultdict(list)
    seen_ids: dict[str, set[Any]] = defaultdict(set)
    for row_id, rule_name, _severity in violations_raw:
        if row_id not in seen_ids[rule_name]:
            seen_ids[rule_name].add(row_id)
            violations_by_rule[rule_name].append(row_id)

    # Build rule name -> Rule lookup for metadata
    rule_lookup: dict[str, Rule] = {r.name: r for r in spec.rules}

    # Build results in rule order
    results: list[RuleResult] = []
    for rule in spec.rules:
        ids = violations_by_rule.get(rule.name, [])
        results.append(
            RuleResult(
                rule_name=rule.name,
                description=rule.description,
                violating_ids=ids,
                violation_count=len(ids),
                severity=rule.severity,
            )
        )

    return ValidationReport(
        dataset=spec.name,
        total_rows=total_rows,
        results=results,
    )
