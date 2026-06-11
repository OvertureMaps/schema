# Auto-generated — do not edit.

"""Generated conformance tests for land_cover."""

from __future__ import annotations

import pytest
from overture.schema.pyspark.expressions.generated.overture.schema.base.land_cover import (
    LAND_COVER_SCHEMA,
    land_cover_checks,
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
    "id": "b03200e9-9f2f-52ac-bae8-e562b3fd26cc",
    "geometry": "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 1, 0 0)))",
    "theme": "base",
    "type": "land_cover",
    "version": 0,
    "subtype": "barren",
}


BASE_ROW_POPULATED: dict = {
    "id": "b03200e9-9f2f-52ac-bae8-e562b3fd26cc",
    "bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0},
    "geometry": "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 1, 0 0)))",
    "theme": "base",
    "type": "land_cover",
    "version": 0,
    "sources": [
        {
            "property": "/valid/pointer",
            "dataset": "",
            "license": "clean",
            "record_id": "",
            "update_time": "2024-01-01T00:00:00Z",
            "confidence": 0.0,
            "between": [0.0, 1.0],
        }
    ],
    "subtype": "barren",
    "cartography": {"prominence": 1, "min_zoom": 0, "max_zoom": 0, "sort_key": 0},
}


SCENARIOS: list[Scenario] = [
    Scenario(
        id="land_cover::id:required",
        scaffold={},
        mutate=set_at_path("id", None),
        expected_field="id",
        expected_check="required",
    ),
    Scenario(
        id="land_cover::id:string_min_length",
        scaffold={},
        mutate=set_at_path("id", ""),
        expected_field="id",
        expected_check="string_min_length",
    ),
    Scenario(
        id="land_cover::id:no_whitespace",
        scaffold={},
        mutate=set_at_path("id", "has whitespace"),
        expected_field="id",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="land_cover::bbox:bbox_completeness",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": None, "ymax": 1.0}
        ),
        expected_field="bbox",
        expected_check="bbox_completeness",
    ),
    Scenario(
        id="land_cover::bbox:bbox_lat_ordering",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": 10.0, "ymax": -10.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_ordering",
    ),
    Scenario(
        id="land_cover::bbox:bbox_lat_range",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": -100.0, "ymax": 100.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_range",
    ),
    Scenario(
        id="land_cover::geometry:required",
        scaffold={},
        mutate=set_at_path("geometry", None),
        expected_field="geometry",
        expected_check="required",
    ),
    Scenario(
        id="land_cover::geometry:geometry_type",
        scaffold={},
        mutate=set_at_path("geometry", "POINT (0 0)"),
        expected_field="geometry",
        expected_check="geometry_type",
    ),
    Scenario(
        id="land_cover::theme:required",
        scaffold={},
        mutate=set_at_path("theme", None),
        expected_field="theme",
        expected_check="required",
    ),
    Scenario(
        id="land_cover::theme:enum",
        scaffold={},
        mutate=set_at_path("theme", "__INVALID__"),
        expected_field="theme",
        expected_check="enum",
    ),
    Scenario(
        id="land_cover::type:required",
        scaffold={},
        mutate=set_at_path("type", None),
        expected_field="type",
        expected_check="required",
    ),
    Scenario(
        id="land_cover::type:enum",
        scaffold={},
        mutate=set_at_path("type", "__INVALID__"),
        expected_field="type",
        expected_check="enum",
    ),
    Scenario(
        id="land_cover::version:required",
        scaffold={},
        mutate=set_at_path("version", None),
        expected_field="version",
        expected_check="required",
    ),
    Scenario(
        id="land_cover::version:bounds",
        scaffold={},
        mutate=set_at_path("version", -1),
        expected_field="version",
        expected_check="bounds",
    ),
    Scenario(
        id="land_cover::sources_min_length:array_min_length",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources", []),
        expected_field="sources_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="land_cover::sources_unique:struct_unique",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=lambda row: mutate_unique_items(row, "sources"),
        expected_field="sources_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="land_cover::sources[].property:required",
        scaffold={"sources": [{"dataset": "", "property": "/valid/pointer"}]},
        mutate=set_at_path("sources[].property", None),
        expected_field="sources[].property",
        expected_check="required",
    ),
    Scenario(
        id="land_cover::sources[].property:json_pointer",
        scaffold={"sources": [{"dataset": "", "property": "/valid/pointer"}]},
        mutate=set_at_path("sources[].property", "no-slash"),
        expected_field="sources[].property",
        expected_check="json_pointer",
    ),
    Scenario(
        id="land_cover::sources[].dataset:required",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].dataset", None),
        expected_field="sources[].dataset",
        expected_check="required",
    ),
    Scenario(
        id="land_cover::sources[].license:stripped",
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
        id="land_cover::sources[].confidence:bounds",
        scaffold={
            "sources": [
                {"property": "/valid/pointer", "dataset": "", "confidence": 0.0}
            ]
        },
        mutate=set_at_path("sources[].confidence", -1.0),
        expected_field="sources[].confidence",
        expected_check="bounds",
    ),
    Scenario(
        id="land_cover::sources[].confidence:bounds_1",
        scaffold={
            "sources": [
                {"property": "/valid/pointer", "dataset": "", "confidence": 0.0}
            ]
        },
        mutate=set_at_path("sources[].confidence", 2.0),
        expected_field="sources[].confidence",
        expected_check="bounds",
    ),
    Scenario(
        id="land_cover::sources[].between:linear_range_length",
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
        id="land_cover::sources[].between:linear_range_bounds",
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
        id="land_cover::sources[].between:linear_range_order",
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
        id="land_cover::subtype:required",
        scaffold={},
        mutate=set_at_path("subtype", None),
        expected_field="subtype",
        expected_check="required",
    ),
    Scenario(
        id="land_cover::subtype:enum",
        scaffold={},
        mutate=set_at_path("subtype", "__INVALID__"),
        expected_field="subtype",
        expected_check="enum",
    ),
    Scenario(
        id="land_cover::cartography.prominence:bounds",
        scaffold={"cartography": {"prominence": 1}},
        mutate=set_at_path("cartography.prominence", 0),
        expected_field="cartography.prominence",
        expected_check="bounds",
    ),
    Scenario(
        id="land_cover::cartography.prominence:bounds_1",
        scaffold={"cartography": {"prominence": 1}},
        mutate=set_at_path("cartography.prominence", 101),
        expected_field="cartography.prominence",
        expected_check="bounds",
    ),
    Scenario(
        id="land_cover::cartography.min_zoom:bounds",
        scaffold={"cartography": {"min_zoom": 0}},
        mutate=set_at_path("cartography.min_zoom", -1),
        expected_field="cartography.min_zoom",
        expected_check="bounds",
    ),
    Scenario(
        id="land_cover::cartography.min_zoom:bounds_1",
        scaffold={"cartography": {"min_zoom": 0}},
        mutate=set_at_path("cartography.min_zoom", 24),
        expected_field="cartography.min_zoom",
        expected_check="bounds",
    ),
    Scenario(
        id="land_cover::cartography.max_zoom:bounds",
        scaffold={"cartography": {"max_zoom": 0}},
        mutate=set_at_path("cartography.max_zoom", -1),
        expected_field="cartography.max_zoom",
        expected_check="bounds",
    ),
    Scenario(
        id="land_cover::cartography.max_zoom:bounds_1",
        scaffold={"cartography": {"max_zoom": 0}},
        mutate=set_at_path("cartography.max_zoom", 24),
        expected_field="cartography.max_zoom",
        expected_check="bounds",
    ),
]


