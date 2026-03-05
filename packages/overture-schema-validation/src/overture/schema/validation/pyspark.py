"""PySpark validation backend.

Compiles validation IR rules into PySpark Column expressions and executes
them against DataFrames, returning a ``ValidationReport``.
"""

from __future__ import annotations

from typing import Any

from .ir import CheckType, Condition, DatasetSpec, Rule, Severity
from .report import RuleResult, ValidationReport

# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

_GEOM_TYPE_MAP: dict[str, str] = {
    "Point": "ST_Point",
    "MultiPoint": "ST_MultiPoint",
    "LineString": "ST_LineString",
    "MultiLineString": "ST_MultiLineString",
    "Polygon": "ST_Polygon",
    "MultiPolygon": "ST_MultiPolygon",
    "GeometryCollection": "ST_GeometryCollection",
}

# ---------------------------------------------------------------------------
# Spark type mapping for IS_TYPE
# ---------------------------------------------------------------------------


def _spark_type_matches(data_type: Any, expected: str) -> bool:
    """Check if a PySpark DataType matches the expected IR type name."""
    from pyspark.sql.types import (
        BooleanType,
        ByteType,
        DateType,
        DecimalType,
        DoubleType,
        FloatType,
        IntegerType,
        LongType,
        ShortType,
        StringType,
        TimestampType,
    )

    type_map: dict[str, tuple] = {
        "boolean": (BooleanType,),
        "integer": (IntegerType, LongType, ShortType, ByteType),
        "float": (FloatType, DoubleType, DecimalType),
        "string": (StringType,),
        "date": (DateType,),
        "datetime": (TimestampType,),
    }

    allowed = type_map.get(expected)
    if allowed is None:
        return False
    return isinstance(data_type, allowed)


# ---------------------------------------------------------------------------
# Column expression helpers
# ---------------------------------------------------------------------------


def _resolve_col(col_name: str):
    """Resolve a dotted column name to a PySpark Column."""
    from pyspark.sql import functions as F

    parts = col_name.split(".")
    result = F.col(parts[0])
    for part in parts[1:]:
        result = result[part]
    return result


def _check_violation(
    check: CheckType,
    col,
    value: Any = None,
    other_column: str | None = None,
    df=None,
):
    """Return a PySpark Column expression that is True when the row violates.

    Parameters
    ----------
    check
        The check type.
    col
        PySpark Column expression for the checked field.
    value
        The check value (if applicable).
    other_column
        The other column for column comparison checks.
    df
        The DataFrame (needed for IS_TYPE to inspect schema).
    """
    from pyspark.sql import functions as F

    if check == CheckType.NOT_NULL:
        return col.isNull()

    if check == CheckType.IS_NULL:
        return col.isNotNull()

    if check == CheckType.GT:
        return col.isNotNull() & ~(col > value)

    if check == CheckType.GTE:
        return col.isNotNull() & ~(col >= value)

    if check == CheckType.LT:
        return col.isNotNull() & ~(col < value)

    if check == CheckType.LTE:
        return col.isNotNull() & ~(col <= value)

    if check == CheckType.EQ:
        return col.isNotNull() & ~(col == value)

    if check == CheckType.NEQ:
        return col.isNotNull() & (col == value)

    if check == CheckType.BETWEEN:
        lo, hi = value
        return col.isNotNull() & ~col.between(lo, hi)

    if check == CheckType.IN:
        return col.isNotNull() & ~col.isin(value)

    if check == CheckType.NOT_IN:
        return col.isNotNull() & col.isin(value)

    if check == CheckType.PATTERN:
        return col.isNotNull() & ~col.rlike(value)

    if check == CheckType.MIN_LENGTH:
        return col.isNotNull() & ~(F.length(col) >= value)

    if check == CheckType.MAX_LENGTH:
        return col.isNotNull() & ~(F.length(col) <= value)

    if check == CheckType.MIN_LIST_LENGTH:
        return col.isNotNull() & ~(F.size(col) >= value)

    if check == CheckType.MAX_LIST_LENGTH:
        return col.isNotNull() & ~(F.size(col) <= value)

    if check == CheckType.UNIQUE:
        return col.isNotNull() & (F.size(col) != F.size(F.array_distinct(col)))

    if check == CheckType.COLUMN_LT:
        other = _resolve_col(other_column)  # type: ignore[arg-type]
        return col.isNotNull() & other.isNotNull() & ~(col < other)

    if check == CheckType.COLUMN_LTE:
        other = _resolve_col(other_column)  # type: ignore[arg-type]
        return col.isNotNull() & other.isNotNull() & ~(col <= other)

    if check == CheckType.COLUMN_EQ:
        other = _resolve_col(other_column)  # type: ignore[arg-type]
        return col.isNotNull() & other.isNotNull() & ~(col == other)

    if check == CheckType.GEOMETRY_TYPE:
        types = value if isinstance(value, list) else [value]
        mapped = [_GEOM_TYPE_MAP.get(t, t) for t in types]
        geom_type_expr = F.expr(f"ST_GeometryType(ST_GeomFromWKB({col._jc.toString()}))")
        return col.isNotNull() & ~geom_type_expr.isin(mapped)

    msg = f"unsupported check type: {check}"
    raise ValueError(msg)


