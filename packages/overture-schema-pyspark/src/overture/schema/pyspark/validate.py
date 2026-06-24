"""Validation pipeline for registered models.

`validate_model()` is the primary entry point: it looks up the
model type in the registry, compares schemas, filters checks, and
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


def model_keys() -> list[str]:
    """Canonical entry-point keys registered in the validation registry."""
    return sorted(REGISTRY)


def model_names() -> list[str]:
    """All names `validate_model` accepts.

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

# Working/output columns `explain_errors` introduces beyond `_err_<int>`:
# `_idx`/`_errors` are UNPIVOT scratch, `field`/`check`/`message` are its
# output contract. An input column sharing any of these names produces
# duplicate attributes -> AMBIGUOUS_REFERENCE.
_EXPLAIN_RESERVED = ("_idx", "_errors", "field", "check", "message")


def _non_error_columns(evaluated: DataFrame) -> list[str]:
    """Column names excluding `_err_N` error columns appended by `evaluate_checks`."""
    return [c for c in evaluated.columns if not _ERR_COLUMN.match(c)]


def _reject_reserved_collisions(collisions: Iterable[str], reserved_label: str) -> None:
    """Raise if any input column collides with a reserved working/output name.

    Parameters
    ----------
    collisions
        Input column names that collide with the reserved set.
    reserved_label
        Human-readable description of the reserved names, completing the
        sentence `... collide with {reserved_label}`.

    Raises
    ------
    ValueError
        If `collisions` is non-empty.  The message names the offending
        columns and the remediation (rename or drop them).
    """
    names = sorted(collisions)
    if names:
        raise ValueError(
            f"input columns {names} collide with {reserved_label}; "
            f"rename or drop them before validating"
        )


def evaluate_checks(df: DataFrame, checks: list[Check]) -> DataFrame:
    """Append `_err_N` columns for each check.

    Returns the input DataFrame with one `array<string>` column per check,
    containing error messages (non-empty) or null/empty (no error).

    Raises
    ------
    ValueError
        If `df` already contains a `_err_<int>` column.  Appending the
        working columns would shadow it (duplicate attributes), so the
        collision is rejected -- most realistically a persisted
        `result.evaluated` fed back through validation.
    """
    _reject_reserved_collisions(
        (c for c in df.columns if _ERR_COLUMN.match(c)),
        "the reserved '_err_<int>' columns evaluate_checks appends",
    )
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

    Raises
    ------
    ValueError
        If an original column collides with a working/output name
        (`_idx`, `_errors`, `field`, `check`, `message`).
    """
    orig_cols = _non_error_columns(evaluated)
    _reject_reserved_collisions(
        (c for c in orig_cols if c in _EXPLAIN_RESERVED),
        f"explain_errors' working/output columns {list(_EXPLAIN_RESERVED)}",
    )
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
    """Result of validate_model().

    Consumer owns caching of `evaluated`. Call `error_rows()` for
    the filtered view; use `explain_errors(result.evaluated,
    result.checks)` for the opt-in UNPIVOT.
    """

    evaluated: DataFrame
    checks: list[Check]
    schema_mismatches: list[SchemaMismatch]
    suppressed_checks: list[Check]
    absent_columns: tuple[str, ...] = ()
    """Root columns present in the schema but absent from the data and not already skipped.

    Ordered by first appearance in `schema_mismatches`, deduplicated.
    Matches the set of root fields whose checks `validate_model` silently
    drops; callers use this to suggest `--skip-columns` without re-deriving
    it from `schema_mismatches`.
    """

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


def validate_model(
    df: DataFrame,
    model_type: str,
    *,
    skip_columns: Iterable[str] = (),
    ignore_extra_columns: Iterable[str] = (),
    suppress: Iterable[str | tuple[str, str] | Check] = (),
) -> ValidationResult:
    """Validate a DataFrame against a registered model type.

    Parameters
    ----------
    df
        Input DataFrame to validate.
    model_type
        Registered model type name (e.g. `"building"`).
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
        If `model_type` isn't registered.  Message includes the
        sorted list of known types.
    """
    model_type = resolve_entry_point_key(model_type, REGISTRY)
    validation = REGISTRY[model_type]
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
        if m.root in skip:
            continue
        if m.expected == "missing" and m.root in ignore_extra:
            continue
        mismatches.append(m)

    # Validate suppress entries match real checks before filtering.  A bare
    # suppress string names a column; it is valid when some check reads it,
    # which is exactly when suppressing it would drop a check -- the same
    # `read_columns` set that drives exclusion below.
    all_checks = validation.checks()
    valid_roots = {col for c in all_checks for col in c.read_columns}
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
            f"suppress entries don't match any check for {model_type!r}: "
            + "; ".join(parts)
        )

    # Schema columns the data lacks.  A check referencing an absent column
    # raises an AnalysisException during Spark plan analysis, so such checks
    # are dropped before evaluation via the `excluded` filter below -- the
    # same filter skip_columns feeds.  Only that check-filtering is shared:
    # a skip_columns mismatch was suppressed by the loop above, so the
    # caller sees no mismatch and validation continues; an absent-column
    # mismatch stays in `mismatches` and is reported, so the caller (the
    # CLI) aborts unless --skip-schema-check.  `--skip-columns` opts into
    # that suppression -- it is not a restatement of the default.
    # Exclusion is column-granular, so filtering is all-or-nothing: if the
    # data has the `bbox` struct but is missing only `bbox.xmin`, every check
    # rooted at `bbox` is dropped, including checks on sub-fields that are
    # present.  Finer granularity would require sub-column awareness in Check,
    # which it deliberately lacks.  `m.root` strips the array/map step markers
    # (`sources[].confidence` -> `sources`) so a nested absence still resolves
    # to the top-level column.
    absent_columns = tuple(
        dict.fromkeys(m.root for m in mismatches if m.actual == "missing")
    )

    # Check filtering.  A check is dropped when any column it reads is gone --
    # whether skipped or structurally absent -- so an unresolvable `F.col()`
    # never reaches Spark.  Suppression by column name is the same predicate
    # over a different set: suppressing a column is treating it as absent.
    excluded = skip | set(absent_columns)

    def _is_excluded(chk: Check) -> bool:
        return not excluded.isdisjoint(chk.read_columns)

    kept: list[Check] = []
    suppressed: list[Check] = []
    for chk in all_checks:
        if _is_excluded(chk):
            continue  # structurally absent, not tracked in suppressed
        if not suppress_roots.isdisjoint(chk.read_columns):
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
        absent_columns=absent_columns,
    )
