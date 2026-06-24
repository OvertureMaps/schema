# Auto-generated — do not edit.

"""Generated conformance tests for division_boundary."""

from __future__ import annotations

import pytest
from overture.schema.pyspark.expressions.generated.overture.schema.divisions.division_boundary import (
    DIVISION_BOUNDARY_SCHEMA,
    division_boundary_checks,
)
from pyspark.sql import SparkSession

from ....._support.harness import (
    ValidationResults,
    run_validation_pipeline,
)
from ....._support.helpers import set_at_path
from ....._support.mutations import (
    mutate_forbid_if,
    mutate_radio_group,
    mutate_require_if,
    mutate_unique_items,
)
from ....._support.scenarios import Scenario

BASE_ROW_SPARSE: dict = {
    "id": "3c9e8190-33ce-5962-9668-d467336901b4",
    "geometry": "LINESTRING (0 0, 1 1)",
    "theme": "divisions",
    "type": "division_boundary",
    "version": 0,
    "subtype": "country",
    "class": "land",
    "division_ids": ["a", "a1"],
    "is_land": True,
    "admin_level": 0,
}


BASE_ROW_POPULATED: dict = {
    "id": "3c9e8190-33ce-5962-9668-d467336901b4",
    "bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0},
    "geometry": "LINESTRING (0 0, 1 1)",
    "theme": "divisions",
    "type": "division_boundary",
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
    "subtype": "country",
    "class": "land",
    "is_land": True,
    "is_territorial": False,
    "division_ids": ["a", "a1"],
    "region": "US-CA",
    "admin_level": 0,
    "is_disputed": False,
    "perspectives": {"mode": "accepted_by", "countries": ["US"]},
}