def _is_type_violation(rule: Rule, df):
    """Handle IS_TYPE check (schema-level)."""
    from pyspark.sql import functions as F

    col_name = rule.column  # type: ignore[assignment]
    field = _find_field(df.schema, col_name)

    if field is None or not _spark_type_matches(field.dataType, rule.value):
        # Type mismatch: all non-null rows violate
        return _resolve_col(col_name).isNotNull()
    # Type matches: no violations
    return F.lit(False)


def _find_field(schema, col_name: str):
    """Find a StructField in a schema by dotted column name."""
    parts = col_name.split(".")
    current = schema
    for part in parts:
        found = None
        for field in current.fields:
            if field.name == part:
                found = field
                break
        if found is None:
            return None
        current = found.dataType if hasattr(found.dataType, "fields") else found.dataType
        if part == parts[-1]:
            return found
    return None


# ---------------------------------------------------------------------------
# When condition
# ---------------------------------------------------------------------------


def _when_expr(condition: Condition):
    """Return a PySpark Column for a when guard condition."""
    from pyspark.sql import functions as F

    col = _resolve_col(condition.column)

    if condition.check == CheckType.NOT_NULL:
        return col.isNotNull()
    if condition.check == CheckType.IS_NULL:
        return col.isNull()
    if condition.check == CheckType.EQ:
        return col == condition.value
    if condition.check == CheckType.NEQ:
        return col != condition.value
    if condition.check == CheckType.GT:
        return col > condition.value
    if condition.check == CheckType.GTE:
        return col >= condition.value
    if condition.check == CheckType.LT:
        return col < condition.value
    if condition.check == CheckType.LTE:
        return col <= condition.value
    if condition.check == CheckType.BETWEEN:
        lo, hi = condition.value
        return col.between(lo, hi)
    if condition.check == CheckType.IN:
        return col.isin(condition.value)
    if condition.check == CheckType.NOT_IN:
        return ~col.isin(condition.value)
    if condition.check == CheckType.PATTERN:
        return col.rlike(condition.value)
    if condition.check == CheckType.IS_TYPE:
        # Not typically used in when conditions for PySpark
        return F.lit(True)

    msg = f"unsupported when check: {condition.check}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Rule → violation Column
# ---------------------------------------------------------------------------


