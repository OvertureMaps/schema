"""Generate constraint-violating values for the rendered conformance tests.

`invalid_value` returns a concrete value that violates a given check. The
generated tests inject these into otherwise-valid rows to confirm that
each constraint produces the expected violation.
"""

from __future__ import annotations

from overture.schema.system.field_constraint.string import (
    CountryCodeAlpha2Constraint,
    HexColorConstraint,
    LanguageTagConstraint,
    NoWhitespaceConstraint,
    PhoneNumberConstraint,
    RegionCodeConstraint,
    SnakeCaseConstraint,
    WikidataIdConstraint,
)
from overture.schema.system.primitive.geom import GeometryType

from ..constraint_dispatch import ExpressionDescriptor

__all__ = ["invalid_value"]

# Ordered candidates for the invalid geometry side (first not in allowed set wins)
_INVALID_GEOMETRY_CANDIDATES: tuple[tuple[GeometryType, str], ...] = (
    (GeometryType.POINT, "POINT (0 0)"),
    (GeometryType.LINE_STRING, "LINESTRING (0 0, 1 1)"),
    (GeometryType.GEOMETRY_COLLECTION, "GEOMETRYCOLLECTION EMPTY"),
)


# Pattern-constraint -> sample value that violates the pattern.
# Used by `check_pattern` whose constraint_type identifies which validator.
_INVALID_PATTERN_VALUES: dict[type, str] = {
    NoWhitespaceConstraint: "has whitespace",
    CountryCodeAlpha2Constraint: "99",
    RegionCodeConstraint: "99-999",
    SnakeCaseConstraint: "HAS SPACES",
    PhoneNumberConstraint: "1234567890",
    WikidataIdConstraint: "P999",
    HexColorConstraint: "not-hex",
    LanguageTagConstraint: "123",
}

# Direct lookup: check function name -> invalid value (no descriptor inspection).
_INVALID_LITERALS: dict[str, object] = {
    "check_required": None,
    "check_enum": "__INVALID__",
    "check_url_format": "not-a-url",
    "check_url_length": "https://" + "x" * 2076,
    "check_email": "not-an-email",
    "check_stripped": " has spaces ",
    "check_json_pointer": "no-slash",
    "check_array_min_length": [],
    "check_string_min_length": "",
    "check_linear_range_length": [0.5],
    "check_linear_range_bounds": [1.5, 2.0],
    "check_linear_range_order": [0.8, 0.2],
    "check_bbox_completeness": {"xmin": 0.0, "xmax": 1.0, "ymin": None, "ymax": 1.0},
    "check_bbox_lat_ordering": {"xmin": 0.0, "xmax": 1.0, "ymin": 10.0, "ymax": -10.0},
    "check_bbox_lat_range": {"xmin": 0.0, "xmax": 1.0, "ymin": -100.0, "ymax": 100.0},
}


def invalid_value(desc: ExpressionDescriptor) -> object:
    """Return a Python value that violates `desc`'s check function.

    Parameters
    ----------
    desc
        The expression descriptor to produce an invalid value for.

    Raises
    ------
    ValueError
        For unrecognised check function names or when all geometry candidates
        are in the allowed set.
    """
    fn = desc.function
    if fn in _INVALID_LITERALS:
        return _INVALID_LITERALS[fn]
    if fn == "check_bounds":
        return _invalid_bound(desc)
    if fn == "check_pattern":
        return _INVALID_PATTERN_VALUES.get(desc.constraint_type, "!!!INVALID!!!")  # type: ignore[arg-type]
    if fn == "check_array_max_length":
        max_len = int(desc.args[0])  # type: ignore[call-overload]
        return [{}] * (max_len + 1)
    if fn == "check_string_max_length":
        max_len = int(desc.args[0])  # type: ignore[call-overload]
        return "x" * (max_len + 1)
    if fn == "check_geometry_type":
        return _invalid_geometry(desc)
    raise ValueError(f"No invalid value defined for check function: {fn!r}")


def _invalid_bound(desc: ExpressionDescriptor) -> object:
    """Produce a value violating a bounds check for invalid-value generation.

    The `ge` / `le` branches return one below / above the bound. For
    `ge=0` this returns `-1`, which violates the bound but would also
    underflow an unsigned base type. No schema today combines `ge=0` with
    an unsigned terminal -- if that ever changes, the caller will need to
    consult the base type and pick a sentinel (e.g. a string or null) for
    the violating value.
    """
    kwargs = dict(desc.kwargs)
    if "ge" in kwargs:
        return kwargs["ge"] - 1  # type: ignore[operator]
    if "gt" in kwargs:
        return kwargs["gt"]
    if "le" in kwargs:
        return kwargs["le"] + 1  # type: ignore[operator]
    if "lt" in kwargs:
        return kwargs["lt"]
    raise ValueError(f"No recognised bound key in kwargs: {kwargs!r}")


def _invalid_geometry(desc: ExpressionDescriptor) -> str:
    allowed = set(desc.args)
    for geom_type, wkt in _INVALID_GEOMETRY_CANDIDATES:
        if geom_type not in allowed:
            return wkt
    raise ValueError(
        f"All geometry candidates are in the allowed set: {allowed!r}. "
        "Cannot produce an invalid geometry value."
    )