SCENARIOS: list[Scenario] = [
    Scenario(
        id="division_boundary::id:required",
        scaffold={},
        mutate=set_at_path("id", None),
        expected_field="id",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::id:string_min_length",
        scaffold={},
        mutate=set_at_path("id", ""),
        expected_field="id",
        expected_check="string_min_length",
    ),
    Scenario(
        id="division_boundary::id:no_whitespace",
        scaffold={},
        mutate=set_at_path("id", "has whitespace"),
        expected_field="id",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="division_boundary::bbox:bbox_completeness",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": None, "ymax": 1.0}
        ),
        expected_field="bbox",
        expected_check="bbox_completeness",
    ),
    Scenario(
        id="division_boundary::bbox:bbox_lat_ordering",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": 10.0, "ymax": -10.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_ordering",
    ),
    Scenario(
        id="division_boundary::bbox:bbox_lat_range",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": -100.0, "ymax": 100.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_range",
    ),
    Scenario(
        id="division_boundary::geometry:required",
        scaffold={},
        mutate=set_at_path("geometry", None),
        expected_field="geometry",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::geometry:geometry_type",
        scaffold={},
        mutate=set_at_path("geometry", "POINT (0 0)"),
        expected_field="geometry",
        expected_check="geometry_type",
    ),
    Scenario(
        id="division_boundary::theme:required",
        scaffold={},
        mutate=set_at_path("theme", None),
        expected_field="theme",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::theme:enum",
        scaffold={},
        mutate=set_at_path("theme", "__INVALID__"),
        expected_field="theme",
        expected_check="enum",
    ),
    Scenario(
        id="division_boundary::type:required",
        scaffold={},
        mutate=set_at_path("type", None),
        expected_field="type",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::type:enum",
        scaffold={},
        mutate=set_at_path("type", "__INVALID__"),
        expected_field="type",
        expected_check="enum",
    ),
    Scenario(
        id="division_boundary::version:required",
        scaffold={},
        mutate=set_at_path("version", None),
        expected_field="version",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::version:bounds",
        scaffold={},
        mutate=set_at_path("version", -1),
        expected_field="version",
        expected_check="bounds",
    ),
    Scenario(
        id="division_boundary::sources_min_length:array_min_length",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources", []),
        expected_field="sources_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="division_boundary::sources_unique:struct_unique",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=lambda row: mutate_unique_items(row, "sources"),
        expected_field="sources_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="division_boundary::sources[].property:required",
        scaffold={"sources": [{"dataset": "", "property": "/valid/pointer"}]},
        mutate=set_at_path("sources[].property", None),
        expected_field="sources[].property",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::sources[].property:json_pointer",
        scaffold={"sources": [{"dataset": "", "property": "/valid/pointer"}]},
        mutate=set_at_path("sources[].property", "no-slash"),
        expected_field="sources[].property",
        expected_check="json_pointer",
    ),
    Scenario(
        id="division_boundary::sources[].dataset:required",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].dataset", None),
        expected_field="sources[].dataset",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::sources[].license:stripped",
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
        id="division_boundary::sources[].confidence_0:bounds",
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
        id="division_boundary::sources[].confidence_1:bounds",
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
        id="division_boundary::sources[].between:linear_range_length",
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
        id="division_boundary::sources[].between:linear_range_bounds",
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
        id="division_boundary::sources[].between:linear_range_order",
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
        id="division_boundary::subtype:required",
        scaffold={},
        mutate=set_at_path("subtype", None),
        expected_field="subtype",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::subtype:enum",
        scaffold={},
        mutate=set_at_path("subtype", "__INVALID__"),
        expected_field="subtype",
        expected_check="enum",
    ),
    Scenario(
        id="division_boundary::class:required",
        scaffold={},
        mutate=set_at_path("class", None),
        expected_field="class",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::class:enum",
        scaffold={},
        mutate=set_at_path("class", "__INVALID__"),
        expected_field="class",
        expected_check="enum",
    ),
    Scenario(
        id="division_boundary::division_ids:required",
        scaffold={},
        mutate=set_at_path("division_ids", None),
        expected_field="division_ids",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::division_ids_min_length:array_min_length",
        scaffold={},
        mutate=set_at_path("division_ids", []),
        expected_field="division_ids_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="division_boundary::division_ids_max_length:array_max_length",
        scaffold={},
        mutate=set_at_path("division_ids", [{}, {}, {}]),
        expected_field="division_ids_max_length",
        expected_check="array_max_length",
    ),
    Scenario(
        id="division_boundary::division_ids_unique:struct_unique",
        scaffold={},
        mutate=lambda row: mutate_unique_items(row, "division_ids"),
        expected_field="division_ids_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="division_boundary::division_ids[]:string_min_length",
        scaffold={},
        mutate=set_at_path("division_ids[]", ""),
        expected_field="division_ids[]",
        expected_check="string_min_length",
    ),
    Scenario(
        id="division_boundary::division_ids[]:no_whitespace",
        scaffold={},
        mutate=set_at_path("division_ids[]", "has whitespace"),
        expected_field="division_ids[]",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="division_boundary::country:country_code_alpha2",
        scaffold={"country": "US"},
        mutate=set_at_path("country", "99"),
        expected_field="country",
        expected_check="country_code_alpha2",
    ),
    Scenario(
        id="division_boundary::region:region_code",
        scaffold={"region": "US-CA"},
        mutate=set_at_path("region", "99-999"),
        expected_field="region",
        expected_check="region_code",
    ),
    Scenario(
        id="division_boundary::admin_level_0:bounds",
        scaffold={"admin_level": 0},
        mutate=set_at_path("admin_level", -1),
        expected_field="admin_level_0",
        expected_check="bounds",
    ),
    Scenario(
        id="division_boundary::admin_level_1:bounds",
        scaffold={"admin_level": 0},
        mutate=set_at_path("admin_level", 17),
        expected_field="admin_level_1",
        expected_check="bounds",
    ),
    Scenario(
        id="division_boundary::perspectives.mode:required",
        scaffold={"perspectives": {"countries": ["US"], "mode": "accepted_by"}},
        mutate=set_at_path("perspectives.mode", None),
        expected_field="perspectives.mode",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::perspectives.mode:enum",
        scaffold={"perspectives": {"countries": ["US"], "mode": "accepted_by"}},
        mutate=set_at_path("perspectives.mode", "__INVALID__"),
        expected_field="perspectives.mode",
        expected_check="enum",
    ),
    Scenario(
        id="division_boundary::perspectives.countries:required",
        scaffold={"perspectives": {"mode": "accepted_by", "countries": ["US"]}},
        mutate=set_at_path("perspectives.countries", None),
        expected_field="perspectives.countries",
        expected_check="required",
    ),
    Scenario(
        id="division_boundary::perspectives.countries_min_length:array_min_length",
        scaffold={"perspectives": {"mode": "accepted_by", "countries": ["US"]}},
        mutate=set_at_path("perspectives.countries", []),
        expected_field="perspectives.countries_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="division_boundary::perspectives.countries_unique:struct_unique",
        scaffold={"perspectives": {"mode": "accepted_by", "countries": ["US"]}},
        mutate=lambda row: mutate_unique_items(row, "perspectives.countries"),
        expected_field="perspectives.countries_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="division_boundary::perspectives.countries[]:country_code_alpha2",
        scaffold={"perspectives": {"mode": "accepted_by", "countries": ["US"]}},
        mutate=set_at_path("perspectives.countries[]", "99"),
        expected_field="perspectives.countries[]",
        expected_check="country_code_alpha2",
    ),
    Scenario(
        id="division_boundary::model:radio_group:0",
        scaffold={},
        mutate=lambda row: mutate_radio_group(row, ["is_land", "is_territorial"]),
        expected_field="radio_group",
        expected_check="radio_group",
    ),
    Scenario(
        id="division_boundary::model:require_if:1",
        scaffold={},
        mutate=lambda row: mutate_require_if(row, ["admin_level"], "subtype", "county"),
        expected_field="admin_level_required_0",
        expected_check="require_if",
    ),
    Scenario(
        id="division_boundary::model:require_if:2",
        scaffold={},
        mutate=lambda row: mutate_require_if(
            row, ["admin_level"], "subtype", "macrocounty"
        ),
        expected_field="admin_level_required_1",
        expected_check="require_if",
    ),
    Scenario(
        id="division_boundary::model:require_if:3",
        scaffold={},
        mutate=lambda row: mutate_require_if(row, ["admin_level"], "subtype", "region"),
        expected_field="admin_level_required_2",
        expected_check="require_if",
    ),
    Scenario(
        id="division_boundary::model:require_if:4",
        scaffold={},
        mutate=lambda row: mutate_require_if(
            row, ["admin_level"], "subtype", "macroregion"
        ),
        expected_field="admin_level_required_3",
        expected_check="require_if",
    ),
    Scenario(
        id="division_boundary::model:require_if:5",
        scaffold={},
        mutate=lambda row: mutate_require_if(
            row, ["admin_level"], "subtype", "dependency"
        ),
        expected_field="admin_level_required_4",
        expected_check="require_if",
    ),
    Scenario(
        id="division_boundary::model:require_if:6",
        scaffold={},
        mutate=lambda row: mutate_require_if(
            row, ["admin_level"], "subtype", "country"
        ),
        expected_field="admin_level_required_5",
        expected_check="require_if",
    ),
    Scenario(
        id="division_boundary::model:require_if:7",
        scaffold={},
        mutate=lambda row: mutate_require_if(
            row, ["country"], "subtype", "country", negate=True
        ),
        expected_field="country_required",
        expected_check="require_if",
    ),
    Scenario(
        id="division_boundary::model:forbid_if:8",
        scaffold={},
        mutate=lambda row: mutate_forbid_if(row, ["country"], "subtype", "country"),
        expected_field="country_forbidden",
        expected_check="forbid_if",
    ),
]


