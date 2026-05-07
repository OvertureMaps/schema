"""Constraint type to PySpark Column expression translation.

Semantic translation layer: maps constraint parameters to Column
expressions that detect violations.  Analogous to
`field_constraint_description.py` in overture-schema-codegen
(which maps constraints to prose).

Each function takes a column accessor (`F.col("x")` or
`el["field"]`) and constraint parameters.  Returns a Column that
evaluates to an error string on violation or null on success.  Field
identity is carried structurally by `Check.field`, not embedded in
error messages.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import reduce
from typing import Literal

from pyspark.sql import Column
from pyspark.sql import functions as F

from overture.schema.system.primitive import GeometryType

from .column_patterns import error_msg

_WKB_TYPE_HEX: dict[GeometryType, str] = {
    GeometryType.POINT: "01",
    GeometryType.LINE_STRING: "02",
    GeometryType.POLYGON: "03",
    GeometryType.MULTI_POINT: "04",
    GeometryType.MULTI_LINE_STRING: "05",
    GeometryType.MULTI_POLYGON: "06",
    GeometryType.GEOMETRY_COLLECTION: "07",
}


_BOUND_OPS: dict[str, tuple[str, Callable[[Column, float | int], Column]]] = {
    "ge": (">=", lambda c, v: c < v),
    "gt": (">", lambda c, v: c <= v),
    "le": ("<=", lambda c, v: c > v),
    "lt": ("<", lambda c, v: c >= v),
}


def check_bounds(
    col: Column,
    *,
    ge: float | int | None = None,
    gt: float | int | None = None,
    le: float | int | None = None,
    lt: float | int | None = None,
) -> Column:
    """Numeric bounds check.  Returns error string or null."""
    checks: list[Column] = []
    for key, value in (("ge", ge), ("gt", gt), ("le", le), ("lt", lt)):
        if value is None:
            continue
        symbol, violates = _BOUND_OPS[key]
        checks.append(
            F.when(
                violates(col, value),
                error_msg(
                    f"must be {symbol} {value}, got ",
                    col.cast("string"),
                ),
            )
        )
    if not checks:
        return F.lit(None).cast("string")
    # null col -> all F.when checks return null (no false positive)
    return F.coalesce(*checks)


def check_enum(
    col: Column,
    allowed: list[str],
) -> Column:
    """Enum membership check.  Returns error string or null."""
    return F.when(
        col.isNotNull() & ~col.isin(allowed),
        error_msg("invalid value '", col.cast("string"), F.lit("'")),
    )


def check_required(col: Column) -> Column:
    """Null check for required fields.  Returns error string or null."""
    return F.when(col.isNull(), F.lit("missing (null)"))


def check_pattern(col: Column, pattern: str, *, label: str) -> Column:
    """Regex pattern check via rlike.  Returns error string or null.

    Parameters
    ----------
    col
        Column to validate.
    pattern
        Java regex pattern (use `\\z` for absolute end-of-input).
    label
        Human-readable description used in error messages:
        `"invalid {label}: got '...'"`
    """
    msg = error_msg(f"invalid {label}: got '", col.cast("string"), F.lit("'"))
    return F.when(col.isNotNull() & ~col.rlike(pattern), msg)


def check_url_format(col: Column) -> Column:
    """HTTP/HTTPS URL format check via pattern match.  Returns error string or null.

    Pydantic's `HttpUrl` additionally normalizes values (adds trailing
    slash, lowercases host and scheme) before validation and comparison.
    This check validates the raw string without normalization — format
    acceptance is broader, and downstream uniqueness checks compare
    un-normalized values.
    """
    return check_pattern(col, r"^https?://[^\s]+\z", label="HTTP/HTTPS URL")


def check_url_length(col: Column) -> Column:
    """URL length check: must not exceed 2083 characters.  Returns error string or null."""
    return F.when(
        col.isNotNull() & (F.length(col) > 2083),
        error_msg("URL exceeds 2083 characters: length ", F.length(col).cast("string")),
    )


def check_email(col: Column) -> Column:
    """Email address format check.  Returns error string or null."""
    return check_pattern(
        col,
        r"^[^\s@.]+(\.[^\s@.]+)*@([^\s@.]+\.)+[^\s@.]+\z",
        label="email address",
    )


def _check_length(
    col: Column,
    measure: Column,
    limit: int,
    *,
    direction: Literal["minimum", "maximum"],
) -> Column:
    """Shared length-check logic for arrays and strings.

    *measure* is the pre-computed size/length column.
    *direction* is `"minimum"` or `"maximum"`, controlling the
    comparison operator and error label.
    """
    violation = measure < limit if direction == "minimum" else measure > limit
    return F.when(
        col.isNotNull() & violation,
        error_msg(f"{direction} length {limit}, got ", measure.cast("string")),
    )


def check_array_min_length(col: Column, min_len: int) -> Column:
    """Array minimum length check.  Returns error string or null."""
    return _check_length(col, F.size(col), min_len, direction="minimum")


def check_array_max_length(col: Column, max_len: int) -> Column:
    """Array maximum length check.  Returns error string or null."""
    return _check_length(col, F.size(col), max_len, direction="maximum")


def check_string_min_length(col: Column, min_len: int) -> Column:
    """String minimum character length check.  Returns error string or null."""
    return _check_length(col, F.length(col), min_len, direction="minimum")


def check_string_max_length(col: Column, max_len: int) -> Column:
    """String maximum character length check.  Returns error string or null."""
    return _check_length(col, F.length(col), max_len, direction="maximum")


_STRIPPED_PATTERN = r"(?sU)^[^\s\p{Cc}](.*[^\s\p{Cc}])?\z"
r"""Java regex: reject whitespace AND control characters at string boundaries.

