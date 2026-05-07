"""Validation harness for generated conformance tests.

Builds a single DataFrame per feature type from scenario mutations,
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
from pyspark.sql.types import StringType, StructField, StructType
from shapely import wkb, wkt

from .helpers import PathTraversalError, deep_merge
from .scenarios import Scenario

# Namespace for `_scenario_id` UUIDs. Distinct from
# `overture.schema.codegen.pyspark.test_data.base_row._BASE_ROW_NAMESPACE`
# (which synthesizes feature `id` values) so a feature `id` can never
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
    feature_name: str,
) -> dict[str, str]:
    """Map _scenario_id values to human-readable scenario IDs.

    Parameters
    ----------
    scenarios
        All scenarios for a feature type.
    feature_name
        Feature name for the baseline row ID.

    Returns
    -------
    dict[str, str]
        Maps _scenario_id UUID string -> scenario ID. Includes baseline.

    Raises
    ------
    ValueError
        If two scenarios would produce the same UUID key.
    """
    baseline_id = f"{feature_name}::baseline"
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
    feature_name: str,
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, str]]:
    """Build mutation rows and scenario mapping from scenarios.

    Parameters
    ----------
    base_row
        Valid base row dict from the example loader.
    scenarios
        Scenarios to apply.
    feature_name
        Feature name for baseline ID and UUID namespace.

    Returns
    -------
    tuple
        (rows, scenario_map, skipped) where rows is a list of row dicts,
        scenario_map maps _scenario_id values to scenario IDs, and skipped
        maps scenario IDs to skip reasons.
    """
    scenario_map = build_scenario_map(scenarios, feature_name=feature_name)
    base_row = sanitize_row(base_row)
    # Deep-copy every row so nested structures aren't aliased with base_row;
    # a future in-place mutation of one row would otherwise leak across rows.
    rows: list[dict[str, Any]] = [
        {
            **copy.deepcopy(base_row),
            "_scenario_id": scenario_uuid(f"{feature_name}::baseline"),
        }
    ]
    skipped: dict[str, str] = {}

    for s in scenarios:
        try:
            invalid_row = sanitize_row(s.mutate(deep_merge(base_row, s.scaffold)))
            invalid_row["_scenario_id"] = scenario_uuid(f"{s.id}::invalid")
            rows.append(
                {
                    **copy.deepcopy(base_row),
                    "_scenario_id": scenario_uuid(f"{s.id}::valid"),
                }
            )
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
    """Assert every check's root field exists in the schema.

    Synthetic model-level checks (`root_field=None`) pass
    unconditionally. Otherwise the root must be a top-level schema
    column. This is a fast sanity check; deeper field paths are the
    codegen's responsibility and surface at Spark execution time.
    """
    top_level = {f.name for f in schema.fields}
    for chk in checks:
        if chk.root_field is None or chk.root_field in top_level:
            continue
        raise AssertionError(
            f"Check references root field {chk.root_field!r} "
            f"not found in schema. Available: {sorted(top_level)}"
        )


def run_validation_pipeline(
    spark: SparkSession,
    schema: StructType,
    checks: list[Check],
    base_row: dict[str, Any],
    scenarios: Sequence[Scenario],
    feature_name: str,
) -> ValidationResults:
    """Run the full validation pipeline.

    Returns a ValidationResults with violations indexed by scenario ID and
    a skipped dict for scenarios that could not be built due to path
    traversal errors.
    """
    assert_schema_covers_checks(schema, checks)
    rows, scenario_map, skipped = build_scenario_rows(
        base_row, scenarios, feature_name=feature_name
    )
    augmented_schema = StructType(
        schema.fields + [StructField("_scenario_id", StringType(), True)]
    )
    df = spark.createDataFrame(rows, schema=augmented_schema, verifySchema=False)  # type: ignore[union-attr]
    violations = explain_errors(evaluate_checks(df, checks), checks)
    return ValidationResults(
        violations=index_violations(violations.collect(), scenario_map),
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
