# Auto-generated — do not edit.

"""Generated conformance tests for building."""

from __future__ import annotations

import pytest
from overture.schema.pyspark.expressions.generated.overture.schema.buildings.building import (
    BUILDING_SCHEMA,
    building_checks,
)
from pyspark.sql import SparkSession

from ....._support.harness import (
    ValidationResults,
    run_validation_pipeline,
)
from ....._support.helpers import set_at_path
from ....._support.mutations import (
    mutate_map_key,
    mutate_map_value,
    mutate_unique_items,
)
from ....._support.scenarios import Scenario

BASE_ROW_SPARSE: dict = {
    "id": "f59ea25f-5910-56e0-b595-25dd9d65ef4b",
    "geometry": "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 1, 0 0)))",
    "theme": "buildings",
    "type": "building",
    "version": 0,
}


BASE_ROW_POPULATED: dict = {
    "id": "f59ea25f-5910-56e0-b595-25dd9d65ef4b",
    "bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0},
    "geometry": "MULTIPOLYGON (((0 0, 1 0, 1 1, 0 1, 0 0)))",
    "theme": "buildings",
    "type": "building",
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
    "subtype": "agricultural",
    "class": "agricultural",
    "has_parts": False,
    "names": {
        "primary": "a",
        "common": {"en": "clean"},
        "rules": [
            {
                "value": "a",
                "variant": "common",
                "language": "en",
                "perspectives": {"mode": "accepted_by", "countries": ["US"]},
                "between": [0.0, 1.0],
                "side": "left",
            }
        ],
    },
    "level": 0,
    "height": 1.0,
    "is_underground": False,
    "num_floors": 1,
    "num_floors_underground": 1,
    "min_height": 0.0,
    "min_floor": 1,
    "facade_color": "#aabbcc",
    "facade_material": "brick",
    "roof_material": "concrete",
    "roof_shape": "dome",
    "roof_direction": 0.0,
    "roof_orientation": "across",
    "roof_color": "#aabbcc",
    "roof_height": 0.0,
}


