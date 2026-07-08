# Auto-generated — do not edit.

"""Generated conformance tests for bathymetry."""

from __future__ import annotations

import pytest
from overture.schema.pyspark.expressions.generated.overture.schema.base.bathymetry import (
    BATHYMETRY_SCHEMA,
    bathymetry_checks,
)
from pyspark.sql import SparkSession

from ....._support.harness import (
    ValidationResults,
    run_validation_pipeline,
)
from ....._support.helpers import set_at_path
from ....._support.mutations import mutate_unique_items
from ....._support.scenarios import Scenario

BASE_ROW_SPARSE: dict = {
    "id": "e1c02779-55d2-5d7e-8673-b7de1642ae68",
    "geometry": "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 1, 0 0)))",
    "theme": "base",
    "type": "bathymetry",
    "version": 0,
    "depth": 0,
}


BASE_ROW_POPULATED: dict = {
    "id": "e1c02779-55d2-5d7e-8673-b7de1642ae68",
    "bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0},
    "geometry": "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 1, 0 0)))",
    "theme": "base",
    "type": "bathymetry",
    "version": 0,
    "sources": [
        {
            "property": "/valid/pointer",
            "dataset": "",
            "license": "clean",
            "record_id": "",
            "update_time": "2024-01-01T00:00:00Z",
            "confidence": 0.0,
            "provider": "a",
            "resource": "a",
            "version": "a",
            "between": [0.0, 1.0],
        }
    ],
    "depth": 0,
    "cartography": {"prominence": 1, "min_zoom": 0, "max_zoom": 0, "sort_key": 0},
}