Boundary class `[^\s\p{Cc}]` rejects two categories at the first and
last character positions:

1. **Whitespace** (`\s` with `(?U)`): Unicode `White_Space` property
   — space, tab, newline, NBSP, em-space, etc.
2. **Control characters** (`\p{Cc}`): Unicode "Control" category —
   C0 (U+0000-001F), DEL (U+007F), and C1 (U+0080-009F).

Why both are needed: Python's `\s` (and `str.strip()`) treats
U+001C-001F (file/group/record/unit separators) as whitespace.  Java's
`\s` with `(?U)` follows the Unicode `White_Space` property, which
excludes those four characters.  Using `\S` alone in Java misses them,
allowing strings like `"Main St \x1f"` to pass.  Adding `\p{Cc}`
closes that gap and also rejects other control characters (NUL, SOH,
DEL, C1 controls) that have no place at string boundaries.

Interior control characters (middle of the string) are NOT rejected —
the `.*` in the middle position still matches anything.  Policing
interior content is a separate concern.

Flags: `(?s)` (DOTALL) lets `.*` cross newlines.  `(?U)`
(UNICODE_CHARACTER_CLASS) gives `\s` full Unicode coverage.  `\z`
(absolute end-of-input) avoids `$` matching before a trailing newline.
"""


def check_stripped(col: Column) -> Column:
    """No leading/trailing whitespace or control characters.  Returns error string or null."""
    return F.when(
        col.isNotNull() & (F.length(col) > 0) & ~col.rlike(_STRIPPED_PATTERN),
        error_msg("leading/trailing whitespace"),
    )


def check_json_pointer(col: Column) -> Column:
    """JSON Pointer (RFC 6901) format check.

    Valid pointers start with `/` or are the empty string (which
    references the whole document).
    """
    return F.when(
        col.isNotNull() & (col != "") & ~col.startswith("/"),
        error_msg(
            "invalid JSON pointer, must start with /, got '",
            col.cast("string"),
            F.lit("'"),
        ),
    )


def check_linear_range_length(col: Column) -> Column:
    """Linear reference range length check: exactly 2 elements."""
    size = F.size(col)
    return F.when(
        col.isNotNull() & (size != 2),
        error_msg("must have exactly 2 elements, got ", size.cast("string")),
    )


def check_linear_range_bounds(col: Column) -> Column:
    """Linear reference range bounds check: both values in [0.0, 1.0].

    The `F.size(col) == 2` guard skips wrong-length arrays so this
    check only fires when exactly two elements are present.  Length
    validation is `check_linear_range_length`'s responsibility.
    """
    size = F.size(col)
    v0, v1 = F.get(col, 0), F.get(col, 1)
    return F.when(
        col.isNotNull()
        & (size == 2)
        & ((v0 < 0.0) | (v0 > 1.0) | (v1 < 0.0) | (v1 > 1.0)),
        error_msg(
            "values must be in [0.0, 1.0], got [",
            v0.cast("string"),
            F.lit(", "),
            v1.cast("string"),
            F.lit("]"),
        ),
    )


def check_linear_range_order(col: Column) -> Column:
    """Linear reference range ordering check: start < end.

    The `F.size(col) == 2` guard skips wrong-length arrays so this
    check only fires when exactly two elements are present.  Length
    validation is `check_linear_range_length`'s responsibility.
    """
    size = F.size(col)
    return F.when(
        col.isNotNull() & (size == 2) & (F.get(col, 0) >= F.get(col, 1)),
        error_msg("start must be < end"),
    )


def check_radio_group(
    cols: list[Column],
    field_names: list[str],
) -> Column:
    """Exactly one of the given boolean columns must be True."""
    true_count = reduce(
        lambda a, b: a + b,
        (F.when(c, 1).otherwise(0) for c in cols),
    )
    names = ", ".join(field_names)
    return F.when(
        true_count != 1,
        error_msg(
            f"exactly one of {names} must be true, got ",
            true_count.cast("string"),
            F.lit(" true"),
        ),
    )


def _count_non_null(cols: list[Column]) -> Column:
    """Sum of non-null indicators across *cols*."""
    return reduce(
        lambda a, b: a + b,
        (F.when(c.isNotNull(), 1).otherwise(0) for c in cols),
    )


def check_require_any_of(
    cols: list[Column],
    field_names: list[str],
) -> Column:
    """At least one of the given columns must be non-null."""
    all_null = reduce(lambda a, b: a & b, (c.isNull() for c in cols))
    names = ", ".join(field_names)
    return F.when(all_null, F.lit(f"requires at least one of {names}"))


def check_min_fields_set(
    cols: list[Column],
    field_names: list[str],
    count: int,
) -> Column:
    """At least *count* of the given columns must be non-null.

    Parameters
    ----------
    cols
        Column expressions to test for non-null.
    field_names
        Human-readable names for each column, used in the error message.
    count
        Minimum number of non-null columns required.

    Returns
    -------
    Column
        Error string on violation, null on success.
    """
    non_null_count = _count_non_null(cols)
    names = ", ".join(field_names)
    return F.when(
        non_null_count < count,
        error_msg(
            f"at least {count} of {names} required, got ",
            non_null_count.cast("string"),
            F.lit(" non-null"),
        ),
    )


def _check_conditional_presence(
    target: Column,
    condition: Column,
    condition_desc: str,
    *condition_value_cols: Column,
    expect_present: bool,
) -> Column:
    """Shared logic for require_if / forbid_if.

    *expect_present=True* means target must be non-null when condition
    holds (require); *False* means target must be null (forbid).
    """
    word = "required" if expect_present else "forbidden"
    target_test = target.isNull() if expect_present else target.isNotNull()
    prefix = f"{word} when {condition_desc}"
    if condition_value_cols:
        interleaved = [
            p
            for vc in condition_value_cols
            for p in (F.lit(", got "), vc.cast("string"))
        ]
        msg = error_msg(prefix, *interleaved)
    else:
        msg = F.lit(prefix)
    return F.when(condition & target_test, msg)


def check_require_if(
    target: Column,
    condition: Column,
    condition_desc: str,
    *condition_value_cols: Column,
) -> Column:
    """Target must be non-null when condition is true."""
    return _check_conditional_presence(
        target,
        condition,
        condition_desc,
        *condition_value_cols,
        expect_present=True,
    )


def check_forbid_if(
    target: Column,
    condition: Column,
    condition_desc: str,
    *condition_value_cols: Column,
) -> Column:
    """Target must be null when condition is true."""
    return _check_conditional_presence(
        target,
        condition,
        condition_desc,
        *condition_value_cols,
        expect_present=False,
    )


def check_geometry_type(
    col: Column,
    *allowed: GeometryType,
) -> Column:
    """Geometry type check via WKB header byte parsing.

    Reads the endianness indicator and type uint32 from the WKB binary
    without deserializing coordinates.  O(1) per row regardless of
    geometry complexity.

    Extracts only the low byte of the type uint32, which is safe for
    OGC types 1-7 and immune to Z/M/ZM flag bits (those modify high
    bytes only).
    """
    hex_geom = F.hex(col)
    byte_order = F.substring(hex_geom, 1, 2)
    # LE: type LSB at hex positions 3-4
    # BE: type LSB at hex positions 9-10
    type_hex = F.when(
        byte_order == "01",
        F.substring(hex_geom, 3, 2),
    ).otherwise(
        F.substring(hex_geom, 9, 2),
    )
    allowed_hex = [_WKB_TYPE_HEX[t] for t in allowed]
    names = " | ".join(t.geo_json_type for t in allowed)
    if len(allowed_hex) == 1:
        violation = type_hex != allowed_hex[0]
    else:
        violation = ~type_hex.isin(allowed_hex)
    return F.when(
        col.isNotNull() & violation,
        error_msg(f"expected {names} geometry"),
    )


def check_bbox_completeness(col: Column) -> Column:
    """Check that all bbox sub-fields are present when bbox is non-null."""
    return F.when(
        col.isNotNull()
        & (
            col["xmin"].isNull()
            | col["ymin"].isNull()
            | col["xmax"].isNull()
            | col["ymax"].isNull()
        ),
        error_msg("bbox sub-fields must all be present"),
    )


def check_bbox_lat_ordering(col: Column) -> Column:
    """Check that ymin does not exceed ymax."""
    return F.when(
        col.isNotNull() & (col["ymin"] > col["ymax"]),
        error_msg("expected ymin <= ymax"),
    )


def check_bbox_lat_range(col: Column) -> Column:
    """Check that latitude values fall within [-90, 90]."""
    return F.when(
        col.isNotNull()
        & (
            (col["ymin"] < -90)
            | (col["ymin"] > 90)
            | (col["ymax"] < -90)
            | (col["ymax"] > 90)
        ),
        error_msg("latitude values must be in [-90, 90]"),
    )


# TODO: check_bbox_lon_ordering -- deferred pending antimeridian crossing
# policy. RFC 7946 section 5.2 allows xmin > xmax for bboxes that cross
# the antimeridian.

# TODO: check_bbox_lon_range -- deferred pending decision on whether
# coordinates can wrap beyond [-180, 180].
