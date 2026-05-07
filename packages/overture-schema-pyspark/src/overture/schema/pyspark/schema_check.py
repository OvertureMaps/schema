"""Schema comparison for structural validation.

Recursively diffs two `StructType` objects and reports mismatches
as a flat list with dot-notation paths.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pyspark.sql.types import (
    ArrayType,
    DataType,
    MapType,
    StructType,
)

# First struct (`.`), array (`[]`), or map (`{key}`/`{value}`) step marker
# in an encoded path; everything before it is the top-level column.
_STEP_MARKER = re.compile(r"[.\[{]")


@dataclass(frozen=True)
class SchemaMismatch:
    """One structural difference between actual and expected schemas.

    Parameters
    ----------
    path
        Dot-notation path to the field (e.g. `"bbox.xmin"`).
    actual
        Actual type name, or `"missing"` if the field is absent.
    expected
        Expected type name, or `"missing"` if the field is unexpected.
    """

    path: str
    actual: str
    expected: str

    @property
    def root(self) -> str:
        """Top-level schema column this mismatch belongs to.

        Strips the struct/array/map step markers `_compare` embeds in
        `path` (e.g. `sources[].confidence` -> `sources`), leaving the
        column name that matches a `Check.read_columns` entry.
        """
        return _STEP_MARKER.split(self.path, maxsplit=1)[0]


def _type_name(dt: DataType) -> str:
    """Short display name for a DataType (e.g. `"StringType"`)."""
    return type(dt).__name__


def _compare(
    actual: DataType,
    expected: DataType,
    prefix: str,
    out: list[SchemaMismatch],
) -> None:
    """Recursively compare two DataType trees."""
    if isinstance(expected, StructType) and isinstance(actual, StructType):
        _compare_structs(actual, expected, prefix, out)
        return

    if isinstance(expected, ArrayType) and isinstance(actual, ArrayType):
        _compare(actual.elementType, expected.elementType, f"{prefix}[]", out)
        return

    if isinstance(expected, MapType) and isinstance(actual, MapType):
        _compare(actual.keyType, expected.keyType, f"{prefix}{{key}}", out)
        _compare(actual.valueType, expected.valueType, f"{prefix}{{value}}", out)
        return

    if type(actual) is not type(expected):
        out.append(SchemaMismatch(prefix, _type_name(actual), _type_name(expected)))


def _compare_structs(
    actual: StructType,
    expected: StructType,
    prefix: str,
    out: list[SchemaMismatch],
) -> None:
    """Compare two StructTypes field by field."""
    actual_fields = {f.name: f for f in actual.fields}
    expected_fields = {f.name: f for f in expected.fields}

    # Ordered union: actual fields first, then any expected-only fields appended.
    all_names = dict.fromkeys([*actual_fields, *expected_fields])
    for name in all_names:
        path = f"{prefix}.{name}" if prefix else name
        a = actual_fields.get(name)
        e = expected_fields.get(name)
        if a is None and e is not None:
            out.append(SchemaMismatch(path, "missing", _type_name(e.dataType)))
        elif e is None and a is not None:
            out.append(SchemaMismatch(path, _type_name(a.dataType), "missing"))
        elif a is not None and e is not None:
            _compare(a.dataType, e.dataType, path, out)


def compare_schemas(actual: StructType, expected: StructType) -> list[SchemaMismatch]:
    """Compare two Spark schemas and return all mismatches.

    Parameters
    ----------
    actual
        Schema inferred from the data (e.g. `df.schema`).
    expected
        Declared expected schema for the feature type.

    Returns
    -------
    list[SchemaMismatch]
        Empty when schemas match. Each mismatch identifies the
        dot-notation path and what differs.
    """
    out: list[SchemaMismatch] = []
    _compare_structs(actual, expected, "", out)
    return out
