# Auto-generated — do not edit.

"""Generated conformance tests for segment."""

from __future__ import annotations

import pytest
from overture.schema.pyspark.expressions.generated.overture.schema.transportation.segment import (
    SEGMENT_SCHEMA,
    segment_checks,
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
    mutate_require_any_of,
    mutate_require_if,
    mutate_unique_items,
)
from ....._support.scenarios import Scenario

BASE_ROW_SPARSE: dict = {
    "id": "1f4d65c9-e092-52c4-b002-7c11ce69a554",
    "geometry": "LINESTRING (0 0, 1 1)",
    "theme": "transportation",
    "type": "segment",
    "version": 0,
    "subtype": "water",
}


BASE_ROW_POPULATED: dict = {
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
    "id": "1f4d65c9-e092-52c4-b002-7c11ce69a554",
    "bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0},
    "geometry": "LINESTRING (0 0, 1 1)",
    "theme": "transportation",
    "type": "segment",
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
    "subtype": "water",
    "access_restrictions": [
        {
            "access_type": "allowed",
            "between": [0.0, 1.0],
            "when": {
                "heading": "forward",
                "during": "",
                "mode": ["vehicle"],
                "using": ["as_customer"],
                "recognized": ["as_permitted"],
                "vehicle": [
                    {
                        "dimension": "height",
                        "comparison": "greater_than",
                        "value": 0.0,
                        "unit": "in",
                    }
                ],
            },
        }
    ],
    "connectors": [{"connector_id": "a", "at": 0.0}, {"connector_id": "a1", "at": 0.0}],
    "level_rules": [{"value": 0, "between": [0.0, 1.0]}],
    "routes": [
        {
            "name": "a",
            "network": "a",
            "ref": "a",
            "symbol": "a",
            "wikidata": "Q42",
            "between": [0.0, 1.0],
        }
    ],
    "subclass_rules": [{"value": "link", "between": [0.0, 1.0]}],
}