@pytest.fixture(scope="module")
def checks() -> list:
    return land_cover_checks()


@pytest.fixture(scope="module")
def sparse_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        LAND_COVER_SCHEMA,
        checks,
        BASE_ROW_SPARSE,
        SCENARIOS,
        feature_name="land_cover",
    )


@pytest.fixture(scope="module")
def populated_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        LAND_COVER_SCHEMA,
        checks,
        BASE_ROW_POPULATED,
        SCENARIOS,
        feature_name="land_cover",
    )


def test_baseline_sparse(sparse_results: ValidationResults) -> None:
    """Sparse base row passes every check the codegen produced.

    Catches drift between base_row synthesis, schema_builder, and
    check_builder -- if any of those produce output inconsistent with
    the others (e.g. a check that rejects values the synthesizer emits
    for required-only fields), the baseline fails here before any
    scenario runs.
    """
    baseline = sparse_results.violations.get("land_cover::baseline", set())
    assert baseline == set(), f"Sparse baseline has violations: {baseline}"


def test_baseline_populated(populated_results: ValidationResults) -> None:
    """Fully-populated base row passes every check the codegen produced.

    Mirrors `test_baseline_sparse` but with all optional fields
    filled, exercising codegen paths that only fire when a value is
    present.
    """
    baseline = populated_results.violations.get("land_cover::baseline", set())
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
        pytest.skip(validation_results.skipped[scenario.id])
    valid_violations = validation_results.violations.get(f"{scenario.id}::valid", set())
    assert expected not in valid_violations
    invalid_violations = validation_results.violations.get(
        f"{scenario.id}::invalid", set()
    )
    assert expected in invalid_violations
