"""Generate constraint-violating values for the rendered conformance tests.

`invalid_value` returns a concrete value that violates a given check. The
generated tests inject these into otherwise-valid rows to confirm that
each constraint produces the expected violation.
"""

from __future__ import annotations

from overture.schema.system.primitive.geom import GeometryType

from ..constraint_dispatch import ExpressionDescriptor
from .constraint_values import (
    CONSTRAINT_VALUES,
    curated_pattern_values,
    invalid_bound,
    uncurated_pattern_error,
)

__all__ = ["invalid_value"]

# Ordered candidates for the invalid geometry side (first not in allowed set wins)
_INVALID_GEOMETRY_CANDIDATES: tuple[tuple[GeometryType, str], ...] = (
    (GeometryType.POINT, "POINT (0 0)"),
    (GeometryType.LINE_STRING, "LINESTRING (0 0, 1 1)"),
    (GeometryType.GEOMETRY_COLLECTION, "GEOMETRYCOLLECTION EMPTY"),
)


# Direct lookup: check function name -> invalid value (no descriptor inspection).
# Reserved for checks with no associated constraint type (url/email, linear_range,
# bbox, required, enum, and min-length literals).
_INVALID_LITERALS: dict[str, object] = {
    "check_required": None,
    "check_enum": "__INVALID__",
    "check_url_format": "not-a-url",
    "check_url_length": "https://" + "x" * 2076,
    "check_email": "not-an-email",
    "check_array_min_length": [],
    "check_string_min_length": "",
    "check_linear_range_length": [0.5],
    "check_linear_range_bounds": [1.5, 2.0],
    "check_linear_range_order": [0.8, 0.2],
    "check_bbox_completeness": {"xmin": 0.0, "xmax": 1.0, "ymin": None, "ymax": 1.0},
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
        For unrecognised check function names, unknown `constraint_type`
        on `check_pattern` descriptors, or when all geometry candidates
        are in the allowed set.
    """
    fn = desc.function
    # Constraint-type lookup precedes function-name lookup: any type present in
    # CONSTRAINT_VALUES resolves via the table even when its check function also
    # appears in _INVALID_LITERALS (e.g. check_stripped, check_json_pointer).
    if desc.constraint_type in CONSTRAINT_VALUES:
        return CONSTRAINT_VALUES[desc.constraint_type].invalid
    if fn in _INVALID_LITERALS:
        return _INVALID_LITERALS[fn]
    if fn == "check_bounds":
        return invalid_bound(desc)
    if fn == "check_pattern":
        if (curated := curated_pattern_values(desc)) is not None:
            return curated.invalid
        raise uncurated_pattern_error(desc, side="invalid")
    if fn == "check_array_max_length":
        max_len = int(desc.args[0])  # type: ignore[call-overload]
        return [{}] * (max_len + 1)
    if fn == "check_string_max_length":
        max_len = int(desc.args[0])  # type: ignore[call-overload]
        return "x" * (max_len + 1)
    if fn == "check_geometry_type":
        return _invalid_geometry(desc)
    raise ValueError(f"No invalid value defined for check function: {fn!r}")


def _invalid_geometry(desc: ExpressionDescriptor) -> str:
    allowed = set(desc.args)
    for geom_type, wkt in _INVALID_GEOMETRY_CANDIDATES:
        if geom_type not in allowed:
            return wkt
    raise ValueError(
        f"All geometry candidates are in the allowed set: {allowed!r}. "
        "Cannot produce an invalid geometry value."
    )
