"""Validation harness for generated conformance tests.

Builds a single DataFrame per model type from scenario mutations,
runs validation once, and indexes violations by scenario ID.
"""

from __future__ import annotations

import copy
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from overture.schema.pyspark.check import Check
from overture.schema.pyspark.validate import evaluate_checks, explain_errors
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    ArrayType,
    DataType,
    DoubleType,
    FloatType,
    MapType,
    StringType,
    StructField,
    StructType,
)
from shapely import wkb, wkt

from .helpers import PathTraversalError, deep_merge
from .scenarios import Scenario

# Namespace for `_scenario_id` UUIDs. Distinct from
# `overture.schema.codegen.pyspark.test_data.base_row._BASE_ROW_NAMESPACE`
# (which synthesizes model `id` values) so a model `id` can never
# collide with a scenario tag and confuse the violations index.
_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


@dataclass(frozen=True)
class ValidationResults:
    """Named return type from run_validation_pipeline."""

    violations: dict[str, set[tuple[str, str]]]
    skipped: dict[str, str]


def scenario_uuid(scenario_id: str) -> str:
    """Deterministic UUID for the harness's `_scenario_id` tag."""
    return str(uuid.uuid5(_NAMESPACE, scenario_id))


def build_scenario_map(
    scenarios: Sequence[Scenario],
    *,
    model_name: str,
) -> dict[str, str]:
    """Map _scenario_id values to human-readable scenario IDs.

    Parameters
    ----------
    scenarios
        All scenarios for a model type.
    model_name
        Model name for the baseline row ID.

    Returns
    -------
    dict[str, str]
        Maps _scenario_id UUID string -> scenario ID. Includes baseline.

    Raises
    ------
    ValueError
        If two scenarios would produce the same UUID key.
    """
    baseline_id = f"{model_name}::baseline"
    scenario_map: dict[str, str] = {scenario_uuid(baseline_id): baseline_id}

    for s in scenarios:
        for suffix in ("::valid", "::invalid"):
            label = f"{s.id}{suffix}"
            key = scenario_uuid(label)
            if key in scenario_map:
                raise ValueError(
                    f"Duplicate scenario id {key!r}: {scenario_map[key]!r} and {label!r}"
                )
            scenario_map[key] = label

    return scenario_map


def build_scenario_rows(
    base_row: dict[str, Any],
    scenarios: Sequence[Scenario],
    *,
    model_name: str,
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, str]]:
    """Build mutation rows and scenario mapping from scenarios.

    Parameters
    ----------
    base_row
        Valid base row dict from the example loader.
    scenarios
        Scenarios to apply.
    model_name
        Model name for baseline ID and UUID namespace.

    Returns
    -------
    tuple
        (rows, scenario_map, skipped) where rows is a list of row dicts,
        scenario_map maps _scenario_id values to scenario IDs, and skipped
        maps scenario IDs to skip reasons.
    """
    scenario_map = build_scenario_map(scenarios, model_name=model_name)
    base_row = sanitize_row(base_row)
    # Deep-copy every row so nested structures aren't aliased with base_row;
    # a future in-place mutation of one row would otherwise leak across rows.
    rows: list[dict[str, Any]] = [
        {
            **copy.deepcopy(base_row),
            "_scenario_id": scenario_uuid(f"{model_name}::baseline"),
        }
    ]
    skipped: dict[str, str] = {}

    for s in scenarios:
        try:
            invalid_row = sanitize_row(s.mutate(deep_merge(base_row, s.scaffold)))
            invalid_row["_scenario_id"] = scenario_uuid(f"{s.id}::invalid")
            # The valid row exercises a real value at the check's target: it
            # merges the scaffold (a constraint-satisfying structure reaching
            # the target) onto the base row, with NO mutation. A scenario may
            # override with `valid_scaffold` to seed a specific value -- e.g.
            # the literal alternative of an `X | Literal[c]` field. Without a
            # valid scaffold the assertion would be vacuous: a target reachable
            # only through scaffolded nesting is absent from a plain base-row
            # copy, so a check that wrongly rejects a valid value passes green.
            valid_source = (
                s.valid_scaffold if s.valid_scaffold is not None else s.scaffold
            )
            valid_row = sanitize_row(deep_merge(base_row, valid_source))
            valid_row["_scenario_id"] = scenario_uuid(f"{s.id}::valid")
            rows.append(valid_row)
            rows.append(invalid_row)
        except PathTraversalError as e:
            skipped[s.id] = str(e)

    return rows, scenario_map, skipped


_WKT_PREFIXES = (
    "POINT",
    "LINESTRING",
    "POLYGON",
    "MULTIPOINT",
    "MULTILINESTRING",
    "MULTIPOLYGON",
    "GEOMETRYCOLLECTION",
)

# Schema field whose string value should be parsed as WKT and re-emitted as
# WKB (the storage representation Spark's BinaryType expects).
_GEOMETRY_FIELD = "geometry"


def sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of `row` with WKT geometry strings converted to WKB.

    Geometry values from TOML examples are WKT strings, but the schema
    expects BinaryType (WKB). Walks the row recursively; any string at
    the `geometry` key that looks like WKT is converted via shapely.
    """
    return _sanitize_in_place(copy.deepcopy(row))


def _sanitize_in_place(d: dict[str, Any]) -> dict[str, Any]:
    for key, value in d.items():
        if isinstance(value, dict):
            d[key] = _sanitize_in_place(value)
        elif isinstance(value, list):
            d[key] = [
                _sanitize_in_place(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif (
            key == _GEOMETRY_FIELD
            and isinstance(value, str)
            and value.upper().startswith(_WKT_PREFIXES)
        ):
            d[key] = wkb.dumps(wkt.loads(value))
    return d


def assert_schema_covers_checks(schema: StructType, checks: list[Check]) -> None:
    """Assert every column a check reads exists in the schema.

    Covers field and model-level checks alike: each top-level column in a
    check's `read_columns` must be a schema column. This is a fast sanity
    check; deeper field paths are the codegen's responsibility and surface
    at Spark execution time.
    """
    top_level = {f.name for f in schema.fields}
    for chk in checks:
        missing = chk.read_columns - top_level
        if missing:
            raise AssertionError(
                f"Check reads columns {sorted(missing)} "
                f"not found in schema. Available: {sorted(top_level)}"
            )


_FLOAT_TYPES = (DoubleType, FloatType)


def coerce_to_schema(value: Any, dtype: DataType) -> Any:
    """Cast Python ints to floats where the schema declares a float column.

    A discriminated union widens a numeric field to the broadest member type
    (e.g. a `uint8` value alongside `float64` values becomes a `DoubleType`
    column). A scaffold built for the narrow arm carries a Python `int`, which
    Spark stores as null in a `DoubleType` column (`createDataFrame` does not
    coerce with `verifySchema=False`) -- a null that fires `required` on the
    `::valid` row. Recursing the row against the schema aligns each numeric
    value with its declared column type, so a valid row stays valid. `bool` is
    excluded (it is an `int` subclass but maps to `BooleanType`).

    The struct branch keeps only keys the schema declares, mirroring how
    `createDataFrame` reads a dict by field name -- so this also drops any
    key absent from `dtype`. No row carries such keys today; the filtering is
    incidental, not a guarantee.
    """
    if value is None:
        return None
    if isinstance(dtype, StructType) and isinstance(value, dict):
        return {
            f.name: coerce_to_schema(value[f.name], f.dataType)
            for f in dtype.fields
            if f.name in value
        }
    if isinstance(dtype, ArrayType) and isinstance(value, list):
        return [coerce_to_schema(item, dtype.elementType) for item in value]
    if isinstance(dtype, MapType) and isinstance(value, dict):
        return {k: coerce_to_schema(v, dtype.valueType) for k, v in value.items()}
    if (
        isinstance(dtype, _FLOAT_TYPES)
        and isinstance(value, int)
        and not isinstance(value, bool)
    ):
        return float(value)
    return value


def run_validation_pipeline(
    spark: SparkSession,
    schema: StructType,
    checks: list[Check],
    base_row: dict[str, Any],
    scenarios: Sequence[Scenario],
    model_name: str,
) -> ValidationResults:
    """Run the full validation pipeline.

    Returns a ValidationResults with violations indexed by scenario ID and
    a skipped dict for scenarios that could not be built due to path
    traversal errors.
    """
    assert_schema_covers_checks(schema, checks)
    rows, scenario_map, skipped = build_scenario_rows(
        base_row, scenarios, model_name=model_name
    )
    augmented_schema = StructType(
        schema.fields + [StructField("_scenario_id", StringType(), True)]
    )
    rows = [coerce_to_schema(row, augmented_schema) for row in rows]
    df = spark.createDataFrame(rows, schema=augmented_schema, verifySchema=False)  # type: ignore[union-attr]
    violations = explain_errors(evaluate_checks(df, checks), checks)
    indexed = violations.select("_scenario_id", "field", "check")
    return ValidationResults(
        violations=index_violations(indexed.collect(), scenario_map),
        skipped=skipped,
    )


def index_violations(
    violation_rows: list[Any],
    scenario_map: dict[str, str],
) -> dict[str, set[tuple[str, str]]]:
    """Index collected violation rows by human-readable scenario ID.

    Parameters
    ----------
    violation_rows
        Collected rows from `explain().collect()`.
    scenario_map
        Mapping from _scenario_id values to scenario IDs.
    """
    result: dict[str, set[tuple[str, str]]] = {}
    for row in violation_rows:
        scenario_id = scenario_map.get(row["_scenario_id"])
        if scenario_id is None:
            continue
        result.setdefault(scenario_id, set()).add((row["field"], row["check"]))
    return result
