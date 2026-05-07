"""Validation pipeline for Overture feature data.

`validate_feature()` is the primary entry point: it looks up the
feature type in the registry, compares schemas, filters checks, and
evaluates them in a single pass.  Returns a `ValidationResult`
carrying the evaluated DataFrame and metadata.

Lower-level helpers (`evaluate_checks`, `filter_errors`,
`explain_errors`) are available for consumers needing finer control.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from overture.schema.system.discovery import (
    entry_point_class_alias,
    resolve_entry_point_key,
)

from ._registry import REGISTRY
from .check import Check, CheckShape
from .expressions.column_patterns import coalesce_errors
from .schema_check import SchemaMismatch, compare_schemas


def feature_keys() -> list[str]:
    """Canonical entry-point keys registered in the validation registry."""
    return sorted(REGISTRY)


def feature_names() -> list[str]:
    """All names `validate_feature` accepts.

    Includes canonical entry-point keys and the snake-case class-name
    aliases the resolver recognizes (only when an alias is unambiguous).
    """
    aliases = {
        name
        for name, count in Counter(entry_point_class_alias(k) for k in REGISTRY).items()
        if count == 1
    }
    return sorted(set(REGISTRY) | aliases)


def _normalize_suppress(
    suppress: Iterable[str | tuple[str, str] | Check],
) -> tuple[set[str], set[tuple[str, str]]]:
    """Partition suppress entries into root field names and (field, name) pairs.

    Parameters
    ----------
    suppress
        Mix of bare field name strings, `(field, name)` tuples, and
        `Check` objects.

    Returns
    -------
    tuple[set[str], set[tuple[str, str]]]
        `(root_fields, pairs)` where `root_fields` is bare field names
        and `pairs` is `(field, name)` pairs extracted from tuples and
        Check objects.
    """
    root_fields: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for entry in suppress:
        if isinstance(entry, str):
            root_fields.add(entry)
        elif isinstance(entry, Check):
            pairs.add((entry.field, entry.name))
        else:
            pairs.add(entry)
    return root_fields, pairs


# Matches the `_err_<int>` columns `evaluate_checks` appends; ordinary
# user columns starting with `_err_` (but not followed by digits only)
# are preserved.
_ERR_COLUMN = re.compile(r"^_err_\d+$")


def _non_error_columns(evaluated: DataFrame) -> list[str]:
    """Column names excluding `_err_N` error columns appended by `evaluate_checks`."""
    return [c for c in evaluated.columns if not _ERR_COLUMN.match(c)]


def evaluate_checks(df: DataFrame, checks: list[Check]) -> DataFrame:
    """Append `_err_N` columns for each check.

    Returns the input DataFrame with one `array<string>` column per check,
    containing error messages (non-empty) or null/empty (no error).
    """
    error_cols = []
    for i, chk in enumerate(checks):
        if chk.shape == CheckShape.SCALAR:
            col = F.array_compact(F.array(chk.expr))
        else:
            col = coalesce_errors(F.filter(chk.expr, lambda x: x.isNotNull()))
        error_cols.append(col.cast("array<string>").alias(f"_err_{i}"))
    return df.select("*", *error_cols)


def _max_error_size(n: int) -> F.Column:
    """Build a Column for the largest `_err_N` array size across all checks.

    Use `greatest()` instead of chaining OR across all checks.  A 255-check
    OR tree triggers Spark's CommutativeExpression.orderCommutative during
    plan canonicalization, which is O(n²+) and OOMs the driver. `greatest()`
    is not a CommutativeExpression, so the optimizer skips that path.

    Caller must guarantee `n >= 1`.
    """
    err_sizes = [F.coalesce(F.size(F.col(f"_err_{i}")), F.lit(0)) for i in range(n)]
    return err_sizes[0] if n == 1 else F.greatest(*err_sizes)


def filter_errors(evaluated: DataFrame, checks: list[Check]) -> DataFrame:
    """Filter an evaluated DataFrame to rows with at least one error.

    Parameters
    ----------
    evaluated
        DataFrame produced by `evaluate_checks()`.
    checks
        Same check list passed to `evaluate_checks()`.

    Returns
    -------
    DataFrame
        Original columns only (`_err_N` columns stripped).
    """
    return evaluated.filter(_max_error_size(len(checks)) > 0).select(
        *_non_error_columns(evaluated)
    )


def explain_errors(evaluated: DataFrame, checks: list[Check]) -> DataFrame:
    """Unpivot evaluated error columns into one row per violation.

    Parameters
    ----------
    evaluated
        DataFrame produced by `evaluate_checks()`.
    checks
        Same check list passed to `evaluate_checks()`.

    Returns
    -------
    DataFrame
        Schema: `<original columns>, field, check, message`.
    """
    orig_cols = _non_error_columns(evaluated)
    n = len(checks)
    if n == 0:
        empty_schema = StructType(
            [
                *evaluated.select(*orig_cols).schema.fields,
                StructField("field", StringType(), True),
                StructField("check", StringType(), True),
                StructField("message", StringType(), True),
            ]
        )
        return evaluated.sparkSession.createDataFrame([], empty_schema)
    stack_args = ", ".join(f"{i}, `_err_{i}`" for i in range(n))
    unpivoted = evaluated.select(
        *orig_cols,
        F.expr(f"stack({n}, {stack_args}) as (_idx, _errors)"),
    ).filter(F.col("_errors").isNotNull() & (F.size("_errors") > 0))

    exploded = unpivoted.select(
        *orig_cols,
        "_idx",
        F.explode("_errors").alias("message"),
    )

    meta_df = evaluated.sparkSession.createDataFrame(
        [(i, c.field, c.name) for i, c in enumerate(checks)],
        ["_idx", "field", "check"],
    )

    return exploded.join(F.broadcast(meta_df), "_idx").select(
        *orig_cols, "field", "check", "message"
    )


@dataclass(frozen=True)
class ValidationResult:
    """Result of validate_feature().

    Consumer owns caching of `evaluated`. Call `error_rows()` for
    the filtered view; use `explain_errors(result.evaluated,
    result.checks)` for the opt-in UNPIVOT.
    """

    evaluated: DataFrame
    checks: list[Check]
    schema_mismatches: list[SchemaMismatch]
    suppressed_checks: list[Check]

    def error_rows(self) -> DataFrame:
        """Rows with at least one violation. Original columns only."""
        if not self.checks:
            return self.evaluated.limit(0)
        return filter_errors(self.evaluated, self.checks)

    def row_counts(self) -> tuple[int, int]:
        """Count total and error rows in a single pass.

        Computes both counts with one aggregation over the evaluated
        DataFrame, avoiding the need to cache before counting.

        Returns
        -------
        tuple[int, int]
            `(total_rows, error_rows)`.
        """
        if not self.checks:
            return self.evaluated.count(), 0
        max_err = _max_error_size(len(self.checks))
        row = self.evaluated.agg(
            F.count(F.lit(1)).alias("total"),
            F.coalesce(F.sum(F.when(max_err > 0, 1).otherwise(0)), F.lit(0)).alias(
                "errors"
            ),
        ).first()
        assert row is not None  # aggregation on a DataFrame always produces a row
        return row["total"], row["errors"]


def validate_feature(
    df: DataFrame,
    feature_type: str,
    *,
    skip_columns: Iterable[str] = (),
    ignore_extra_columns: Iterable[str] = (),
    suppress: Iterable[str | tuple[str, str] | Check] = (),
) -> ValidationResult:
    """Validate a DataFrame against a registered feature type.

    Parameters
    ----------
    df
        Input DataFrame to validate.
    feature_type
        Registered feature type name (e.g. `"building"`).
    skip_columns
        Columns declared absent from the data.  Raises `ValueError`
        if any are present in `df.columns`.
    ignore_extra_columns
        Columns that may be present in the data but absent from the
        expected schema.
    suppress
        Checks to remove before evaluation.  Bare strings suppress by
        root field; tuples by exact `(field, name)`; Check objects
        by extracting `(field, name)`.  Raises `ValueError` if any
        entry doesn't match a registered check.

    Raises
    ------
    ValueError
        If `feature_type` isn't registered.  Message includes the
        sorted list of known types.
    """
    feature_type = resolve_entry_point_key(feature_type, REGISTRY)
    validation = REGISTRY[feature_type]
    skip = frozenset(skip_columns)
    ignore_extra = frozenset(ignore_extra_columns)
    suppress_roots, suppress_pairs = _normalize_suppress(suppress)

    # Validate skip_columns are actually absent
    present = skip & set(df.columns)
    if present:
        raise ValueError(
            f"skip_columns {sorted(present)} are present in the "
            f"DataFrame; remove them from skip_columns or drop them "
            f"from the data"
        )

    # Schema comparison with filtering
    raw_mismatches = compare_schemas(df.schema, validation.schema)
    mismatches = []
    for m in raw_mismatches:
        root = m.path.split(".", 1)[0]
        if root in skip:
            continue
        if m.expected == "missing" and root in ignore_extra:
            continue
        mismatches.append(m)

    # Validate suppress entries match real checks before filtering
    all_checks = validation.checks()
    valid_roots = {c.root_field for c in all_checks if c.root_field is not None}
    valid_pairs = {(c.field, c.name) for c in all_checks}
    unmatched_roots = suppress_roots - valid_roots
    unmatched_pairs = suppress_pairs - valid_pairs
    if unmatched_roots or unmatched_pairs:
        parts = []
        if unmatched_roots:
            parts.append(f"unknown root fields {sorted(unmatched_roots)}")
        if unmatched_pairs:
            parts.append(f"unknown (field, name) pairs {sorted(unmatched_pairs)}")
        raise ValueError(
            f"suppress entries don't match any check for {feature_type!r}: "
            + "; ".join(parts)
        )

    # Check filtering
    kept: list[Check] = []
    suppressed: list[Check] = []
    for chk in all_checks:
        if chk.root_field is not None and chk.root_field in skip:
            continue  # structurally absent, not tracked in suppressed
        if chk.root_field is not None and chk.root_field in suppress_roots:
            suppressed.append(chk)
            continue
        if (chk.field, chk.name) in suppress_pairs:
            suppressed.append(chk)
            continue
        kept.append(chk)

    evaluated = evaluate_checks(df, kept)
    return ValidationResult(
        evaluated=evaluated,
        checks=kept,
        schema_mismatches=mismatches,
        suppressed_checks=suppressed,
    )