SCENARIOS: list[Scenario] = [
    Scenario(
        id="building::id:required",
        scaffold={},
        mutate=set_at_path("id", None),
        expected_field="id",
        expected_check="required",
    ),
    Scenario(
        id="building::id:string_min_length",
        scaffold={},
        mutate=set_at_path("id", ""),
        expected_field="id",
        expected_check="string_min_length",
    ),
    Scenario(
        id="building::id:no_whitespace",
        scaffold={},
        mutate=set_at_path("id", "has whitespace"),
        expected_field="id",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="building::bbox:bbox_completeness",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": None, "ymax": 1.0}
        ),
        expected_field="bbox",
        expected_check="bbox_completeness",
    ),
    Scenario(
        id="building::bbox:bbox_lat_ordering",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": 10.0, "ymax": -10.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_ordering",
    ),
    Scenario(
        id="building::bbox:bbox_lat_range",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": -100.0, "ymax": 100.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_range",
    ),
    Scenario(
        id="building::geometry:required",
        scaffold={},
        mutate=set_at_path("geometry", None),
        expected_field="geometry",
        expected_check="required",
    ),
    Scenario(
        id="building::geometry:geometry_type",
        scaffold={},
        mutate=set_at_path("geometry", "POINT (0 0)"),
        expected_field="geometry",
        expected_check="geometry_type",
    ),
    Scenario(
        id="building::theme:required",
        scaffold={},
        mutate=set_at_path("theme", None),
        expected_field="theme",
        expected_check="required",
    ),
    Scenario(
        id="building::theme:enum",
        scaffold={},
        mutate=set_at_path("theme", "__INVALID__"),
        expected_field="theme",
        expected_check="enum",
    ),
    Scenario(
        id="building::type:required",
        scaffold={},
        mutate=set_at_path("type", None),
        expected_field="type",
        expected_check="required",
    ),
    Scenario(
        id="building::type:enum",
        scaffold={},
        mutate=set_at_path("type", "__INVALID__"),
        expected_field="type",
        expected_check="enum",
    ),
    Scenario(
        id="building::version:required",
        scaffold={},
        mutate=set_at_path("version", None),
        expected_field="version",
        expected_check="required",
    ),
    Scenario(
        id="building::version:bounds",
        scaffold={},
        mutate=set_at_path("version", -1),
        expected_field="version",
        expected_check="bounds",
    ),
    Scenario(
        id="building::sources_min_length:array_min_length",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources", []),
        expected_field="sources_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="building::sources_unique:struct_unique",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=lambda row: mutate_unique_items(row, "sources"),
        expected_field="sources_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="building::sources[].property:required",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].property", None),
        expected_field="sources[].property",
        expected_check="required",
    ),
    Scenario(
        id="building::sources[].property:json_pointer",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].property", "no-slash"),
        expected_field="sources[].property",
        expected_check="json_pointer",
    ),
    Scenario(
        id="building::sources[].dataset:required",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].dataset", None),
        expected_field="sources[].dataset",
        expected_check="required",
    ),
    Scenario(
        id="building::sources[].license:stripped",
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
        id="building::sources[].confidence_0:bounds",
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
        id="building::sources[].confidence_1:bounds",
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
        id="building::sources[].between:linear_range_length",
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
        id="building::sources[].between:linear_range_bounds",
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
        id="building::sources[].between:linear_range_order",
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
        id="building::subtype:enum",
        scaffold={"subtype": "agricultural"},
        mutate=set_at_path("subtype", "__INVALID__"),
        expected_field="subtype",
        expected_check="enum",
    ),
    Scenario(
        id="building::class:enum",
        scaffold={"class": "agricultural"},
        mutate=set_at_path("class", "__INVALID__"),
        expected_field="class",
        expected_check="enum",
    ),
    Scenario(
        id="building::names.primary:required",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", None),
        expected_field="names.primary",
        expected_check="required",
    ),
    Scenario(
        id="building::names.primary:string_min_length",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", ""),
        expected_field="names.primary",
        expected_check="string_min_length",
    ),
    Scenario(
        id="building::names.primary:stripped",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", " has spaces "),
        expected_field="names.primary",
        expected_check="stripped",
    ),
    Scenario(
        id="building::names.common{key}:language_tag",
        scaffold={"names": {"primary": "a", "common": {"en": "clean"}}},
        mutate=lambda row: mutate_map_key(row, "names.common", "123"),
        expected_field="names.common{key}",
        expected_check="language_tag",
    ),
    Scenario(
        id="building::names.common{value}:stripped",
        scaffold={"names": {"primary": "a", "common": {"en": "clean"}}},
        mutate=lambda row: mutate_map_value(row, "names.common", " has spaces "),
        expected_field="names.common{value}",
        expected_check="stripped",
    ),
    Scenario(
        id="building::names.rules[].value:required",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].value", None),
        expected_field="names.rules[].value",
        expected_check="required",
    ),
    Scenario(
        id="building::names.rules[].value:string_min_length",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].value", ""),
        expected_field="names.rules[].value",
        expected_check="string_min_length",
    ),
    Scenario(
        id="building::names.rules[].value:stripped",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].value", " has spaces "),
        expected_field="names.rules[].value",
        expected_check="stripped",
    ),
    Scenario(
        id="building::names.rules[].variant:required",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].variant", None),
        expected_field="names.rules[].variant",
        expected_check="required",
    ),
    Scenario(
        id="building::names.rules[].variant:enum",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].variant", "__INVALID__"),
        expected_field="names.rules[].variant",
        expected_check="enum",
    ),
    Scenario(
        id="building::names.rules[].language:language_tag",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [{"value": "a", "variant": "common", "language": "en"}],
            }
        },
        mutate=set_at_path("names.rules[].language", "123"),
        expected_field="names.rules[].language",
        expected_check="language_tag",
    ),
    Scenario(
        id="building::names.rules[].perspectives.mode:required",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [
                    {
                        "value": "a",
                        "variant": "common",
                        "perspectives": {"mode": "accepted_by", "countries": ["US"]},
                    }
                ],
            }
        },
        mutate=set_at_path("names.rules[].perspectives.mode", None),
        expected_field="names.rules[].perspectives.mode",
        expected_check="required",
    ),
    Scenario(
        id="building::names.rules[].perspectives.mode:enum",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [
                    {
                        "value": "a",
                        "variant": "common",
                        "perspectives": {"mode": "accepted_by", "countries": ["US"]},
                    }
                ],
            }
        },
        mutate=set_at_path("names.rules[].perspectives.mode", "__INVALID__"),
        expected_field="names.rules[].perspectives.mode",
        expected_check="enum",
    ),
    Scenario(
        id="building::names.rules[].perspectives.countries:required",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [
                    {
                        "value": "a",
                        "variant": "common",
                        "perspectives": {"mode": "accepted_by", "countries": ["US"]},
                    }
                ],
            }
        },
        mutate=set_at_path("names.rules[].perspectives.countries", None),
        expected_field="names.rules[].perspectives.countries",
        expected_check="required",
    ),
    Scenario(
        id="building::names.rules[].perspectives.countries_min_length:array_min_length",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [
                    {
                        "value": "a",
                        "variant": "common",
                        "perspectives": {"mode": "accepted_by", "countries": ["US"]},
                    }
                ],
            }
        },
        mutate=set_at_path("names.rules[].perspectives.countries", []),
        expected_field="names.rules[].perspectives.countries_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="building::names.rules[].perspectives.countries_unique:struct_unique",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [
                    {
                        "value": "a",
                        "variant": "common",
                        "perspectives": {"mode": "accepted_by", "countries": ["US"]},
                    }
                ],
            }
        },
        mutate=lambda row: mutate_unique_items(
            row, "names.rules[].perspectives.countries"
        ),
        expected_field="names.rules[].perspectives.countries_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="building::names.rules[].perspectives.countries[]:country_code_alpha2",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [
                    {
                        "value": "a",
                        "variant": "common",
                        "perspectives": {"mode": "accepted_by", "countries": ["US"]},
                    }
                ],
            }
        },
        mutate=set_at_path("names.rules[].perspectives.countries[]", "99"),
        expected_field="names.rules[].perspectives.countries[]",
        expected_check="country_code_alpha2",
    ),
    Scenario(
        id="building::names.rules[].between:linear_range_length",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [{"value": "a", "variant": "common", "between": [0.0, 1.0]}],
            }
        },
        mutate=set_at_path("names.rules[].between", [0.5]),
        expected_field="names.rules[].between",
        expected_check="linear_range_length",
    ),
    Scenario(
        id="building::names.rules[].between:linear_range_bounds",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [{"value": "a", "variant": "common", "between": [0.0, 1.0]}],
            }
        },
        mutate=set_at_path("names.rules[].between", [1.5, 2.0]),
        expected_field="names.rules[].between",
        expected_check="linear_range_bounds",
    ),
    Scenario(
        id="building::names.rules[].between:linear_range_order",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [{"value": "a", "variant": "common", "between": [0.0, 1.0]}],
            }
        },
        mutate=set_at_path("names.rules[].between", [0.8, 0.2]),
        expected_field="names.rules[].between",
        expected_check="linear_range_order",
    ),
    Scenario(
        id="building::names.rules[].side:enum",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [{"value": "a", "variant": "common", "side": "left"}],
            }
        },
        mutate=set_at_path("names.rules[].side", "__INVALID__"),
        expected_field="names.rules[].side",
        expected_check="enum",
    ),
    Scenario(
        id="building::height:bounds",
        scaffold={"height": 1.0},
        mutate=set_at_path("height", 0.0),
        expected_field="height",
        expected_check="bounds",
    ),
    Scenario(
        id="building::num_floors:bounds",
        scaffold={"num_floors": 1},
        mutate=set_at_path("num_floors", 0),
        expected_field="num_floors",
        expected_check="bounds",
    ),
    Scenario(
        id="building::num_floors_underground:bounds",
        scaffold={"num_floors_underground": 1},
        mutate=set_at_path("num_floors_underground", 0),
        expected_field="num_floors_underground",
        expected_check="bounds",
    ),
    Scenario(
        id="building::min_floor:bounds",
        scaffold={"min_floor": 1},
        mutate=set_at_path("min_floor", 0),
        expected_field="min_floor",
        expected_check="bounds",
    ),
    Scenario(
        id="building::facade_color:hex_color",
        scaffold={"facade_color": "#aabbcc"},
        mutate=set_at_path("facade_color", "not-hex"),
        expected_field="facade_color",
        expected_check="hex_color",
    ),
    Scenario(
        id="building::facade_material:enum",
        scaffold={"facade_material": "brick"},
        mutate=set_at_path("facade_material", "__INVALID__"),
        expected_field="facade_material",
        expected_check="enum",
    ),
    Scenario(
        id="building::roof_material:enum",
        scaffold={"roof_material": "concrete"},
        mutate=set_at_path("roof_material", "__INVALID__"),
        expected_field="roof_material",
        expected_check="enum",
    ),
    Scenario(
        id="building::roof_shape:enum",
        scaffold={"roof_shape": "dome"},
        mutate=set_at_path("roof_shape", "__INVALID__"),
        expected_field="roof_shape",
        expected_check="enum",
    ),
    Scenario(
        id="building::roof_direction_0:bounds",
        scaffold={"roof_direction": 0.0},
        mutate=set_at_path("roof_direction", -1.0),
        expected_field="roof_direction_0",
        expected_check="bounds",
    ),
    Scenario(
        id="building::roof_direction_1:bounds",
        scaffold={"roof_direction": 0.0},
        mutate=set_at_path("roof_direction", 360.0),
        expected_field="roof_direction_1",
        expected_check="bounds",
    ),
    Scenario(
        id="building::roof_orientation:enum",
        scaffold={"roof_orientation": "across"},
        mutate=set_at_path("roof_orientation", "__INVALID__"),
        expected_field="roof_orientation",
        expected_check="enum",
    ),
    Scenario(
        id="building::roof_color:hex_color",
        scaffold={"roof_color": "#aabbcc"},
        mutate=set_at_path("roof_color", "not-hex"),
        expected_field="roof_color",
        expected_check="hex_color",
    ),
]


