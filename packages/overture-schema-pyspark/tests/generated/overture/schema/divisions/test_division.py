# Auto-generated — do not edit.

"""Generated conformance tests for division."""

from __future__ import annotations

import pytest
from overture.schema.pyspark.expressions.generated.overture.schema.divisions.division import (
    DIVISION_SCHEMA,
    division_checks,
)
from pyspark.sql import SparkSession

from ....._support.harness import (
    ValidationResults,
    run_validation_pipeline,
)
from ....._support.helpers import set_at_path
from ....._support.mutations import (
    mutate_forbid_if,
    mutate_map_key,
    mutate_map_value,
    mutate_require_if,
    mutate_unique_items,
)
from ....._support.scenarios import Scenario

BASE_ROW_SPARSE: dict = {
    "names": {"primary": "a"},
    "id": "97a2a97d-1eb8-5161-9ae5-bfb82594ed67",
    "geometry": "POINT (0 0)",
    "theme": "divisions",
    "type": "division",
    "version": 0,
    "subtype": "country",
    "country": "US",
    "hierarchies": [[{"division_id": "a", "subtype": "country", "name": "a"}]],
    "admin_level": 0,
}


BASE_ROW_POPULATED: dict = {
    "cartography": {"prominence": 1, "min_zoom": 0, "max_zoom": 0, "sort_key": 0},
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
    "id": "97a2a97d-1eb8-5161-9ae5-bfb82594ed67",
    "bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0},
    "geometry": "POINT (0 0)",
    "theme": "divisions",
    "type": "division",
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
    "country": "US",
    "hierarchies": [[{"division_id": "a", "subtype": "country", "name": "a"}]],
    "admin_level": 0,
    "class": "megacity",
    "local_type": {"en": "clean"},
    "region": "US-CA",
    "perspectives": {"mode": "accepted_by", "countries": ["US"]},
    "norms": {"driving_side": "left"},
    "population": 0,
    "capital_division_ids": ["a"],
    "capital_of_divisions": [{"division_id": "a", "subtype": "country"}],
    "wikidata": "Q42",
}