def _rule_violation_col(rule: Rule, df) -> "Column":
    """Build the boolean violation Column for a single rule."""
    from pyspark.sql import functions as F

    check = rule.check

    # --- Multi-field checks ---
    if check == CheckType.ANY_OF:
        cols = [_resolve_col(c) for c in rule.columns]  # type: ignore[union-attr]
        # All columns are null → violation
        result = cols[0].isNull()
        for c in cols[1:]:
            result = result & c.isNull()
        return result

    if check == CheckType.EXACTLY_ONE_OF:
        cols = [_resolve_col(c) for c in rule.columns]  # type: ignore[union-attr]
        count_expr = sum(
            F.when(c.isNotNull(), F.lit(1)).otherwise(F.lit(0)) for c in cols
        )
        return count_expr != 1

    # --- IS_TYPE (schema-level) ---
    if check == CheckType.IS_TYPE:
        violation = _is_type_violation(rule, df)
        if rule.when:
            return _when_expr(rule.when) & violation
        return violation

    # --- Nested list iteration ---
    if rule.list_columns:
        return _nested_list_violation(rule, df)

    # --- Scalar checks ---
    col = _resolve_col(rule.column)  # type: ignore[arg-type]
    violation = _check_violation(check, col, rule.value, rule.other_column, df)

    if rule.when:
        return _when_expr(rule.when) & violation

    return violation


def _nested_list_violation(rule: Rule, df):
    """Build the violation predicate for a rule with list_columns set."""
    from pyspark.sql import functions as F

    sources = rule.list_columns  # type: ignore[assignment]
    n = len(sources)
    column = rule.column  # type: ignore[assignment]

    def _build_inner_check(elem_col):
        """Build the innermost violation check on an element."""
        if column == sources[-1]:
            field_expr = elem_col
        else:
            suffix = column[len(sources[-1]) + 1:]
            parts = suffix.split(".")
            field_expr = elem_col
            for part in parts:
                field_expr = field_expr[part]

        inner = _check_violation(rule.check, field_expr, rule.value, rule.other_column, df)

        # Fold when condition into the lambda if it's inside a list source
        if rule.when is not None:
            when_col_name = rule.when.column
            for src in sources:
                if when_col_name.startswith(src + ".") or when_col_name == src:
                    if when_col_name != src:
                        src_idx = sources.index(src)
                        when_suffix = when_col_name[len(src) + 1:]
                        # This is a simplification: we assume the when is
                        # in the same list as the check
                        when_field = elem_col
                        for part in when_suffix.split("."):
                            when_field = when_field[part]
                        when_pred = _when_expr_from_col(rule.when, when_field)
                        inner = when_pred & inner
                    break
        return inner

    # Build from inside out with F.exists
    def _wrap_exists(depth, source_col):
        if depth == n - 1:
            return F.exists(source_col, lambda x: _build_inner_check(x))
        else:
            next_src = sources[depth + 1]
            suffix = next_src[len(sources[depth]) + 1:]
            parts = suffix.split(".")
            return F.exists(source_col, lambda x: (
                _access_field(x, parts).isNotNull() &
                _wrap_exists(depth + 1, _access_field(x, parts))
            ))

    root_col = _resolve_col(sources[0])
    result = root_col.isNotNull() & _wrap_exists(0, root_col)

    # Apply when condition if not folded
    if rule.when is not None:
        when_col_name = rule.when.column
        folded = any(
            when_col_name.startswith(src + ".") or when_col_name == src
            for src in sources
        )
        if not folded:
            result = _when_expr(rule.when) & result

    return result


def _access_field(col, parts):
    """Access nested struct fields from a column."""
    result = col
    for part in parts:
        result = result[part]
    return result