@pytest.fixture(scope="module")
def checks() -> list:
    return building_checks()


@pytest.fixture(scope="module")
def sparse_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        BUILDING_SCHEMA,
        checks,
        BASE_ROW_SPARSE,
        SCENARIOS,
        model_name="building",
    )


@pytest.fixture(scope="module")
def populated_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        BUILDING_SCHEMA,
        checks,
        BASE_ROW_POPULATED,
        SCENARIOS,
        model_name="building",
    )


def test_baseline_sparse(sparse_results: ValidationResults) -> None:
    """Sparse base row passes every check the codegen produced.

    Catches drift between base_row synthesis, schema_builder, and
    check_builder -- if any of those produce output inconsistent with
    the others (e.g. a check that rejects values the synthesizer emits
    for required-only fields), the baseline fails here before any
    scenario runs.
    """
    baseline = sparse_results.violations.get("building::baseline", set())
    assert baseline == set(), f"Sparse baseline has violations: {baseline}"


def test_baseline_populated(populated_results: ValidationResults) -> None:
    """Fully-populated base row passes every check the codegen produced.

    Mirrors `test_baseline_sparse` but with all optional fields
    filled, exercising codegen paths that only fire when a value is
    present.
    """
    baseline = populated_results.violations.get("building::baseline", set())
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
