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


def _single_violation(
    check: CheckType,
    expr: str,
    value: Any = None,
    other_column: str | None = None,
) -> str:
    """Return the violation expression for a single check against *expr*.

    Reusable for both scalar and nested-list paths.
    """
    if check == CheckType.NOT_NULL:
        return f"{expr} IS NULL"
    if check == CheckType.IS_NULL:
        return f"{expr} IS NOT NULL"
    if check == CheckType.NEQ:
        return f"{expr} IS NOT NULL AND {expr} = {_sql_literal(value)}"
    if check == CheckType.UNIQUE:
        return f"{expr} IS NOT NULL AND len({expr}) != len(list_distinct({expr}))"
    if check in (CheckType.COLUMN_LT, CheckType.COLUMN_LTE, CheckType.COLUMN_EQ):
        other = _quote_col(other_column)  # type: ignore[arg-type]
        positive = _check_expr(check, expr, value, other_column)
        return f"{expr} IS NOT NULL AND {other} IS NOT NULL AND NOT ({positive})"
    # Default: positive check negated
    positive = _check_expr(check, expr, value, other_column)
    return f"{expr} IS NOT NULL AND NOT ({positive})"


def _nested_list_violation(rule: Rule) -> str:
    """Build the violation predicate for a rule with list_columns set.

    Handles arbitrary nesting depth by wrapping with list_filter from
    inside out.
    """
    sources = rule.list_columns  # type: ignore[assignment]
    n = len(sources)
    column = rule.column  # type: ignore[assignment]

    # Determine innermost expression
    if column == sources[-1]:
        # Check targets each element of the innermost list
        field_expr = f"x{n - 1}"
    else:
        # Check targets a struct field accessed from the innermost lambda var
        # e.g. column="items.value", sources=["items"] → x0."value"
        suffix = column[len(sources[-1]) + 1:]
        parts = suffix.split(".")
        field_expr = f"x{n - 1}." + ".".join(f'"{p}"' for p in parts)

    # Build the innermost violation
    inner = _single_violation(rule.check, field_expr, rule.value, rule.other_column)

    # Fold when condition into the innermost lambda if the when column is
    # inside any of the list sources
    when_folded = False
    if rule.when is not None:
        when_col = rule.when.column
        for src in sources:
            if when_col.startswith(src + ".") or when_col == src:
                when_folded = True
                if when_col == src:
                    # Redundant — the source IS NOT NULL guard handles it
                    break
                # Find which lambda depth this when column belongs to
                src_idx = sources.index(src)
                when_suffix = when_col[len(src) + 1:]
                when_parts = when_suffix.split(".")
                when_expr = f"x{src_idx}." + ".".join(f'"{p}"' for p in when_parts)
                if rule.when.check == CheckType.NOT_NULL:
                    when_pred = f"{when_expr} IS NOT NULL"
                elif rule.when.check == CheckType.IS_NULL:
                    when_pred = f"{when_expr} IS NULL"
                else:
                    when_pred = _check_expr(rule.when.check, when_expr, rule.when.value)
                inner = f"{when_pred} AND {inner}"
                break

    # Wrap with list_filter from inside out
    result = inner
    for i in range(n - 1, -1, -1):
        if i == 0:
            source_expr = _quote_col(sources[0])
        else:
            # Access from previous lambda variable into the struct field
            # e.g. sources=["a", "a.b"] → x0."b"
            prev_suffix = sources[i][len(sources[i - 1]) + 1:]
            prev_parts = prev_suffix.split(".")
            source_expr = f"x{i - 1}." + ".".join(f'"{p}"' for p in prev_parts)
        result = (
            f"{source_expr} IS NOT NULL AND "
            f"len(list_filter({source_expr}, x{i} -> {result})) > 0"
        )

    return result, when_folded  # type: ignore[return-value]


def _violation_predicate(rule: Rule, all_rules: list[Rule]) -> tuple[str, bool]:
    """Build the WHERE clause predicate that selects *violating* rows.

    Returns (predicate_sql, when_folded) where when_folded indicates
    whether the when condition was folded into a list_filter lambda.
    """
    check = rule.check
    col = _quote_col(rule.column) if rule.column else None

    # --- Multi-field checks ---
    if check == CheckType.ANY_OF:
        parts = [f"{_quote_col(c)} IS NULL" for c in rule.columns]  # type: ignore[union-attr]
        return " AND ".join(parts), False

    if check == CheckType.EXACTLY_ONE_OF:
        cases = [
            f"CASE WHEN {_quote_col(c)} IS NOT NULL THEN 1 ELSE 0 END"
            for c in rule.columns  # type: ignore[union-attr]
        ]
        return f"({' + '.join(cases)}) != 1", False

    # --- Nested list iteration ---
    if rule.list_columns:
        return _nested_list_violation(rule)

    # --- Unique (scalar fallback) ---
    if check == CheckType.UNIQUE:
        return f"len({col}) != len(list_distinct({col}))", False

    # --- Scalar checks ---
    return _single_violation(check, col, rule.value, rule.other_column), False  # type: ignore[arg-type]


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


def _rule_predicate_expr(rule: Rule, all_rules: list[Rule]) -> str:
    """Return the boolean violation expression for a single rule."""
    predicate, when_folded = _violation_predicate(rule, all_rules)

    if rule.when and not when_folded:
        when_pred = _when_sql(rule.when)
        return f"({when_pred}) AND ({predicate})"

    return predicate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compile(spec: DatasetSpec, parquet_path: str) -> str:
    """Compile a DatasetSpec into a self-contained DuckDB SQL query.

    Returns SQL that finds all rule violations. No duckdb dependency needed.
    """
    path = _escape_sql(parquet_path)

    if not spec.rules:
        cte = (
            f"WITH src AS MATERIALIZED (\n"
            f"    SELECT * FROM read_parquet('{path}')\n"
            f")"
        )
        return (
            f"{cte}\n"
            f"SELECT NULL AS id, NULL AS rule_name, "
            f"NULL AS severity WHERE FALSE"
        )

    cte = (
        f"WITH src AS MATERIALIZED (\n"
        f"    SELECT * FROM read_parquet('{path}')\n"
        f")"
    )

    # Build per-rule boolean columns and metadata VALUES
    id_col = _quote_col(spec.id_column)
    columns: list[str] = []
    meta_values: list[str] = []
    for i, rule in enumerate(spec.rules):
        alias = f"_r{i}"
        expr = _rule_predicate_expr(rule, spec.rules)
        columns.append(f"        , ({expr}) AS {alias}")
        name = _escape_sql(rule.name)
        severity = rule.severity.value
        meta_values.append(f"    ('{alias}', '{name}', '{severity}')")

    col_list = "\n".join(columns)
    aliases = ", ".join(f"_r{i}" for i in range(len(spec.rules)))
    meta = ",\n".join(meta_values)

    return (
        f"{cte}\n"
        f"SELECT u.{id_col} AS id, _meta.rule_name, _meta.severity\n"
        f"FROM (\n"
        f"    SELECT {id_col}, _violated, _idx FROM (\n"
        f"        SELECT {id_col}\n"
        f"{col_list}\n"
        f"        FROM src\n"
        f"    )\n"
        f"    UNPIVOT (_violated FOR _idx IN ({aliases}))\n"
        f"    WHERE _violated\n"
        f") u\n"
        f"JOIN (VALUES\n"
        f"{meta}\n"
        f") AS _meta(_idx, rule_name, severity)\n"
        f"USING (_idx)"
    )


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