SCENARIOS: list[Scenario] = [
    Scenario(
        id="segment::id:required",
        scaffold={},
        mutate=set_at_path("id", None),
        expected_field="id",
        expected_check="required",
    ),
    Scenario(
        id="segment::id:string_min_length",
        scaffold={},
        mutate=set_at_path("id", ""),
        expected_field="id",
        expected_check="string_min_length",
    ),
    Scenario(
        id="segment::id:no_whitespace",
        scaffold={},
        mutate=set_at_path("id", "has whitespace"),
        expected_field="id",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="segment::bbox:bbox_completeness",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": None, "ymax": 1.0}
        ),
        expected_field="bbox",
        expected_check="bbox_completeness",
    ),
    Scenario(
        id="segment::bbox:bbox_lat_ordering",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": 10.0, "ymax": -10.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_ordering",
    ),
    Scenario(
        id="segment::bbox:bbox_lat_range",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": -100.0, "ymax": 100.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_range",
    ),
    Scenario(
        id="segment::geometry:required",
        scaffold={},
        mutate=set_at_path("geometry", None),
        expected_field="geometry",
        expected_check="required",
    ),
    Scenario(
        id="segment::geometry:geometry_type",
        scaffold={},
        mutate=set_at_path("geometry", "POINT (0 0)"),
        expected_field="geometry",
        expected_check="geometry_type",
    ),
    Scenario(
        id="segment::theme:required",
        scaffold={},
        mutate=set_at_path("theme", None),
        expected_field="theme",
        expected_check="required",
    ),
    Scenario(
        id="segment::theme:enum",
        scaffold={},
        mutate=set_at_path("theme", "__INVALID__"),
        expected_field="theme",
        expected_check="enum",
    ),
    Scenario(
        id="segment::type:required",
        scaffold={},
        mutate=set_at_path("type", None),
        expected_field="type",
        expected_check="required",
    ),
    Scenario(
        id="segment::type:enum",
        scaffold={},
        mutate=set_at_path("type", "__INVALID__"),
        expected_field="type",
        expected_check="enum",
    ),
    Scenario(
        id="segment::version:required",
        scaffold={},
        mutate=set_at_path("version", None),
        expected_field="version",
        expected_check="required",
    ),
    Scenario(
        id="segment::version:bounds",
        scaffold={},
        mutate=set_at_path("version", -1),
        expected_field="version",
        expected_check="bounds",
    ),
    Scenario(
        id="segment::sources_min_length:array_min_length",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources", []),
        expected_field="sources_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="segment::sources_unique:struct_unique",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=lambda row: mutate_unique_items(row, "sources"),
        expected_field="sources_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="segment::sources[].property:required",
        scaffold={"sources": [{"dataset": "", "property": "/valid/pointer"}]},
        mutate=set_at_path("sources[].property", None),
        expected_field="sources[].property",
        expected_check="required",
    ),
    Scenario(
        id="segment::sources[].property:json_pointer",
        scaffold={"sources": [{"dataset": "", "property": "/valid/pointer"}]},
        mutate=set_at_path("sources[].property", "no-slash"),
        expected_field="sources[].property",
        expected_check="json_pointer",
    ),
    Scenario(
        id="segment::sources[].dataset:required",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].dataset", None),
        expected_field="sources[].dataset",
        expected_check="required",
    ),
    Scenario(
        id="segment::sources[].license:stripped",
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
        id="segment::sources[].confidence_0:bounds",
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
        id="segment::sources[].confidence_1:bounds",
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
        id="segment::sources[].between:linear_range_length",
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
        id="segment::sources[].between:linear_range_bounds",
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
        id="segment::sources[].between:linear_range_order",
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
        id="segment::subtype:required",
        scaffold={},
        mutate=set_at_path("subtype", None),
        expected_field="subtype",
        expected_check="required",
    ),
    Scenario(
        id="segment::subtype:enum",
        scaffold={},
        mutate=set_at_path("subtype", "__INVALID__"),
        expected_field="subtype",
        expected_check="enum",
    ),
    Scenario(
        id="segment::access_restrictions_min_length:array_min_length",
        scaffold={"access_restrictions": [{"access_type": "allowed"}]},
        mutate=set_at_path("access_restrictions", []),
        expected_field="access_restrictions_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="segment::access_restrictions_unique:struct_unique",
        scaffold={"access_restrictions": [{"access_type": "allowed"}]},
        mutate=lambda row: mutate_unique_items(row, "access_restrictions"),
        expected_field="access_restrictions_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="segment::access_restrictions[].access_type:required",
        scaffold={"access_restrictions": [{"access_type": "allowed"}]},
        mutate=set_at_path("access_restrictions[].access_type", None),
        expected_field="access_restrictions[].access_type",
        expected_check="required",
    ),
    Scenario(
        id="segment::access_restrictions[].access_type:enum",
        scaffold={"access_restrictions": [{"access_type": "allowed"}]},
        mutate=set_at_path("access_restrictions[].access_type", "__INVALID__"),
        expected_field="access_restrictions[].access_type",
        expected_check="enum",
    ),
    Scenario(
        id="segment::access_restrictions[].between:linear_range_length",
        scaffold={
            "access_restrictions": [{"access_type": "allowed", "between": [0.0, 1.0]}]
        },
        mutate=set_at_path("access_restrictions[].between", [0.5]),
        expected_field="access_restrictions[].between",
        expected_check="linear_range_length",
    ),
    Scenario(
        id="segment::access_restrictions[].between:linear_range_bounds",
        scaffold={
            "access_restrictions": [{"access_type": "allowed", "between": [0.0, 1.0]}]
        },
        mutate=set_at_path("access_restrictions[].between", [1.5, 2.0]),
        expected_field="access_restrictions[].between",
        expected_check="linear_range_bounds",
    ),
    Scenario(
        id="segment::access_restrictions[].between:linear_range_order",
        scaffold={
            "access_restrictions": [{"access_type": "allowed", "between": [0.0, 1.0]}]
        },
        mutate=set_at_path("access_restrictions[].between", [0.8, 0.2]),
        expected_field="access_restrictions[].between",
        expected_check="linear_range_order",
    ),
    Scenario(
        id="segment::access_restrictions[].when.heading:enum",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"heading": "forward"}}
            ]
        },
        mutate=set_at_path("access_restrictions[].when.heading", "__INVALID__"),
        expected_field="access_restrictions[].when.heading",
        expected_check="enum",
    ),
    Scenario(
        id="segment::access_restrictions[].when.mode_min_length:array_min_length",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"mode": ["vehicle"]}}
            ]
        },
        mutate=set_at_path("access_restrictions[].when.mode", []),
        expected_field="access_restrictions[].when.mode_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="segment::access_restrictions[].when.mode_unique:struct_unique",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"mode": ["vehicle"]}}
            ]
        },
        mutate=lambda row: mutate_unique_items(row, "access_restrictions[].when.mode"),
        expected_field="access_restrictions[].when.mode_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="segment::access_restrictions[].when.mode[]:enum",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"mode": ["vehicle"]}}
            ]
        },
        mutate=set_at_path("access_restrictions[].when.mode[]", "__INVALID__"),
        expected_field="access_restrictions[].when.mode[]",
        expected_check="enum",
    ),
    Scenario(
        id="segment::access_restrictions[].when.using_min_length:array_min_length",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"using": ["as_customer"]}}
            ]
        },
        mutate=set_at_path("access_restrictions[].when.using", []),
        expected_field="access_restrictions[].when.using_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="segment::access_restrictions[].when.using_unique:struct_unique",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"using": ["as_customer"]}}
            ]
        },
        mutate=lambda row: mutate_unique_items(row, "access_restrictions[].when.using"),
        expected_field="access_restrictions[].when.using_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="segment::access_restrictions[].when.using[]:enum",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"using": ["as_customer"]}}
            ]
        },
        mutate=set_at_path("access_restrictions[].when.using[]", "__INVALID__"),
        expected_field="access_restrictions[].when.using[]",
        expected_check="enum",
    ),
    Scenario(
        id="segment::access_restrictions[].when.recognized_min_length:array_min_length",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"recognized": ["as_permitted"]}}
            ]
        },
        mutate=set_at_path("access_restrictions[].when.recognized", []),
        expected_field="access_restrictions[].when.recognized_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="segment::access_restrictions[].when.recognized_unique:struct_unique",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"recognized": ["as_permitted"]}}
            ]
        },
        mutate=lambda row: mutate_unique_items(
            row, "access_restrictions[].when.recognized"
        ),
        expected_field="access_restrictions[].when.recognized_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="segment::access_restrictions[].when.recognized[]:enum",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"recognized": ["as_permitted"]}}
            ]
        },
        mutate=set_at_path("access_restrictions[].when.recognized[]", "__INVALID__"),
        expected_field="access_restrictions[].when.recognized[]",
        expected_check="enum",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle_min_length:array_min_length",
        scaffold={
            "access_restrictions": [
                {
                    "access_type": "allowed",
                    "when": {
                        "vehicle": [
                            {
                                "dimension": "height",
                                "comparison": "greater_than",
                                "value": 0.0,
                                "unit": "in",
                            }
                        ]
                    },
                }
            ]
        },
        mutate=set_at_path("access_restrictions[].when.vehicle", []),
        expected_field="access_restrictions[].when.vehicle_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle_unique:struct_unique",
        scaffold={
            "access_restrictions": [
                {
                    "access_type": "allowed",
                    "when": {
                        "vehicle": [
                            {
                                "dimension": "height",
                                "comparison": "greater_than",
                                "value": 0.0,
                                "unit": "in",
                            }
                        ]
                    },
                }
            ]
        },
        mutate=lambda row: mutate_unique_items(
            row, "access_restrictions[].when.vehicle"
        ),
        expected_field="access_restrictions[].when.vehicle_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle[].dimension:required",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"vehicle": [{}]}}
            ]
        },
        mutate=set_at_path("access_restrictions[].when.vehicle[].dimension", None),
        expected_field="access_restrictions[].when.vehicle[].dimension",
        expected_check="required",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle[].dimension:enum",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"vehicle": [{}]}}
            ]
        },
        mutate=set_at_path(
            "access_restrictions[].when.vehicle[].dimension", "__INVALID__"
        ),
        expected_field="access_restrictions[].when.vehicle[].dimension",
        expected_check="enum",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle[].comparison:required",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"vehicle": [{}]}}
            ]
        },
        mutate=set_at_path("access_restrictions[].when.vehicle[].comparison", None),
        expected_field="access_restrictions[].when.vehicle[].comparison",
        expected_check="required",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle[].comparison:enum",
        scaffold={
            "access_restrictions": [
                {"access_type": "allowed", "when": {"vehicle": [{}]}}
            ]
        },
        mutate=set_at_path(
            "access_restrictions[].when.vehicle[].comparison", "__INVALID__"
        ),
        expected_field="access_restrictions[].when.vehicle[].comparison",
        expected_check="enum",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle[].value_0:required",
        scaffold={
            "access_restrictions": [
                {
                    "access_type": "allowed",
                    "when": {"vehicle": [{"dimension": "axle_count"}]},
                }
            ]
        },
        mutate=set_at_path("access_restrictions[].when.vehicle[].value", None),
        expected_field="access_restrictions[].when.vehicle[].value_0",
        expected_check="required",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle[].value_1:required",
        scaffold={
            "access_restrictions": [
                {
                    "access_type": "allowed",
                    "when": {"vehicle": [{"dimension": "height"}]},
                }
            ]
        },
        mutate=set_at_path("access_restrictions[].when.vehicle[].value", None),
        expected_field="access_restrictions[].when.vehicle[].value_1",
        expected_check="required",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle[].value:bounds",
        scaffold={
            "access_restrictions": [
                {
                    "access_type": "allowed",
                    "when": {"vehicle": [{"dimension": "height"}]},
                }
            ]
        },
        mutate=set_at_path("access_restrictions[].when.vehicle[].value", -1.0),
        expected_field="access_restrictions[].when.vehicle[].value",
        expected_check="bounds",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle[].unit_0:required",
        scaffold={
            "access_restrictions": [
                {
                    "access_type": "allowed",
                    "when": {"vehicle": [{"dimension": "height"}]},
                }
            ]
        },
        mutate=set_at_path("access_restrictions[].when.vehicle[].unit", None),
        expected_field="access_restrictions[].when.vehicle[].unit_0",
        expected_check="required",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle[].unit_0:enum",
        scaffold={
            "access_restrictions": [
                {
                    "access_type": "allowed",
                    "when": {"vehicle": [{"dimension": "height"}]},
                }
            ]
        },
        mutate=set_at_path("access_restrictions[].when.vehicle[].unit", "__INVALID__"),
        expected_field="access_restrictions[].when.vehicle[].unit_0",
        expected_check="enum",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle[].unit_1:required",
        scaffold={
            "access_restrictions": [
                {
                    "access_type": "allowed",
                    "when": {"vehicle": [{"dimension": "weight"}]},
                }
            ]
        },
        mutate=set_at_path("access_restrictions[].when.vehicle[].unit", None),
        expected_field="access_restrictions[].when.vehicle[].unit_1",
        expected_check="required",
    ),
    Scenario(
        id="segment::access_restrictions[].when.vehicle[].unit_1:enum",
        scaffold={
            "access_restrictions": [
                {
                    "access_type": "allowed",
                    "when": {"vehicle": [{"dimension": "weight"}]},
                }
            ]
        },
        mutate=set_at_path("access_restrictions[].when.vehicle[].unit", "__INVALID__"),
        expected_field="access_restrictions[].when.vehicle[].unit_1",
        expected_check="enum",
    ),
    Scenario(
        id="segment::connectors_min_length:array_min_length",
        scaffold={"connectors": [{"connector_id": "a"}, {"connector_id": "a1"}]},
        mutate=set_at_path("connectors", []),
        expected_field="connectors_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="segment::connectors_unique:struct_unique",
        scaffold={"connectors": [{"connector_id": "a"}, {"connector_id": "a1"}]},
        mutate=lambda row: mutate_unique_items(row, "connectors"),
        expected_field="connectors_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="segment::connectors[].connector_id:required",
        scaffold={"connectors": [{"connector_id": "a"}]},
        mutate=set_at_path("connectors[].connector_id", None),
        expected_field="connectors[].connector_id",
        expected_check="required",
    ),
    Scenario(
        id="segment::connectors[].connector_id:string_min_length",
        scaffold={"connectors": [{"connector_id": "a"}]},
        mutate=set_at_path("connectors[].connector_id", ""),
        expected_field="connectors[].connector_id",
        expected_check="string_min_length",
    ),
    Scenario(
        id="segment::connectors[].connector_id:no_whitespace",
        scaffold={"connectors": [{"connector_id": "a"}]},
        mutate=set_at_path("connectors[].connector_id", "has whitespace"),
        expected_field="connectors[].connector_id",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="segment::connectors[].at_0:bounds",
        scaffold={"connectors": [{"connector_id": "a", "at": 0.0}]},
        mutate=set_at_path("connectors[].at", -1.0),
        expected_field="connectors[].at_0",
        expected_check="bounds",
    ),
    Scenario(
        id="segment::connectors[].at_1:bounds",
        scaffold={"connectors": [{"connector_id": "a", "at": 0.0}]},
        mutate=set_at_path("connectors[].at", 2.0),
        expected_field="connectors[].at_1",
        expected_check="bounds",
    ),
    Scenario(
        id="segment::level_rules[].value:required",
        scaffold={"level_rules": [{"value": 0}]},
        mutate=set_at_path("level_rules[].value", None),
        expected_field="level_rules[].value",
        expected_check="required",
    ),
    Scenario(
        id="segment::level_rules[].between:linear_range_length",
        scaffold={"level_rules": [{"value": 0, "between": [0.0, 1.0]}]},
        mutate=set_at_path("level_rules[].between", [0.5]),
        expected_field="level_rules[].between",
        expected_check="linear_range_length",
    ),
    Scenario(
        id="segment::level_rules[].between:linear_range_bounds",
        scaffold={"level_rules": [{"value": 0, "between": [0.0, 1.0]}]},
        mutate=set_at_path("level_rules[].between", [1.5, 2.0]),
        expected_field="level_rules[].between",
        expected_check="linear_range_bounds",
    ),
    Scenario(
        id="segment::level_rules[].between:linear_range_order",
        scaffold={"level_rules": [{"value": 0, "between": [0.0, 1.0]}]},
        mutate=set_at_path("level_rules[].between", [0.8, 0.2]),
        expected_field="level_rules[].between",
        expected_check="linear_range_order",
    ),
    Scenario(
        id="segment::routes[].name:string_min_length",
        scaffold={"routes": [{"name": "a"}]},
        mutate=set_at_path("routes[].name", ""),
        expected_field="routes[].name",
        expected_check="string_min_length",
    ),
    Scenario(
        id="segment::routes[].name:stripped",
        scaffold={"routes": [{"name": "a"}]},
        mutate=set_at_path("routes[].name", " has spaces "),
        expected_field="routes[].name",
        expected_check="stripped",
    ),
    Scenario(
        id="segment::routes[].network:string_min_length",
        scaffold={"routes": [{"network": "a"}]},
        mutate=set_at_path("routes[].network", ""),
        expected_field="routes[].network",
        expected_check="string_min_length",
    ),
    Scenario(
        id="segment::routes[].network:stripped",
        scaffold={"routes": [{"network": "a"}]},
        mutate=set_at_path("routes[].network", " has spaces "),
        expected_field="routes[].network",
        expected_check="stripped",
    ),
    Scenario(
        id="segment::routes[].ref:string_min_length",
        scaffold={"routes": [{"ref": "a"}]},
        mutate=set_at_path("routes[].ref", ""),
        expected_field="routes[].ref",
        expected_check="string_min_length",
    ),
    Scenario(
        id="segment::routes[].ref:stripped",
        scaffold={"routes": [{"ref": "a"}]},
        mutate=set_at_path("routes[].ref", " has spaces "),
        expected_field="routes[].ref",
        expected_check="stripped",
    ),
    Scenario(
        id="segment::routes[].symbol:string_min_length",
        scaffold={"routes": [{"symbol": "a"}]},
        mutate=set_at_path("routes[].symbol", ""),
        expected_field="routes[].symbol",
        expected_check="string_min_length",
    ),
    Scenario(
        id="segment::routes[].symbol:stripped",
        scaffold={"routes": [{"symbol": "a"}]},
        mutate=set_at_path("routes[].symbol", " has spaces "),
        expected_field="routes[].symbol",
        expected_check="stripped",
    ),
    Scenario(
        id="segment::routes[].wikidata:wikidata_id",
        scaffold={"routes": [{"wikidata": "Q42"}]},
        mutate=set_at_path("routes[].wikidata", "P999"),
        expected_field="routes[].wikidata",
        expected_check="wikidata_id",
    ),
    Scenario(
        id="segment::routes[].between:linear_range_length",
        scaffold={"routes": [{"between": [0.0, 1.0]}]},
        mutate=set_at_path("routes[].between", [0.5]),
        expected_field="routes[].between",
        expected_check="linear_range_length",
    ),
    Scenario(
        id="segment::routes[].between:linear_range_bounds",
        scaffold={"routes": [{"between": [0.0, 1.0]}]},
        mutate=set_at_path("routes[].between", [1.5, 2.0]),
        expected_field="routes[].between",
        expected_check="linear_range_bounds",
    ),
    Scenario(
        id="segment::routes[].between:linear_range_order",
        scaffold={"routes": [{"between": [0.0, 1.0]}]},
        mutate=set_at_path("routes[].between", [0.8, 0.2]),
        expected_field="routes[].between",
        expected_check="linear_range_order",
    ),
    Scenario(
        id="segment::subclass_rules[].value:required",
        scaffold={"subclass_rules": [{"value": "link"}]},
        mutate=set_at_path("subclass_rules[].value", None),
        expected_field="subclass_rules[].value",
        expected_check="required",
    ),
    Scenario(
        id="segment::subclass_rules[].value:enum",
        scaffold={"subclass_rules": [{"value": "link"}]},
        mutate=set_at_path("subclass_rules[].value", "__INVALID__"),
        expected_field="subclass_rules[].value",
        expected_check="enum",
    ),
    Scenario(
        id="segment::subclass_rules[].between:linear_range_length",
        scaffold={"subclass_rules": [{"value": "link", "between": [0.0, 1.0]}]},
        mutate=set_at_path("subclass_rules[].between", [0.5]),
        expected_field="subclass_rules[].between",
        expected_check="linear_range_length",
    ),
    Scenario(
        id="segment::subclass_rules[].between:linear_range_bounds",
        scaffold={"subclass_rules": [{"value": "link", "between": [0.0, 1.0]}]},
        mutate=set_at_path("subclass_rules[].between", [1.5, 2.0]),
        expected_field="subclass_rules[].between",
        expected_check="linear_range_bounds",
    ),
    Scenario(
        id="segment::subclass_rules[].between:linear_range_order",
        scaffold={"subclass_rules": [{"value": "link", "between": [0.0, 1.0]}]},
        mutate=set_at_path("subclass_rules[].between", [0.8, 0.2]),
        expected_field="subclass_rules[].between",
        expected_check="linear_range_order",
    ),
    Scenario(
        id="segment::names.primary:required",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", None),
        expected_field="names.primary",
        expected_check="required",
    ),
    Scenario(
        id="segment::names.primary:string_min_length",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", ""),
        expected_field="names.primary",
        expected_check="string_min_length",
    ),
    Scenario(
        id="segment::names.primary:stripped",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", " has spaces "),
        expected_field="names.primary",
        expected_check="stripped",
    ),
    Scenario(
        id="segment::names.common{key}:language_tag",
        scaffold={"names": {"primary": "a", "common": {"en": "clean"}}},
        mutate=lambda row: mutate_map_key(row, "names.common", "123"),
        expected_field="names.common{key}",
        expected_check="language_tag",
    ),
    Scenario(
        id="segment::names.common{value}:stripped",
        scaffold={"names": {"primary": "a", "common": {"en": "clean"}}},
        mutate=lambda row: mutate_map_value(row, "names.common", " has spaces "),
        expected_field="names.common{value}",
        expected_check="stripped",
    ),
    Scenario(
        id="segment::names.rules[].value:required",
        scaffold={
            "names": {"primary": "a", "rules": [{"variant": "common", "value": "a"}]}
        },
        mutate=set_at_path("names.rules[].value", None),
        expected_field="names.rules[].value",
        expected_check="required",
    ),
    Scenario(
        id="segment::names.rules[].value:string_min_length",
        scaffold={
            "names": {"primary": "a", "rules": [{"variant": "common", "value": "a"}]}
        },
        mutate=set_at_path("names.rules[].value", ""),
        expected_field="names.rules[].value",
        expected_check="string_min_length",
    ),
    Scenario(
        id="segment::names.rules[].value:stripped",
        scaffold={
            "names": {"primary": "a", "rules": [{"variant": "common", "value": "a"}]}
        },
        mutate=set_at_path("names.rules[].value", " has spaces "),
        expected_field="names.rules[].value",
        expected_check="stripped",
    ),
    Scenario(
        id="segment::names.rules[].variant:required",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].variant", None),
        expected_field="names.rules[].variant",
        expected_check="required",
    ),
    Scenario(
        id="segment::names.rules[].variant:enum",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].variant", "__INVALID__"),
        expected_field="names.rules[].variant",
        expected_check="enum",
    ),
    Scenario(
        id="segment::names.rules[].language:language_tag",
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
        id="segment::names.rules[].perspectives.mode:required",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [
                    {
                        "value": "a",
                        "variant": "common",
                        "perspectives": {"countries": ["US"], "mode": "accepted_by"},
                    }
                ],
            }
        },
        mutate=set_at_path("names.rules[].perspectives.mode", None),
        expected_field="names.rules[].perspectives.mode",
        expected_check="required",
    ),
    Scenario(
        id="segment::names.rules[].perspectives.mode:enum",
        scaffold={
            "names": {
                "primary": "a",
                "rules": [
                    {
                        "value": "a",
                        "variant": "common",
                        "perspectives": {"countries": ["US"], "mode": "accepted_by"},
                    }
                ],
            }
        },
        mutate=set_at_path("names.rules[].perspectives.mode", "__INVALID__"),
        expected_field="names.rules[].perspectives.mode",
        expected_check="enum",
    ),
    Scenario(
        id="segment::names.rules[].perspectives.countries:required",
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
        id="segment::names.rules[].perspectives.countries_min_length:array_min_length",
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
        id="segment::names.rules[].perspectives.countries_unique:struct_unique",
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
        id="segment::names.rules[].perspectives.countries[]:country_code_alpha2",
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
        id="segment::names.rules[].between:linear_range_length",
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
        id="segment::names.rules[].between:linear_range_bounds",
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
        id="segment::names.rules[].between:linear_range_order",
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
        id="segment::names.rules[].side:enum",
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
        id="segment::model:forbid_if:0",
        scaffold={"access_restrictions": [{"when": {"vehicle": [{}]}}]},
        mutate=lambda row: mutate_forbid_if(
            row,
            ["unit"],
            "dimension",
            "axle_count",
            array_path="access_restrictions",
            inner_array_path="when.vehicle",
        ),
        expected_field="access_restrictions[].when.vehicle[].unit_forbidden",
        expected_check="forbid_if",
    ),
    Scenario(
        id="segment::model:require_if:1",
        scaffold={"access_restrictions": [{"when": {"vehicle": [{}]}}]},
        mutate=lambda row: mutate_require_if(
            row,
            ["unit"],
            "dimension",
            "height",
            array_path="access_restrictions",
            inner_array_path="when.vehicle",
        ),
        expected_field="access_restrictions[].when.vehicle[].unit_required_0",
        expected_check="require_if",
    ),
    Scenario(
        id="segment::model:require_if:2",
        scaffold={"access_restrictions": [{"when": {"vehicle": [{}]}}]},
        mutate=lambda row: mutate_require_if(
            row,
            ["unit"],
            "dimension",
            "length",
            array_path="access_restrictions",
            inner_array_path="when.vehicle",
        ),
        expected_field="access_restrictions[].when.vehicle[].unit_required_1",
        expected_check="require_if",
    ),
    Scenario(
        id="segment::model:require_if:3",
        scaffold={"access_restrictions": [{"when": {"vehicle": [{}]}}]},
        mutate=lambda row: mutate_require_if(
            row,
            ["unit"],
            "dimension",
            "weight",
            array_path="access_restrictions",
            inner_array_path="when.vehicle",
        ),
        expected_field="access_restrictions[].when.vehicle[].unit_required_2",
        expected_check="require_if",
    ),
    Scenario(
        id="segment::model:require_if:4",
        scaffold={"access_restrictions": [{"when": {"vehicle": [{}]}}]},
        mutate=lambda row: mutate_require_if(
            row,
            ["unit"],
            "dimension",
            "width",
            array_path="access_restrictions",
            inner_array_path="when.vehicle",
        ),
        expected_field="access_restrictions[].when.vehicle[].unit_required_3",
        expected_check="require_if",
    ),
    Scenario(
        id="segment::model:require_any_of:5",
        scaffold={"access_restrictions": [{"when": {}}]},
        mutate=lambda row: mutate_require_any_of(
            row,
            ["heading", "during", "mode", "using", "recognized", "vehicle"],
            array_path="access_restrictions",
            struct_path="when",
        ),
        expected_field="access_restrictions[].when",
        expected_check="require_any_of",
    ),
    Scenario(
        id="segment::model:forbid_if:6",
        scaffold={},
        mutate=lambda row: mutate_forbid_if(row, ["class"], "subtype", "water"),
        expected_field="class_forbidden",
        expected_check="forbid_if",
    ),
    Scenario(
        id="segment::model:require_if:7",
        scaffold={},
        mutate=lambda row: mutate_require_if(row, ["class"], "subtype", "rail"),
        expected_field="class_required_0",
        expected_check="require_if",
    ),
    Scenario(
        id="segment::model:require_if:8",
        scaffold={},
        mutate=lambda row: mutate_require_if(row, ["class"], "subtype", "road"),
        expected_field="class_required_1",
        expected_check="require_if",
    ),
    Scenario(
        id="segment::model:forbid_if:9",
        scaffold={},
        mutate=lambda row: mutate_forbid_if(
            row,
            ["destinations"],
            "subtype",
            "road",
            negate=True,
            fill_values={"destinations": [{}]},
        ),
        expected_field="destinations_forbidden",
        expected_check="forbid_if",
    ),
    Scenario(
        id="segment::model:forbid_if:10",
        scaffold={},
        mutate=lambda row: mutate_forbid_if(
            row,
            ["prohibited_transitions"],
            "subtype",
            "road",
            negate=True,
            fill_values={"prohibited_transitions": [{}]},
        ),
        expected_field="prohibited_transitions_forbidden",
        expected_check="forbid_if",
    ),
    Scenario(
        id="segment::model:forbid_if:11",
        scaffold={},
        mutate=lambda row: mutate_forbid_if(
            row,
            ["road_flags"],
            "subtype",
            "road",
            negate=True,
            fill_values={"road_flags": [{}]},
        ),
        expected_field="road_flags_forbidden",
        expected_check="forbid_if",
    ),
    Scenario(
        id="segment::model:forbid_if:12",
        scaffold={},
        mutate=lambda row: mutate_forbid_if(
            row,
            ["road_surface"],
            "subtype",
            "road",
            negate=True,
            fill_values={"road_surface": [{}]},
        ),
        expected_field="road_surface_forbidden",
        expected_check="forbid_if",
    ),
    Scenario(
        id="segment::model:forbid_if:13",
        scaffold={},
        mutate=lambda row: mutate_forbid_if(
            row,
            ["speed_limits"],
            "subtype",
            "road",
            negate=True,
            fill_values={"speed_limits": [{}]},
        ),
        expected_field="speed_limits_forbidden",
        expected_check="forbid_if",
    ),
    Scenario(
        id="segment::model:forbid_if:14",
        scaffold={},
        mutate=lambda row: mutate_forbid_if(
            row, ["subclass"], "subtype", "road", negate=True
        ),
        expected_field="subclass_forbidden",
        expected_check="forbid_if",
    ),
    Scenario(
        id="segment::model:forbid_if:15",
        scaffold={},
        mutate=lambda row: mutate_forbid_if(
            row,
            ["width_rules"],
            "subtype",
            "road",
            negate=True,
            fill_values={"width_rules": [{}]},
        ),
        expected_field="width_rules_forbidden",
        expected_check="forbid_if",
    ),
    Scenario(
        id="segment::model:forbid_if:16",
        scaffold={},
        mutate=lambda row: mutate_forbid_if(
            row,
            ["rail_flags"],
            "subtype",
            "rail",
            negate=True,
            fill_values={"rail_flags": [{}]},
        ),
        expected_field="rail_flags_forbidden",
        expected_check="forbid_if",
    ),
]