def _when_expr_from_col(condition: Condition, col):
    """Build a when expression using an existing Column instead of resolving by name."""
    from pyspark.sql import functions as F

    if condition.check == CheckType.NOT_NULL:
        return col.isNotNull()
    if condition.check == CheckType.IS_NULL:
        return col.isNull()
    if condition.check == CheckType.EQ:
        return col == condition.value
    if condition.check == CheckType.NEQ:
        return col != condition.value
    if condition.check == CheckType.GT:
        return col > condition.value
    if condition.check == CheckType.GTE:
        return col >= condition.value
    if condition.check == CheckType.LT:
        return col < condition.value
    if condition.check == CheckType.LTE:
        return col <= condition.value
    if condition.check == CheckType.BETWEEN:
        lo, hi = condition.value
        return col.between(lo, hi)
    if condition.check == CheckType.IN:
        return col.isin(condition.value)
    if condition.check == CheckType.NOT_IN:
        return ~col.isin(condition.value)
    if condition.check == CheckType.PATTERN:
        return col.rlike(condition.value)

    return F.lit(True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_df(spec: DatasetSpec, df, spark=None):
    """Validate a Spark DataFrame against a DatasetSpec.

    Returns a violations DataFrame with columns: (id, name, severity).

    The session should have been created via :func:`create_spark_session`
    so that Sedona UDFs are available for ``GEOMETRY_TYPE`` checks.
    """
    from pyspark.sql import functions as F

    if not spec.rules:
        return df.sparkSession.createDataFrame([], "id STRING, name STRING, severity STRING")

    id_col = spec.id_column

    # Build per-rule boolean violation columns
    rule_aliases = []
    select_cols = [F.col(id_col)]
    for i, rule in enumerate(spec.rules):
        alias = f"_r{i}"
        violation_expr = _rule_violation_col(rule, df)
        select_cols.append(violation_expr.alias(alias))
        rule_aliases.append(alias)

    flagged = df.select(*select_cols)

    # Unpivot: use stack() to turn boolean columns into rows
    n = len(rule_aliases)
    stack_args = ", ".join(
        f"{i}, {alias}" for i, alias in enumerate(rule_aliases)
    )
    stack_expr = f"stack({n}, {stack_args}) as (_idx, _violated)"

    unpivoted = flagged.select(
        F.col(id_col),
        F.expr(stack_expr),
    ).filter(F.col("_violated") == True)  # noqa: E712

    # Map index to rule name and severity
    meta_rows = [
        (i, rule.name, rule.severity.value)
        for i, rule in enumerate(spec.rules)
    ]
    session = spark or df.sparkSession
    meta_df = session.createDataFrame(meta_rows, ["_idx", "name", "severity"])

    result = unpivoted.join(meta_df, "_idx").select(
        F.col(id_col).alias("id"),
        F.col("name"),
        F.col("severity"),
    )

    return result


def validate(spec: DatasetSpec, df, spark=None) -> ValidationReport:
    """Validate a Spark DataFrame against a DatasetSpec.

    Returns a ``ValidationReport`` with one ``RuleResult`` per violation.
    """
    violations_df = validate_df(spec, df, spark)
    rows = violations_df.collect()

    results = [
        RuleResult(
            name=row["name"],
            violating_id=row["id"],
            severity=Severity(row["severity"]),
        )
        for row in rows
    ]

    return ValidationReport(
        dataset=spec.name,
        results=results,
    )


def create_spark_session(app_name: str = "overture-validation", **config):
    """Create a SparkSession with Sedona pre-configured.

    Uses ``SedonaContext.builder()`` to ensure Sedona JARs are on the
    classpath and Sedona UDFs are registered.  Any extra keyword arguments
    are forwarded as Spark config options.

    Parameters
    ----------
    app_name
        Spark application name.
    **config
        Additional Spark configuration key-value pairs
        (e.g. ``master="local[1]"``).
    """
    try:
        from sedona.spark import SedonaContext
    except ImportError as exc:
        msg = (
            "apache-sedona is required for the PySpark backend. "
            "Install it with: pip install overture-schema-validation[pyspark]"
        )
        raise ImportError(msg) from exc

    from importlib.metadata import version

    sedona_version = version("apache-sedona")
    from pyspark import __version__ as spark_version

    spark_major_minor = ".".join(spark_version.split(".")[:2])

    packages = (
        f"org.apache.sedona:sedona-spark-shaded-{spark_major_minor}_2.12:{sedona_version},"
        f"org.datasyslab:geotools-wrapper:{sedona_version}-33.1"
    )

    builder = (
        SedonaContext.builder()
        .appName(app_name)
        .config("spark.jars.packages", packages)
    )
    for key, value in config.items():
        builder = builder.config(key, value)

    spark = builder.getOrCreate()
    return SedonaContext.create(spark)
