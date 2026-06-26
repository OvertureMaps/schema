"""Structural PySpark column patterns for validation expression composition.

These functions provide reusable wrappers for array iteration, null
guarding, and error message construction.  Expression builders and
constraint translators compose them; codegen calls them rather than
reimplementing the patterns.
"""

from __future__ import annotations

from collections.abc import Callable

from pyspark.sql import Column
from pyspark.sql import functions as F


def error_msg(prefix: str, *value_cols: Column) -> Column:
    """Build an error message: literal prefix followed by interpolated values.

    Each interpolated value is coalesced to a string before concatenation so
    that a NULL value never makes the whole message NULL. `F.concat` returns
    NULL if any argument is NULL, and a NULL message is silently dropped by
    `array_compact` in the array-check path (or the scalar wrapper) -- which
    would discard a real violation whenever the offending value is itself
    NULL (e.g. a linear-reference range `[null, 1.5]`).
    """
    safe = [F.coalesce(c.cast("string"), F.lit("null")) for c in value_cols]
    return F.concat(F.lit(prefix), *safe)


def _resolve_column(column: str | Column) -> Column:
    """Resolve a string column name to a Column, passing Column through."""
    return F.col(column) if isinstance(column, str) else column


def _null_guarded_transform(
    col: Column,
    check_fn: Callable[[Column], Column],
    flatten: bool = False,
) -> Column:
    """Null-guard, transform, optionally flatten, and compact.

    When `flatten=True`, null inner arrays are coalesced to empty before
    flattening.  `F.flatten` returns NULL whenever any inner array is
    NULL, which would silently drop sibling errors -- inner `array_check`
    legitimately returns NULL when its column is null (e.g. an optional
    nested array that's absent on some elements but populated on others).
    """
    transformed = F.transform(col, check_fn)
    if flatten:
        empty = F.array().cast("array<string>")
        transformed = F.flatten(
            F.transform(transformed, lambda inner: F.coalesce(inner, empty))
        )
    return F.when(col.isNotNull(), F.array_compact(transformed))


def array_check(column: str | Column, check_fn: Callable[[Column], Column]) -> Column:
    """Null-guard a column, transform its elements, compact out nulls.

    *check_fn* receives each array element and returns a string Column
    (error message) or null.
    """
    return _null_guarded_transform(_resolve_column(column), check_fn)


def nested_array_check(
    column: str | Column, check_fn: Callable[[Column], Column]
) -> Column:
    """Like `array_check` but flattens nested error arrays.

    Use when *check_fn* itself returns an `array<string>` (e.g. an
    inner `array_check`).  The outer transform produces
    `array<array<string>>`; this function flattens to `array<string>`
    before compacting nulls.
    """
    return _null_guarded_transform(_resolve_column(column), check_fn, flatten=True)


def _map_projection_check(
    column: str | Column,
    projector: Callable[[Column], Column],
    check_fn: Callable[[Column], Column],
) -> Column:
    """Project a map column to an array, then null-guard and transform it.

    *projector* is `F.map_keys` or `F.map_values`.  The projection already
    yields a Column, so this calls `_null_guarded_transform` directly --
    routing through `array_check` would re-resolve an already-resolved
    Column.  A null map column projects to null, which the guard yields
    through as null.
    """
    return _null_guarded_transform(projector(_resolve_column(column)), check_fn)


def map_keys_check(
    column: str | Column, check_fn: Callable[[Column], Column]
) -> Column:
    """Validate a map's keys: project to `map_keys`, then array-check.

    *check_fn* receives each map key and returns a string Column (error
    message) or null. A null map column yields null.
    """
    return _map_projection_check(column, F.map_keys, check_fn)


def map_values_check(
    column: str | Column, check_fn: Callable[[Column], Column]
) -> Column:
    """Validate a map's values: project to `map_values`, then array-check.

    *check_fn* receives each map value and returns a string Column (error
    message) or null. A null map column yields null.
    """
    return _map_projection_check(column, F.map_values, check_fn)


def check_struct_unique(column: str | Column) -> Column:
    """Check that an array has no duplicate items by whole-element comparison.

    Compares `size(col)` against `size(array_distinct(col))`.
    `array_distinct` handles struct and nested-array elements natively
    in Spark 3.4+.

    For string arrays (e.g. websites, socials), this compares raw values.
    Pydantic's UniqueItemsConstraint on `list[HttpUrl]` compares
    *normalized* URLs (adds trailing slash, lowercases host and scheme),
    so it catches duplicates that differ only in normalization.  This
    check catches exact duplicates only — the difference is accepted.
    """
    col = _resolve_column(column)
    has_duplicates = F.size(col) > F.size(F.array_distinct(col))
    return F.when(
        col.isNotNull(),
        F.when(has_duplicates, F.lit("contains duplicate items")),
    )


def coalesce_errors(check: Column) -> Column:
    """Wrap an array-producing check so nulls become empty arrays."""
    return F.coalesce(check, F.array().cast("array<string>"))