SCENARIOS: list[Scenario] = [
    Scenario(
        id="bathymetry::id:required",
        scaffold={},
        mutate=set_at_path("id", None),
        expected_field="id",
        expected_check="required",
    ),
    Scenario(
        id="bathymetry::id:string_min_length",
        scaffold={},
        mutate=set_at_path("id", ""),
        expected_field="id",
        expected_check="string_min_length",
    ),
    Scenario(
        id="bathymetry::id:no_whitespace",
        scaffold={},
        mutate=set_at_path("id", "has whitespace"),
        expected_field="id",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="bathymetry::bbox:bbox_completeness",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": None, "ymax": 1.0}
        ),
        expected_field="bbox",
        expected_check="bbox_completeness",
    ),
    Scenario(
        id="bathymetry::bbox:bbox_lat_ordering",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": 10.0, "ymax": -10.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_ordering",
    ),
    Scenario(
        id="bathymetry::bbox:bbox_lat_range",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": -100.0, "ymax": 100.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_range",
    ),
    Scenario(
        id="bathymetry::geometry:required",
        scaffold={},
        mutate=set_at_path("geometry", None),
        expected_field="geometry",
        expected_check="required",
    ),
    Scenario(
        id="bathymetry::geometry:geometry_type",
        scaffold={},
        mutate=set_at_path("geometry", "POINT (0 0)"),
        expected_field="geometry",
        expected_check="geometry_type",
    ),
    Scenario(
        id="bathymetry::theme:required",
        scaffold={},
        mutate=set_at_path("theme", None),
        expected_field="theme",
        expected_check="required",
    ),
    Scenario(
        id="bathymetry::theme:enum",
        scaffold={},
        mutate=set_at_path("theme", "__INVALID__"),
        expected_field="theme",
        expected_check="enum",
    ),
    Scenario(
        id="bathymetry::type:required",
        scaffold={},
        mutate=set_at_path("type", None),
        expected_field="type",
        expected_check="required",
    ),
    Scenario(
        id="bathymetry::type:enum",
        scaffold={},
        mutate=set_at_path("type", "__INVALID__"),
        expected_field="type",
        expected_check="enum",
    ),
    Scenario(
        id="bathymetry::version:required",
        scaffold={},
        mutate=set_at_path("version", None),
        expected_field="version",
        expected_check="required",
    ),
    Scenario(
        id="bathymetry::version:bounds",
        scaffold={},
        mutate=set_at_path("version", -1),
        expected_field="version",
        expected_check="bounds",
    ),
    Scenario(
        id="bathymetry::sources_min_length:array_min_length",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources", []),
        expected_field="sources_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="bathymetry::sources_unique:struct_unique",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=lambda row: mutate_unique_items(row, "sources"),
        expected_field="sources_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="bathymetry::sources[].property:required",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].property", None),
        expected_field="sources[].property",
        expected_check="required",
    ),
    Scenario(
        id="bathymetry::sources[].property:json_pointer",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].property", "no-slash"),
        expected_field="sources[].property",
        expected_check="json_pointer",
    ),
    Scenario(
        id="bathymetry::sources[].dataset:required",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].dataset", None),
        expected_field="sources[].dataset",
        expected_check="required",
    ),
    Scenario(
        id="bathymetry::sources[].license:stripped",
        scaffold={
            "sources": [
                {"property": "/valid/pointer", "dataset": "", "license": "clean"}
            ]
        },
        mutate=set_at_path("sources[].license", " has spaces "),
        expected_field="sources[].license",
        expected_check="stripped",
    ),
    Scenario(
        id="bathymetry::sources[].confidence_0:bounds",
        scaffold={
            "sources": [
                {"property": "/valid/pointer", "dataset": "", "confidence": 0.0}
            ]
        },
        mutate=set_at_path("sources[].confidence", -1.0),
        expected_field="sources[].confidence_0",
        expected_check="bounds",
    ),
    Scenario(
        id="bathymetry::sources[].confidence_1:bounds",
        scaffold={
            "sources": [
                {"property": "/valid/pointer", "dataset": "", "confidence": 0.0}
            ]
        },
        mutate=set_at_path("sources[].confidence", 2.0),
        expected_field="sources[].confidence_1",
        expected_check="bounds",
    ),
    Scenario(
        id="bathymetry::sources[].provider:string_min_length",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "provider": "a"}]
        },
        mutate=set_at_path("sources[].provider", ""),
        expected_field="sources[].provider",
        expected_check="string_min_length",
    ),
    Scenario(
        id="bathymetry::sources[].provider:snake_case",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "provider": "a"}]
        },
        mutate=set_at_path("sources[].provider", "HAS SPACES"),
        expected_field="sources[].provider",
        expected_check="snake_case",
    ),
    Scenario(
        id="bathymetry::sources[].resource:string_min_length",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "resource": "a"}]
        },
        mutate=set_at_path("sources[].resource", ""),
        expected_field="sources[].resource",
        expected_check="string_min_length",
    ),
    Scenario(
        id="bathymetry::sources[].resource:snake_case",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "resource": "a"}]
        },
        mutate=set_at_path("sources[].resource", "HAS SPACES"),
        expected_field="sources[].resource",
        expected_check="snake_case",
    ),
    Scenario(
        id="bathymetry::sources[].version:string_min_length",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "version": "a"}]
        },
        mutate=set_at_path("sources[].version", ""),
        expected_field="sources[].version",
        expected_check="string_min_length",
    ),
    Scenario(
        id="bathymetry::sources[].version:no_whitespace",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "version": "a"}]
        },
        mutate=set_at_path("sources[].version", "has whitespace"),
        expected_field="sources[].version",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="bathymetry::sources[].between:linear_range_length",
        scaffold={
            "sources": [
                {"property": "/valid/pointer", "dataset": "", "between": [0.0, 1.0]}
            ]
        },
        mutate=set_at_path("sources[].between", [0.5]),
        expected_field="sources[].between",
        expected_check="linear_range_length",
    ),
    Scenario(
        id="bathymetry::sources[].between:linear_range_bounds",
        scaffold={
            "sources": [
                {"property": "/valid/pointer", "dataset": "", "between": [0.0, 1.0]}
            ]
        },
        mutate=set_at_path("sources[].between", [1.5, 2.0]),
        expected_field="sources[].between",
        expected_check="linear_range_bounds",
    ),
    Scenario(
        id="bathymetry::sources[].between:linear_range_order",
        scaffold={
            "sources": [
                {"property": "/valid/pointer", "dataset": "", "between": [0.0, 1.0]}
            ]
        },
        mutate=set_at_path("sources[].between", [0.8, 0.2]),
        expected_field="sources[].between",
        expected_check="linear_range_order",
    ),
    Scenario(
        id="bathymetry::depth:required",
        scaffold={},
        mutate=set_at_path("depth", None),
        expected_field="depth",
        expected_check="required",
    ),
    Scenario(
        id="bathymetry::depth:bounds",
        scaffold={},
        mutate=set_at_path("depth", -1),
        expected_field="depth",
        expected_check="bounds",
    ),
    Scenario(
        id="bathymetry::cartography.prominence_0:bounds",
        scaffold={"cartography": {"prominence": 1}},
        mutate=set_at_path("cartography.prominence", 0),
        expected_field="cartography.prominence_0",
        expected_check="bounds",
    ),
    Scenario(
        id="bathymetry::cartography.prominence_1:bounds",
        scaffold={"cartography": {"prominence": 1}},
        mutate=set_at_path("cartography.prominence", 101),
        expected_field="cartography.prominence_1",
        expected_check="bounds",
    ),
    Scenario(
        id="bathymetry::cartography.min_zoom_0:bounds",
        scaffold={"cartography": {"min_zoom": 0}},
        mutate=set_at_path("cartography.min_zoom", -1),
        expected_field="cartography.min_zoom_0",
        expected_check="bounds",
    ),
    Scenario(
        id="bathymetry::cartography.min_zoom_1:bounds",
        scaffold={"cartography": {"min_zoom": 0}},
        mutate=set_at_path("cartography.min_zoom", 24),
        expected_field="cartography.min_zoom_1",
        expected_check="bounds",
    ),
    Scenario(
        id="bathymetry::cartography.max_zoom_0:bounds",
        scaffold={"cartography": {"max_zoom": 0}},
        mutate=set_at_path("cartography.max_zoom", -1),
        expected_field="cartography.max_zoom_0",
        expected_check="bounds",
    ),
    Scenario(
        id="bathymetry::cartography.max_zoom_1:bounds",
        scaffold={"cartography": {"max_zoom": 0}},
        mutate=set_at_path("cartography.max_zoom", 24),
        expected_field="cartography.max_zoom_1",
        expected_check="bounds",
    ),
]