@pytest.fixture(scope="module")
def checks() -> list:
    return division_boundary_checks()


@pytest.fixture(scope="module")
def sparse_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        DIVISION_BOUNDARY_SCHEMA,
        checks,
        BASE_ROW_SPARSE,
        SCENARIOS,
        model_name="division_boundary",
    )


@pytest.fixture(scope="module")
def populated_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        DIVISION_BOUNDARY_SCHEMA,
        checks,
        BASE_ROW_POPULATED,
        SCENARIOS,
        model_name="division_boundary",
    )


def test_baseline_sparse(sparse_results: ValidationResults) -> None:
    """Sparse base row passes every check the codegen produced.

    Catches drift between base_row synthesis, schema_builder, and
    check_builder -- if any of those produce output inconsistent with
    the others (e.g. a check that rejects values the synthesizer emits
    for required-only fields), the baseline fails here before any
    scenario runs.
    """
    baseline = sparse_results.violations.get("division_boundary::baseline", set())
    assert baseline == set(), f"Sparse baseline has violations: {baseline}"


def test_baseline_populated(populated_results: ValidationResults) -> None:
    """Fully-populated base row passes every check the codegen produced.

    Mirrors `test_baseline_sparse` but with all optional fields
    filled, exercising codegen paths that only fire when a value is
    present.
    """
    baseline = populated_results.violations.get("division_boundary::baseline", set())
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