SCENARIOS: list[Scenario] = [
    Scenario(
        id="division::cartography.prominence_0:bounds",
        scaffold={"cartography": {"prominence": 1}},
        mutate=set_at_path("cartography.prominence", 0),
        expected_field="cartography.prominence_0",
        expected_check="bounds",
    ),
    Scenario(
        id="division::cartography.prominence_1:bounds",
        scaffold={"cartography": {"prominence": 1}},
        mutate=set_at_path("cartography.prominence", 101),
        expected_field="cartography.prominence_1",
        expected_check="bounds",
    ),
    Scenario(
        id="division::cartography.min_zoom_0:bounds",
        scaffold={"cartography": {"min_zoom": 0}},
        mutate=set_at_path("cartography.min_zoom", -1),
        expected_field="cartography.min_zoom_0",
        expected_check="bounds",
    ),
    Scenario(
        id="division::cartography.min_zoom_1:bounds",
        scaffold={"cartography": {"min_zoom": 0}},
        mutate=set_at_path("cartography.min_zoom", 24),
        expected_field="cartography.min_zoom_1",
        expected_check="bounds",
    ),
    Scenario(
        id="division::cartography.max_zoom_0:bounds",
        scaffold={"cartography": {"max_zoom": 0}},
        mutate=set_at_path("cartography.max_zoom", -1),
        expected_field="cartography.max_zoom_0",
        expected_check="bounds",
    ),
    Scenario(
        id="division::cartography.max_zoom_1:bounds",
        scaffold={"cartography": {"max_zoom": 0}},
        mutate=set_at_path("cartography.max_zoom", 24),
        expected_field="cartography.max_zoom_1",
        expected_check="bounds",
    ),
    Scenario(
        id="division::names:required",
        scaffold={},
        mutate=set_at_path("names", None),
        expected_field="names",
        expected_check="required",
    ),
    Scenario(
        id="division::names.primary:required",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", None),
        expected_field="names.primary",
        expected_check="required",
    ),
    Scenario(
        id="division::names.primary:string_min_length",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", ""),
        expected_field="names.primary",
        expected_check="string_min_length",
    ),
    Scenario(
        id="division::names.primary:stripped",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", " has spaces "),
        expected_field="names.primary",
        expected_check="stripped",
    ),
    Scenario(
        id="division::names.common{key}:language_tag",
        scaffold={"names": {"primary": "a", "common": {"en": "clean"}}},
        mutate=lambda row: mutate_map_key(row, "names.common", "123"),
        expected_field="names.common{key}",
        expected_check="language_tag",
    ),
    Scenario(
        id="division::names.common{value}:stripped",
        scaffold={"names": {"primary": "a", "common": {"en": "clean"}}},
        mutate=lambda row: mutate_map_value(row, "names.common", " has spaces "),
        expected_field="names.common{value}",
        expected_check="stripped",
    ),
    Scenario(
        id="division::names.rules[].value:required",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].value", None),
        expected_field="names.rules[].value",
        expected_check="required",
    ),
    Scenario(
        id="division::names.rules[].value:string_min_length",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].value", ""),
        expected_field="names.rules[].value",
        expected_check="string_min_length",
    ),
    Scenario(
        id="division::names.rules[].value:stripped",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].value", " has spaces "),
        expected_field="names.rules[].value",
        expected_check="stripped",
    ),
    Scenario(
        id="division::names.rules[].variant:required",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].variant", None),
        expected_field="names.rules[].variant",
        expected_check="required",
    ),
    Scenario(
        id="division::names.rules[].variant:enum",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].variant", "__INVALID__"),
        expected_field="names.rules[].variant",
        expected_check="enum",
    ),
    Scenario(
        id="division::names.rules[].language:language_tag",
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
        id="division::names.rules[].perspectives.mode:required",
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
        id="division::names.rules[].perspectives.mode:enum",
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
        id="division::names.rules[].perspectives.countries:required",
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
        id="division::names.rules[].perspectives.countries_min_length:array_min_length",
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
        id="division::names.rules[].perspectives.countries_unique:struct_unique",
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
        id="division::names.rules[].perspectives.countries[]:country_code_alpha2",
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
        id="division::names.rules[].between:linear_range_length",
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
        id="division::names.rules[].between:linear_range_bounds",
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
        id="division::names.rules[].between:linear_range_order",
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
        id="division::names.rules[].side:enum",
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
        id="division::id:required",
        scaffold={},
        mutate=set_at_path("id", None),
        expected_field="id",
        expected_check="required",
    ),
    Scenario(
        id="division::id:string_min_length",
        scaffold={},
        mutate=set_at_path("id", ""),
        expected_field="id",
        expected_check="string_min_length",
    ),
    Scenario(
        id="division::id:no_whitespace",
        scaffold={},
        mutate=set_at_path("id", "has whitespace"),
        expected_field="id",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="division::bbox:bbox_completeness",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": None, "ymax": 1.0}
        ),
        expected_field="bbox",
        expected_check="bbox_completeness",
    ),
    Scenario(
        id="division::bbox:bbox_lat_ordering",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": 10.0, "ymax": -10.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_ordering",
    ),
    Scenario(
        id="division::bbox:bbox_lat_range",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": -100.0, "ymax": 100.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_range",
    ),
    Scenario(
        id="division::geometry:required",
        scaffold={},
        mutate=set_at_path("geometry", None),
        expected_field="geometry",
        expected_check="required",
    ),
    Scenario(
        id="division::geometry:geometry_type",
        scaffold={},
        mutate=set_at_path("geometry", "LINESTRING (0 0, 1 1)"),
        expected_field="geometry",
        expected_check="geometry_type",
    ),
    Scenario(
        id="division::theme:required",
        scaffold={},
        mutate=set_at_path("theme", None),
        expected_field="theme",
        expected_check="required",
    ),
    Scenario(
        id="division::theme:enum",
        scaffold={},
        mutate=set_at_path("theme", "__INVALID__"),
        expected_field="theme",
        expected_check="enum",
    ),
    Scenario(
        id="division::type:required",
        scaffold={},
        mutate=set_at_path("type", None),
        expected_field="type",
        expected_check="required",
    ),
    Scenario(
        id="division::type:enum",
        scaffold={},
        mutate=set_at_path("type", "__INVALID__"),
        expected_field="type",
        expected_check="enum",
    ),
    Scenario(
        id="division::version:required",
        scaffold={},
        mutate=set_at_path("version", None),
        expected_field="version",
        expected_check="required",
    ),
    Scenario(
        id="division::version:bounds",
        scaffold={},
        mutate=set_at_path("version", -1),
        expected_field="version",
        expected_check="bounds",
    ),
    Scenario(
        id="division::sources_min_length:array_min_length",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources", []),
        expected_field="sources_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="division::sources_unique:struct_unique",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=lambda row: mutate_unique_items(row, "sources"),
        expected_field="sources_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="division::sources[].property:required",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].property", None),
        expected_field="sources[].property",
        expected_check="required",
    ),
    Scenario(
        id="division::sources[].property:json_pointer",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].property", "no-slash"),
        expected_field="sources[].property",
        expected_check="json_pointer",
    ),
    Scenario(
        id="division::sources[].dataset:required",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].dataset", None),
        expected_field="sources[].dataset",
        expected_check="required",
    ),
    Scenario(
        id="division::sources[].license:stripped",
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
        id="division::sources[].confidence_0:bounds",
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
        id="division::sources[].confidence_1:bounds",
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
        id="division::sources[].between:linear_range_length",
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
        id="division::sources[].between:linear_range_bounds",
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
        id="division::sources[].between:linear_range_order",
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
        id="division::subtype:required",
        scaffold={},
        mutate=set_at_path("subtype", None),
        expected_field="subtype",
        expected_check="required",
    ),
    Scenario(
        id="division::subtype:enum",
        scaffold={},
        mutate=set_at_path("subtype", "__INVALID__"),
        expected_field="subtype",
        expected_check="enum",
    ),
    Scenario(
        id="division::country:required",
        scaffold={},
        mutate=set_at_path("country", None),
        expected_field="country",
        expected_check="required",
    ),
    Scenario(
        id="division::country:country_code_alpha2",
        scaffold={},
        mutate=set_at_path("country", "99"),
        expected_field="country",
        expected_check="country_code_alpha2",
    ),
    Scenario(
        id="division::hierarchies:required",
        scaffold={},
        mutate=set_at_path("hierarchies", None),
        expected_field="hierarchies",
        expected_check="required",
    ),
    Scenario(
        id="division::hierarchies_min_length:array_min_length",
        scaffold={},
        mutate=set_at_path("hierarchies", []),
        expected_field="hierarchies_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="division::hierarchies_unique:struct_unique",
        scaffold={},
        mutate=lambda row: mutate_unique_items(row, "hierarchies"),
        expected_field="hierarchies_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="division::hierarchies[]_min_length:array_min_length",
        scaffold={},
        mutate=set_at_path("hierarchies[]", []),
        expected_field="hierarchies[]_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="division::hierarchies[]_unique:struct_unique",
        scaffold={},
        mutate=lambda row: mutate_unique_items(row, "hierarchies[]"),
        expected_field="hierarchies[]_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="division::hierarchies[][].division_id:required",
        scaffold={
            "hierarchies": [[{"division_id": "a", "subtype": "country", "name": "a"}]]
        },
        mutate=set_at_path("hierarchies[][].division_id", None),
        expected_field="hierarchies[][].division_id",
        expected_check="required",
    ),
    Scenario(
        id="division::hierarchies[][].division_id:string_min_length",
        scaffold={
            "hierarchies": [[{"division_id": "a", "subtype": "country", "name": "a"}]]
        },
        mutate=set_at_path("hierarchies[][].division_id", ""),
        expected_field="hierarchies[][].division_id",
        expected_check="string_min_length",
    ),
    Scenario(
        id="division::hierarchies[][].division_id:no_whitespace",
        scaffold={
            "hierarchies": [[{"division_id": "a", "subtype": "country", "name": "a"}]]
        },
        mutate=set_at_path("hierarchies[][].division_id", "has whitespace"),
        expected_field="hierarchies[][].division_id",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="division::hierarchies[][].subtype:required",
        scaffold={
            "hierarchies": [[{"division_id": "a", "subtype": "country", "name": "a"}]]
        },
        mutate=set_at_path("hierarchies[][].subtype", None),
        expected_field="hierarchies[][].subtype",
        expected_check="required",
    ),
    Scenario(
        id="division::hierarchies[][].subtype:enum",
        scaffold={
            "hierarchies": [[{"division_id": "a", "subtype": "country", "name": "a"}]]
        },
        mutate=set_at_path("hierarchies[][].subtype", "__INVALID__"),
        expected_field="hierarchies[][].subtype",
        expected_check="enum",
    ),
    Scenario(
        id="division::hierarchies[][].name:required",
        scaffold={
            "hierarchies": [[{"division_id": "a", "subtype": "country", "name": "a"}]]
        },
        mutate=set_at_path("hierarchies[][].name", None),
        expected_field="hierarchies[][].name",
        expected_check="required",
    ),
    Scenario(
        id="division::hierarchies[][].name:string_min_length",
        scaffold={
            "hierarchies": [[{"division_id": "a", "subtype": "country", "name": "a"}]]
        },
        mutate=set_at_path("hierarchies[][].name", ""),
        expected_field="hierarchies[][].name",
        expected_check="string_min_length",
    ),
    Scenario(
        id="division::hierarchies[][].name:stripped",
        scaffold={
            "hierarchies": [[{"division_id": "a", "subtype": "country", "name": "a"}]]
        },
        mutate=set_at_path("hierarchies[][].name", " has spaces "),
        expected_field="hierarchies[][].name",
        expected_check="stripped",
    ),
    Scenario(
        id="division::parent_division_id:string_min_length",
        scaffold={"subtype": "dependency", "parent_division_id": "a"},
        mutate=set_at_path("parent_division_id", ""),
        expected_field="parent_division_id",
        expected_check="string_min_length",
    ),
    Scenario(
        id="division::parent_division_id:no_whitespace",
        scaffold={"subtype": "dependency", "parent_division_id": "a"},
        mutate=set_at_path("parent_division_id", "has whitespace"),
        expected_field="parent_division_id",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="division::admin_level_0:bounds",
        scaffold={"admin_level": 0},
        mutate=set_at_path("admin_level", -1),
        expected_field="admin_level_0",
        expected_check="bounds",
    ),
    Scenario(
        id="division::admin_level_1:bounds",
        scaffold={"admin_level": 0},
        mutate=set_at_path("admin_level", 17),
        expected_field="admin_level_1",
        expected_check="bounds",
    ),
    Scenario(
        id="division::class:enum",
        scaffold={"class": "megacity"},
        mutate=set_at_path("class", "__INVALID__"),
        expected_field="class",
        expected_check="enum",
    ),
    Scenario(
        id="division::local_type{key}:language_tag",
        scaffold={"local_type": {"en": "clean"}},
        mutate=lambda row: mutate_map_key(row, "local_type", "123"),
        expected_field="local_type{key}",
        expected_check="language_tag",
    ),
    Scenario(
        id="division::local_type{value}:stripped",
        scaffold={"local_type": {"en": "clean"}},
        mutate=lambda row: mutate_map_value(row, "local_type", " has spaces "),
        expected_field="local_type{value}",
        expected_check="stripped",
    ),
    Scenario(
        id="division::region:region_code",
        scaffold={"region": "US-CA"},
        mutate=set_at_path("region", "99-999"),
        expected_field="region",
        expected_check="region_code",
    ),
    Scenario(
        id="division::perspectives.mode:required",
        scaffold={"perspectives": {"mode": "accepted_by", "countries": ["US"]}},
        mutate=set_at_path("perspectives.mode", None),
        expected_field="perspectives.mode",
        expected_check="required",
    ),
    Scenario(
        id="division::perspectives.mode:enum",
        scaffold={"perspectives": {"mode": "accepted_by", "countries": ["US"]}},
        mutate=set_at_path("perspectives.mode", "__INVALID__"),
        expected_field="perspectives.mode",
        expected_check="enum",
    ),
    Scenario(
        id="division::perspectives.countries:required",
        scaffold={"perspectives": {"mode": "accepted_by", "countries": ["US"]}},
        mutate=set_at_path("perspectives.countries", None),
        expected_field="perspectives.countries",
        expected_check="required",
    ),
    Scenario(
        id="division::perspectives.countries_min_length:array_min_length",
        scaffold={"perspectives": {"mode": "accepted_by", "countries": ["US"]}},
        mutate=set_at_path("perspectives.countries", []),
        expected_field="perspectives.countries_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="division::perspectives.countries_unique:struct_unique",
        scaffold={"perspectives": {"mode": "accepted_by", "countries": ["US"]}},
        mutate=lambda row: mutate_unique_items(row, "perspectives.countries"),
        expected_field="perspectives.countries_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="division::perspectives.countries[]:country_code_alpha2",
        scaffold={"perspectives": {"mode": "accepted_by", "countries": ["US"]}},
        mutate=set_at_path("perspectives.countries[]", "99"),
        expected_field="perspectives.countries[]",
        expected_check="country_code_alpha2",
    ),
    Scenario(
        id="division::norms.driving_side:enum",
        scaffold={"norms": {"driving_side": "left"}},
        mutate=set_at_path("norms.driving_side", "__INVALID__"),
        expected_field="norms.driving_side",
        expected_check="enum",
    ),
    Scenario(
        id="division::population:bounds",
        scaffold={"population": 0},
        mutate=set_at_path("population", -1),
        expected_field="population",
        expected_check="bounds",
    ),
    Scenario(
        id="division::capital_division_ids_min_length:array_min_length",
        scaffold={"capital_division_ids": ["a"]},
        mutate=set_at_path("capital_division_ids", []),
        expected_field="capital_division_ids_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="division::capital_division_ids_unique:struct_unique",
        scaffold={"capital_division_ids": ["a"]},
        mutate=lambda row: mutate_unique_items(row, "capital_division_ids"),
        expected_field="capital_division_ids_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="division::capital_division_ids[]:string_min_length",
        scaffold={"capital_division_ids": ["a"]},
        mutate=set_at_path("capital_division_ids[]", ""),
        expected_field="capital_division_ids[]",
        expected_check="string_min_length",
    ),
    Scenario(
        id="division::capital_division_ids[]:no_whitespace",
        scaffold={"capital_division_ids": ["a"]},
        mutate=set_at_path("capital_division_ids[]", "has whitespace"),
        expected_field="capital_division_ids[]",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="division::capital_of_divisions_min_length:array_min_length",
        scaffold={"capital_of_divisions": [{"division_id": "a", "subtype": "country"}]},
        mutate=set_at_path("capital_of_divisions", []),
        expected_field="capital_of_divisions_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="division::capital_of_divisions_unique:struct_unique",
        scaffold={"capital_of_divisions": [{"division_id": "a", "subtype": "country"}]},
        mutate=lambda row: mutate_unique_items(row, "capital_of_divisions"),
        expected_field="capital_of_divisions_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="division::capital_of_divisions[].division_id:required",
        scaffold={"capital_of_divisions": [{"division_id": "a", "subtype": "country"}]},
        mutate=set_at_path("capital_of_divisions[].division_id", None),
        expected_field="capital_of_divisions[].division_id",
        expected_check="required",
    ),
    Scenario(
        id="division::capital_of_divisions[].division_id:string_min_length",
        scaffold={"capital_of_divisions": [{"division_id": "a", "subtype": "country"}]},
        mutate=set_at_path("capital_of_divisions[].division_id", ""),
        expected_field="capital_of_divisions[].division_id",
        expected_check="string_min_length",
    ),
    Scenario(
        id="division::capital_of_divisions[].division_id:no_whitespace",
        scaffold={"capital_of_divisions": [{"division_id": "a", "subtype": "country"}]},
        mutate=set_at_path("capital_of_divisions[].division_id", "has whitespace"),
        expected_field="capital_of_divisions[].division_id",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="division::capital_of_divisions[].subtype:required",
        scaffold={"capital_of_divisions": [{"division_id": "a", "subtype": "country"}]},
        mutate=set_at_path("capital_of_divisions[].subtype", None),
        expected_field="capital_of_divisions[].subtype",
        expected_check="required",
    ),
    Scenario(
        id="division::capital_of_divisions[].subtype:enum",
        scaffold={"capital_of_divisions": [{"division_id": "a", "subtype": "country"}]},
        mutate=set_at_path("capital_of_divisions[].subtype", "__INVALID__"),
        expected_field="capital_of_divisions[].subtype",
        expected_check="enum",
    ),
    Scenario(
        id="division::wikidata:wikidata_id",
        scaffold={"wikidata": "Q42"},
        mutate=set_at_path("wikidata", "P999"),
        expected_field="wikidata",
        expected_check="wikidata_id",
    ),
    Scenario(
        id="division::model:require_if:0",
        scaffold={},
        mutate=lambda row: mutate_require_if(row, ["admin_level"], "subtype", "county"),
        expected_field="admin_level_required_0",
        expected_check="require_if",
    ),
    Scenario(
        id="division::model:require_if:1",
        scaffold={},
        mutate=lambda row: mutate_require_if(
            row, ["admin_level"], "subtype", "macrocounty"
        ),
        expected_field="admin_level_required_1",
        expected_check="require_if",
    ),
    Scenario(
        id="division::model:require_if:2",
        scaffold={},
        mutate=lambda row: mutate_require_if(row, ["admin_level"], "subtype", "region"),
        expected_field="admin_level_required_2",
        expected_check="require_if",
    ),
    Scenario(
        id="division::model:require_if:3",
        scaffold={},
        mutate=lambda row: mutate_require_if(
            row, ["admin_level"], "subtype", "macroregion"
        ),
        expected_field="admin_level_required_3",
        expected_check="require_if",
    ),
    Scenario(
        id="division::model:require_if:4",
        scaffold={},
        mutate=lambda row: mutate_require_if(
            row, ["admin_level"], "subtype", "dependency"
        ),
        expected_field="admin_level_required_4",
        expected_check="require_if",
    ),
    Scenario(
        id="division::model:require_if:5",
        scaffold={},
        mutate=lambda row: mutate_require_if(
            row, ["admin_level"], "subtype", "country"
        ),
        expected_field="admin_level_required_5",
        expected_check="require_if",
    ),
    Scenario(
        id="division::model:require_if:6",
        scaffold={},
        mutate=lambda row: mutate_require_if(
            row, ["parent_division_id"], "subtype", "country", negate=True
        ),
        expected_field="parent_division_id_required",
        expected_check="require_if",
    ),
    Scenario(
        id="division::model:forbid_if:7",
        scaffold={},
        mutate=lambda row: mutate_forbid_if(
            row, ["parent_division_id"], "subtype", "country"
        ),
        expected_field="parent_division_id_forbidden",
        expected_check="forbid_if",
    ),
]