@pytest.fixture(scope="module")
def checks() -> list:
    return bathymetry_checks()


@pytest.fixture(scope="module")
def sparse_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        BATHYMETRY_SCHEMA,
        checks,
        BASE_ROW_SPARSE,
        SCENARIOS,
        model_name="bathymetry",
    )


@pytest.fixture(scope="module")
def populated_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        BATHYMETRY_SCHEMA,
        checks,
        BASE_ROW_POPULATED,
        SCENARIOS,
        model_name="bathymetry",
    )


def test_baseline_sparse(sparse_results: ValidationResults) -> None:
    """Sparse base row passes every check the codegen produced.

    Catches drift between base_row synthesis, schema_builder, and
    check_builder -- if any of those produce output inconsistent with
    the others (e.g. a check that rejects values the synthesizer emits
    for required-only fields), the baseline fails here before any
    scenario runs.
    """
    baseline = sparse_results.violations.get("bathymetry::baseline", set())
    assert baseline == set(), f"Sparse baseline has violations: {baseline}"


def test_baseline_populated(populated_results: ValidationResults) -> None:
    """Fully-populated base row passes every check the codegen produced.

    Mirrors `test_baseline_sparse` but with all optional fields
    filled, exercising codegen paths that only fire when a value is
    present.
    """
    baseline = populated_results.violations.get("bathymetry::baseline", set())
    assert baseline == set(), f"Populated baseline has violations: {baseline}"


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
def test_scenario_sparse(
    scenario: Scenario,
    sparse_results: ValidationResults,
) -> None:
    _assert_scenario(scenario, sparse_results)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
def test_scenario_populated(
    scenario: Scenario,
    populated_results: ValidationResults,
) -> None:
    _assert_scenario(scenario, populated_results)


def _assert_scenario(
    scenario: Scenario,
    validation_results: ValidationResults,
) -> None:
    expected = (scenario.expected_field, scenario.expected_check)
    if scenario.id in validation_results.skipped:
        # An unbuildable scenario exercises nothing; fail loud rather than skip
        # (a skip reads as a pass and hides codegen/scaffold gaps).
        pytest.fail(
            f"unbuildable scenario {scenario.id!r}: "
            f"{validation_results.skipped[scenario.id]}"
        )
    valid_violations = validation_results.violations.get(f"{scenario.id}::valid", set())
    assert expected not in valid_violations
    invalid_violations = validation_results.violations.get(
        f"{scenario.id}::invalid", set()
    )
    assert expected in invalid_violations