@pytest.fixture(scope="module")
def checks() -> list:
    return segment_checks()


@pytest.fixture(scope="module")
def sparse_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        SEGMENT_SCHEMA,
        checks,
        BASE_ROW_SPARSE,
        SCENARIOS,
        model_name="segment",
    )


@pytest.fixture(scope="module")
def populated_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        SEGMENT_SCHEMA,
        checks,
        BASE_ROW_POPULATED,
        SCENARIOS,
        model_name="segment",
    )


def test_baseline_sparse(sparse_results: ValidationResults) -> None:
    """Sparse base row passes every check the codegen produced.

    Catches drift between base_row synthesis, schema_builder, and
    check_builder -- if any of those produce output inconsistent with
    the others (e.g. a check that rejects values the synthesizer emits
    for required-only fields), the baseline fails here before any
    scenario runs.
    """
    baseline = sparse_results.violations.get("segment::baseline", set())
    assert baseline == set(), f"Sparse baseline has violations: {baseline}"


def test_baseline_populated(populated_results: ValidationResults) -> None:
    """Fully-populated base row passes every check the codegen produced.

    Mirrors `test_baseline_sparse` but with all optional fields
    filled, exercising codegen paths that only fire when a value is
    present.
    """
    baseline = populated_results.violations.get("segment::baseline", set())
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