@pytest.fixture(scope="module")
def checks() -> list:
    return division_checks()


@pytest.fixture(scope="module")
def sparse_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        DIVISION_SCHEMA,
        checks,
        BASE_ROW_SPARSE,
        SCENARIOS,
        model_name="division",
    )


@pytest.fixture(scope="module")
def populated_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        DIVISION_SCHEMA,
        checks,
        BASE_ROW_POPULATED,
        SCENARIOS,
        model_name="division",
    )


def test_baseline_sparse(sparse_results: ValidationResults) -> None:
    """Sparse base row passes every check the codegen produced.

    Catches drift between base_row synthesis, schema_builder, and
    check_builder -- if any of those produce output inconsistent with
    the others (e.g. a check that rejects values the synthesizer emits
    for required-only fields), the baseline fails here before any
    scenario runs.
    """
    baseline = sparse_results.violations.get("division::baseline", set())
    assert baseline == set(), f"Sparse baseline has violations: {baseline}"


def test_baseline_populated(populated_results: ValidationResults) -> None:
    """Fully-populated base row passes every check the codegen produced.

    Mirrors `test_baseline_sparse` but with all optional fields
    filled, exercising codegen paths that only fire when a value is
    present.
    """
    baseline = populated_results.violations.get("division::baseline", set())
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
