# Auto-generated — do not edit.

"""Generated conformance tests for place."""

from __future__ import annotations

import pytest
from overture.schema.pyspark.expressions.generated.overture.schema.places.place import (
    PLACE_SCHEMA,
    place_checks,
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
    "id": "771dc733-3cd9-5ec4-a0b9-946ff01afb4e",
    "geometry": "POINT (0 0)",
    "theme": "places",
    "type": "place",
    "version": 0,
}


BASE_ROW_POPULATED: dict = {
    "id": "771dc733-3cd9-5ec4-a0b9-946ff01afb4e",
    "bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0},
    "geometry": "POINT (0 0)",
    "theme": "places",
    "type": "place",
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
    "operating_status": "open",
    "categories": {"primary": "snake_case", "alternate": ["snake_case"]},
    "basic_category": "snake_case",
    "taxonomy": {
        "primary": "snake_case",
        "hierarchy": ["snake_case"],
        "alternates": ["snake_case"],
    },
    "confidence": 0.0,
    "websites": ["https://example.com/"],
    "socials": ["https://example.com/"],
    "emails": ["user@example.com"],
    "phones": ["+1 555-555-5555"],
    "brand": {
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
        "wikidata": "Q42",
    },
    "addresses": [
        {
            "freeform": "",
            "locality": "",
            "postcode": "",
            "region": "US-CA",
            "country": "US",
        }
    ],
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
}


SCENARIOS: list[Scenario] = [
    Scenario(
        id="place::id:required",
        scaffold={},
        mutate=set_at_path("id", None),
        expected_field="id",
        expected_check="required",
    ),
    Scenario(
        id="place::id:string_min_length",
        scaffold={},
        mutate=set_at_path("id", ""),
        expected_field="id",
        expected_check="string_min_length",
    ),
    Scenario(
        id="place::id:no_whitespace",
        scaffold={},
        mutate=set_at_path("id", "has whitespace"),
        expected_field="id",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="place::bbox:bbox_completeness",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": None, "ymax": 1.0}
        ),
        expected_field="bbox",
        expected_check="bbox_completeness",
    ),
    Scenario(
        id="place::bbox:bbox_lat_ordering",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": 10.0, "ymax": -10.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_ordering",
    ),
    Scenario(
        id="place::bbox:bbox_lat_range",
        scaffold={"bbox": {"xmin": 0.0, "xmax": 1.0, "ymin": 0.0, "ymax": 1.0}},
        mutate=set_at_path(
            "bbox", {"xmin": 0.0, "xmax": 1.0, "ymin": -100.0, "ymax": 100.0}
        ),
        expected_field="bbox",
        expected_check="bbox_lat_range",
    ),
    Scenario(
        id="place::geometry:required",
        scaffold={},
        mutate=set_at_path("geometry", None),
        expected_field="geometry",
        expected_check="required",
    ),
    Scenario(
        id="place::geometry:geometry_type",
        scaffold={},
        mutate=set_at_path("geometry", "LINESTRING (0 0, 1 1)"),
        expected_field="geometry",
        expected_check="geometry_type",
    ),
    Scenario(
        id="place::theme:required",
        scaffold={},
        mutate=set_at_path("theme", None),
        expected_field="theme",
        expected_check="required",
    ),
    Scenario(
        id="place::theme:enum",
        scaffold={},
        mutate=set_at_path("theme", "__INVALID__"),
        expected_field="theme",
        expected_check="enum",
    ),
    Scenario(
        id="place::type:required",
        scaffold={},
        mutate=set_at_path("type", None),
        expected_field="type",
        expected_check="required",
    ),
    Scenario(
        id="place::type:enum",
        scaffold={},
        mutate=set_at_path("type", "__INVALID__"),
        expected_field="type",
        expected_check="enum",
    ),
    Scenario(
        id="place::version:required",
        scaffold={},
        mutate=set_at_path("version", None),
        expected_field="version",
        expected_check="required",
    ),
    Scenario(
        id="place::version:bounds",
        scaffold={},
        mutate=set_at_path("version", -1),
        expected_field="version",
        expected_check="bounds",
    ),
    Scenario(
        id="place::sources_min_length:array_min_length",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources", []),
        expected_field="sources_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="place::sources_unique:struct_unique",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=lambda row: mutate_unique_items(row, "sources"),
        expected_field="sources_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="place::sources[].property:required",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].property", None),
        expected_field="sources[].property",
        expected_check="required",
    ),
    Scenario(
        id="place::sources[].property:json_pointer",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].property", "no-slash"),
        expected_field="sources[].property",
        expected_check="json_pointer",
    ),
    Scenario(
        id="place::sources[].dataset:required",
        scaffold={"sources": [{"property": "/valid/pointer", "dataset": ""}]},
        mutate=set_at_path("sources[].dataset", None),
        expected_field="sources[].dataset",
        expected_check="required",
    ),
    Scenario(
        id="place::sources[].license:stripped",
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
        id="place::sources[].confidence_0:bounds",
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
        id="place::sources[].confidence_1:bounds",
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
        id="place::sources[].provider:string_min_length",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "provider": "a"}]
        },
        mutate=set_at_path("sources[].provider", ""),
        expected_field="sources[].provider",
        expected_check="string_min_length",
    ),
    Scenario(
        id="place::sources[].provider:snake_case",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "provider": "a"}]
        },
        mutate=set_at_path("sources[].provider", "HAS SPACES"),
        expected_field="sources[].provider",
        expected_check="snake_case",
    ),
    Scenario(
        id="place::sources[].resource:string_min_length",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "resource": "a"}]
        },
        mutate=set_at_path("sources[].resource", ""),
        expected_field="sources[].resource",
        expected_check="string_min_length",
    ),
    Scenario(
        id="place::sources[].resource:snake_case",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "resource": "a"}]
        },
        mutate=set_at_path("sources[].resource", "HAS SPACES"),
        expected_field="sources[].resource",
        expected_check="snake_case",
    ),
    Scenario(
        id="place::sources[].version:string_min_length",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "version": "a"}]
        },
        mutate=set_at_path("sources[].version", ""),
        expected_field="sources[].version",
        expected_check="string_min_length",
    ),
    Scenario(
        id="place::sources[].version:no_whitespace",
        scaffold={
            "sources": [{"property": "/valid/pointer", "dataset": "", "version": "a"}]
        },
        mutate=set_at_path("sources[].version", "has whitespace"),
        expected_field="sources[].version",
        expected_check="no_whitespace",
    ),
    Scenario(
        id="place::sources[].between:linear_range_length",
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
        id="place::sources[].between:linear_range_bounds",
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
        id="place::sources[].between:linear_range_order",
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
        id="place::operating_status:enum",
        scaffold={"operating_status": "open"},
        mutate=set_at_path("operating_status", "__INVALID__"),
        expected_field="operating_status",
        expected_check="enum",
    ),
    Scenario(
        id="place::categories.primary:required",
        scaffold={"categories": {"primary": "snake_case"}},
        mutate=set_at_path("categories.primary", None),
        expected_field="categories.primary",
        expected_check="required",
    ),
    Scenario(
        id="place::categories.primary:snake_case",
        scaffold={"categories": {"primary": "snake_case"}},
        mutate=set_at_path("categories.primary", "HAS SPACES"),
        expected_field="categories.primary",
        expected_check="snake_case",
    ),
    Scenario(
        id="place::categories.alternate_unique:struct_unique",
        scaffold={"categories": {"primary": "snake_case", "alternate": ["snake_case"]}},
        mutate=lambda row: mutate_unique_items(row, "categories.alternate"),
        expected_field="categories.alternate_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="place::categories.alternate[]:snake_case",
        scaffold={"categories": {"primary": "snake_case", "alternate": ["snake_case"]}},
        mutate=set_at_path("categories.alternate[]", "HAS SPACES"),
        expected_field="categories.alternate[]",
        expected_check="snake_case",
    ),
    Scenario(
        id="place::basic_category:snake_case",
        scaffold={"basic_category": "snake_case"},
        mutate=set_at_path("basic_category", "HAS SPACES"),
        expected_field="basic_category",
        expected_check="snake_case",
    ),
    Scenario(
        id="place::taxonomy.primary:required",
        scaffold={"taxonomy": {"primary": "snake_case", "hierarchy": ["snake_case"]}},
        mutate=set_at_path("taxonomy.primary", None),
        expected_field="taxonomy.primary",
        expected_check="required",
    ),
    Scenario(
        id="place::taxonomy.primary:snake_case",
        scaffold={"taxonomy": {"primary": "snake_case", "hierarchy": ["snake_case"]}},
        mutate=set_at_path("taxonomy.primary", "HAS SPACES"),
        expected_field="taxonomy.primary",
        expected_check="snake_case",
    ),
    Scenario(
        id="place::taxonomy.hierarchy:required",
        scaffold={"taxonomy": {"primary": "snake_case", "hierarchy": ["snake_case"]}},
        mutate=set_at_path("taxonomy.hierarchy", None),
        expected_field="taxonomy.hierarchy",
        expected_check="required",
    ),
    Scenario(
        id="place::taxonomy.hierarchy_min_length:array_min_length",
        scaffold={"taxonomy": {"primary": "snake_case", "hierarchy": ["snake_case"]}},
        mutate=set_at_path("taxonomy.hierarchy", []),
        expected_field="taxonomy.hierarchy_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="place::taxonomy.hierarchy_unique:struct_unique",
        scaffold={"taxonomy": {"primary": "snake_case", "hierarchy": ["snake_case"]}},
        mutate=lambda row: mutate_unique_items(row, "taxonomy.hierarchy"),
        expected_field="taxonomy.hierarchy_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="place::taxonomy.hierarchy[]:snake_case",
        scaffold={"taxonomy": {"primary": "snake_case", "hierarchy": ["snake_case"]}},
        mutate=set_at_path("taxonomy.hierarchy[]", "HAS SPACES"),
        expected_field="taxonomy.hierarchy[]",
        expected_check="snake_case",
    ),
    Scenario(
        id="place::taxonomy.alternates_min_length:array_min_length",
        scaffold={
            "taxonomy": {
                "primary": "snake_case",
                "hierarchy": ["snake_case"],
                "alternates": ["snake_case"],
            }
        },
        mutate=set_at_path("taxonomy.alternates", []),
        expected_field="taxonomy.alternates_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="place::taxonomy.alternates_unique:struct_unique",
        scaffold={
            "taxonomy": {
                "primary": "snake_case",
                "hierarchy": ["snake_case"],
                "alternates": ["snake_case"],
            }
        },
        mutate=lambda row: mutate_unique_items(row, "taxonomy.alternates"),
        expected_field="taxonomy.alternates_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="place::taxonomy.alternates[]:snake_case",
        scaffold={
            "taxonomy": {
                "primary": "snake_case",
                "hierarchy": ["snake_case"],
                "alternates": ["snake_case"],
            }
        },
        mutate=set_at_path("taxonomy.alternates[]", "HAS SPACES"),
        expected_field="taxonomy.alternates[]",
        expected_check="snake_case",
    ),
    Scenario(
        id="place::confidence_0:bounds",
        scaffold={"confidence": 0.0},
        mutate=set_at_path("confidence", -1.0),
        expected_field="confidence_0",
        expected_check="bounds",
    ),
    Scenario(
        id="place::confidence_1:bounds",
        scaffold={"confidence": 0.0},
        mutate=set_at_path("confidence", 2.0),
        expected_field="confidence_1",
        expected_check="bounds",
    ),
    Scenario(
        id="place::websites_min_length:array_min_length",
        scaffold={"websites": ["https://example.com/"]},
        mutate=set_at_path("websites", []),
        expected_field="websites_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="place::websites_unique:struct_unique",
        scaffold={"websites": ["https://example.com/"]},
        mutate=lambda row: mutate_unique_items(row, "websites"),
        expected_field="websites_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="place::websites[]:url_format",
        scaffold={"websites": ["https://example.com/"]},
        mutate=set_at_path("websites[]", "not-a-url"),
        expected_field="websites[]",
        expected_check="url_format",
    ),
    Scenario(
        id="place::websites[]:url_length",
        scaffold={"websites": ["https://example.com/"]},
        mutate=set_at_path(
            "websites[]",
            "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        ),
        expected_field="websites[]",
        expected_check="url_length",
    ),
    Scenario(
        id="place::socials_min_length:array_min_length",
        scaffold={"socials": ["https://example.com/"]},
        mutate=set_at_path("socials", []),
        expected_field="socials_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="place::socials_unique:struct_unique",
        scaffold={"socials": ["https://example.com/"]},
        mutate=lambda row: mutate_unique_items(row, "socials"),
        expected_field="socials_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="place::socials[]:url_format",
        scaffold={"socials": ["https://example.com/"]},
        mutate=set_at_path("socials[]", "not-a-url"),
        expected_field="socials[]",
        expected_check="url_format",
    ),
    Scenario(
        id="place::socials[]:url_length",
        scaffold={"socials": ["https://example.com/"]},
        mutate=set_at_path(
            "socials[]",
            "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        ),
        expected_field="socials[]",
        expected_check="url_length",
    ),
    Scenario(
        id="place::emails_min_length:array_min_length",
        scaffold={"emails": ["user@example.com"]},
        mutate=set_at_path("emails", []),
        expected_field="emails_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="place::emails_unique:struct_unique",
        scaffold={"emails": ["user@example.com"]},
        mutate=lambda row: mutate_unique_items(row, "emails"),
        expected_field="emails_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="place::emails[]:email",
        scaffold={"emails": ["user@example.com"]},
        mutate=set_at_path("emails[]", "not-an-email"),
        expected_field="emails[]",
        expected_check="email",
    ),
    Scenario(
        id="place::phones_min_length:array_min_length",
        scaffold={"phones": ["+1 555-555-5555"]},
        mutate=set_at_path("phones", []),
        expected_field="phones_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="place::phones_unique:struct_unique",
        scaffold={"phones": ["+1 555-555-5555"]},
        mutate=lambda row: mutate_unique_items(row, "phones"),
        expected_field="phones_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="place::phones[]:phone_number",
        scaffold={"phones": ["+1 555-555-5555"]},
        mutate=set_at_path("phones[]", "1234567890"),
        expected_field="phones[]",
        expected_check="phone_number",
    ),
    Scenario(
        id="place::brand.names.primary:required",
        scaffold={"brand": {"names": {"primary": "a"}}},
        mutate=set_at_path("brand.names.primary", None),
        expected_field="brand.names.primary",
        expected_check="required",
    ),
    Scenario(
        id="place::brand.names.primary:string_min_length",
        scaffold={"brand": {"names": {"primary": "a"}}},
        mutate=set_at_path("brand.names.primary", ""),
        expected_field="brand.names.primary",
        expected_check="string_min_length",
    ),
    Scenario(
        id="place::brand.names.primary:stripped",
        scaffold={"brand": {"names": {"primary": "a"}}},
        mutate=set_at_path("brand.names.primary", " has spaces "),
        expected_field="brand.names.primary",
        expected_check="stripped",
    ),
    Scenario(
        id="place::brand.names.common{key}:language_tag",
        scaffold={"brand": {"names": {"primary": "a", "common": {"en": "clean"}}}},
        mutate=lambda row: mutate_map_key(row, "brand.names.common", "123"),
        expected_field="brand.names.common{key}",
        expected_check="language_tag",
    ),
    Scenario(
        id="place::brand.names.common{value}:stripped",
        scaffold={"brand": {"names": {"primary": "a", "common": {"en": "clean"}}}},
        mutate=lambda row: mutate_map_value(row, "brand.names.common", " has spaces "),
        expected_field="brand.names.common{value}",
        expected_check="stripped",
    ),
    Scenario(
        id="place::brand.names.rules[].value:required",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [{"value": "a", "variant": "common"}],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].value", None),
        expected_field="brand.names.rules[].value",
        expected_check="required",
    ),
    Scenario(
        id="place::brand.names.rules[].value:string_min_length",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [{"value": "a", "variant": "common"}],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].value", ""),
        expected_field="brand.names.rules[].value",
        expected_check="string_min_length",
    ),
    Scenario(
        id="place::brand.names.rules[].value:stripped",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [{"value": "a", "variant": "common"}],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].value", " has spaces "),
        expected_field="brand.names.rules[].value",
        expected_check="stripped",
    ),
    Scenario(
        id="place::brand.names.rules[].variant:required",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [{"value": "a", "variant": "common"}],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].variant", None),
        expected_field="brand.names.rules[].variant",
        expected_check="required",
    ),
    Scenario(
        id="place::brand.names.rules[].variant:enum",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [{"value": "a", "variant": "common"}],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].variant", "__INVALID__"),
        expected_field="brand.names.rules[].variant",
        expected_check="enum",
    ),
    Scenario(
        id="place::brand.names.rules[].language:language_tag",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [{"value": "a", "variant": "common", "language": "en"}],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].language", "123"),
        expected_field="brand.names.rules[].language",
        expected_check="language_tag",
    ),
    Scenario(
        id="place::brand.names.rules[].perspectives.mode:required",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [
                        {
                            "value": "a",
                            "variant": "common",
                            "perspectives": {
                                "mode": "accepted_by",
                                "countries": ["US"],
                            },
                        }
                    ],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].perspectives.mode", None),
        expected_field="brand.names.rules[].perspectives.mode",
        expected_check="required",
    ),
    Scenario(
        id="place::brand.names.rules[].perspectives.mode:enum",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [
                        {
                            "value": "a",
                            "variant": "common",
                            "perspectives": {
                                "mode": "accepted_by",
                                "countries": ["US"],
                            },
                        }
                    ],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].perspectives.mode", "__INVALID__"),
        expected_field="brand.names.rules[].perspectives.mode",
        expected_check="enum",
    ),
    Scenario(
        id="place::brand.names.rules[].perspectives.countries:required",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [
                        {
                            "value": "a",
                            "variant": "common",
                            "perspectives": {
                                "mode": "accepted_by",
                                "countries": ["US"],
                            },
                        }
                    ],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].perspectives.countries", None),
        expected_field="brand.names.rules[].perspectives.countries",
        expected_check="required",
    ),
    Scenario(
        id="place::brand.names.rules[].perspectives.countries_min_length:array_min_length",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [
                        {
                            "value": "a",
                            "variant": "common",
                            "perspectives": {
                                "mode": "accepted_by",
                                "countries": ["US"],
                            },
                        }
                    ],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].perspectives.countries", []),
        expected_field="brand.names.rules[].perspectives.countries_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="place::brand.names.rules[].perspectives.countries_unique:struct_unique",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [
                        {
                            "value": "a",
                            "variant": "common",
                            "perspectives": {
                                "mode": "accepted_by",
                                "countries": ["US"],
                            },
                        }
                    ],
                }
            }
        },
        mutate=lambda row: mutate_unique_items(
            row, "brand.names.rules[].perspectives.countries"
        ),
        expected_field="brand.names.rules[].perspectives.countries_unique",
        expected_check="struct_unique",
    ),
    Scenario(
        id="place::brand.names.rules[].perspectives.countries[]:country_code_alpha2",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [
                        {
                            "value": "a",
                            "variant": "common",
                            "perspectives": {
                                "mode": "accepted_by",
                                "countries": ["US"],
                            },
                        }
                    ],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].perspectives.countries[]", "99"),
        expected_field="brand.names.rules[].perspectives.countries[]",
        expected_check="country_code_alpha2",
    ),
    Scenario(
        id="place::brand.names.rules[].between:linear_range_length",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [
                        {"value": "a", "variant": "common", "between": [0.0, 1.0]}
                    ],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].between", [0.5]),
        expected_field="brand.names.rules[].between",
        expected_check="linear_range_length",
    ),
    Scenario(
        id="place::brand.names.rules[].between:linear_range_bounds",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [
                        {"value": "a", "variant": "common", "between": [0.0, 1.0]}
                    ],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].between", [1.5, 2.0]),
        expected_field="brand.names.rules[].between",
        expected_check="linear_range_bounds",
    ),
    Scenario(
        id="place::brand.names.rules[].between:linear_range_order",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [
                        {"value": "a", "variant": "common", "between": [0.0, 1.0]}
                    ],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].between", [0.8, 0.2]),
        expected_field="brand.names.rules[].between",
        expected_check="linear_range_order",
    ),
    Scenario(
        id="place::brand.names.rules[].side:enum",
        scaffold={
            "brand": {
                "names": {
                    "primary": "a",
                    "rules": [{"value": "a", "variant": "common", "side": "left"}],
                }
            }
        },
        mutate=set_at_path("brand.names.rules[].side", "__INVALID__"),
        expected_field="brand.names.rules[].side",
        expected_check="enum",
    ),
    Scenario(
        id="place::brand.wikidata:wikidata_id",
        scaffold={"brand": {"wikidata": "Q42"}},
        mutate=set_at_path("brand.wikidata", "P999"),
        expected_field="brand.wikidata",
        expected_check="wikidata_id",
    ),
    Scenario(
        id="place::addresses_min_length:array_min_length",
        scaffold={"addresses": [{}]},
        mutate=set_at_path("addresses", []),
        expected_field="addresses_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="place::addresses[].region:region_code",
        scaffold={"addresses": [{"region": "US-CA"}]},
        mutate=set_at_path("addresses[].region", "99-999"),
        expected_field="addresses[].region",
        expected_check="region_code",
    ),
    Scenario(
        id="place::addresses[].country:country_code_alpha2",
        scaffold={"addresses": [{"country": "US"}]},
        mutate=set_at_path("addresses[].country", "99"),
        expected_field="addresses[].country",
        expected_check="country_code_alpha2",
    ),
    Scenario(
        id="place::names.primary:required",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", None),
        expected_field="names.primary",
        expected_check="required",
    ),
    Scenario(
        id="place::names.primary:string_min_length",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", ""),
        expected_field="names.primary",
        expected_check="string_min_length",
    ),
    Scenario(
        id="place::names.primary:stripped",
        scaffold={"names": {"primary": "a"}},
        mutate=set_at_path("names.primary", " has spaces "),
        expected_field="names.primary",
        expected_check="stripped",
    ),
    Scenario(
        id="place::names.common{key}:language_tag",
        scaffold={"names": {"primary": "a", "common": {"en": "clean"}}},
        mutate=lambda row: mutate_map_key(row, "names.common", "123"),
        expected_field="names.common{key}",
        expected_check="language_tag",
    ),
    Scenario(
        id="place::names.common{value}:stripped",
        scaffold={"names": {"primary": "a", "common": {"en": "clean"}}},
        mutate=lambda row: mutate_map_value(row, "names.common", " has spaces "),
        expected_field="names.common{value}",
        expected_check="stripped",
    ),
    Scenario(
        id="place::names.rules[].value:required",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].value", None),
        expected_field="names.rules[].value",
        expected_check="required",
    ),
    Scenario(
        id="place::names.rules[].value:string_min_length",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].value", ""),
        expected_field="names.rules[].value",
        expected_check="string_min_length",
    ),
    Scenario(
        id="place::names.rules[].value:stripped",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].value", " has spaces "),
        expected_field="names.rules[].value",
        expected_check="stripped",
    ),
    Scenario(
        id="place::names.rules[].variant:required",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].variant", None),
        expected_field="names.rules[].variant",
        expected_check="required",
    ),
    Scenario(
        id="place::names.rules[].variant:enum",
        scaffold={
            "names": {"primary": "a", "rules": [{"value": "a", "variant": "common"}]}
        },
        mutate=set_at_path("names.rules[].variant", "__INVALID__"),
        expected_field="names.rules[].variant",
        expected_check="enum",
    ),
    Scenario(
        id="place::names.rules[].language:language_tag",
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
        id="place::names.rules[].perspectives.mode:required",
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
        id="place::names.rules[].perspectives.mode:enum",
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
        id="place::names.rules[].perspectives.countries:required",
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
        id="place::names.rules[].perspectives.countries_min_length:array_min_length",
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
        id="place::names.rules[].perspectives.countries_unique:struct_unique",
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
        id="place::names.rules[].perspectives.countries[]:country_code_alpha2",
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
        id="place::names.rules[].between:linear_range_length",
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
        id="place::names.rules[].between:linear_range_bounds",
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
        id="place::names.rules[].between:linear_range_order",
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
        id="place::names.rules[].side:enum",
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
]


@pytest.fixture(scope="module")
def checks() -> list:
    return place_checks()


@pytest.fixture(scope="module")
def sparse_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        PLACE_SCHEMA,
        checks,
        BASE_ROW_SPARSE,
        SCENARIOS,
        model_name="place",
    )


@pytest.fixture(scope="module")
def populated_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        PLACE_SCHEMA,
        checks,
        BASE_ROW_POPULATED,
        SCENARIOS,
        model_name="place",
    )


def test_baseline_sparse(sparse_results: ValidationResults) -> None:
    """Sparse base row passes every check the codegen produced.

    Catches drift between base_row synthesis, schema_builder, and
    check_builder -- if any of those produce output inconsistent with
    the others (e.g. a check that rejects values the synthesizer emits
    for required-only fields), the baseline fails here before any
    scenario runs.
    """
    baseline = sparse_results.violations.get("place::baseline", set())
    assert baseline == set(), f"Sparse baseline has violations: {baseline}"


def test_baseline_populated(populated_results: ValidationResults) -> None:
    """Fully-populated base row passes every check the codegen produced.

    Mirrors `test_baseline_sparse` but with all optional fields
    filled, exercising codegen paths that only fire when a value is
    present.
    """
    baseline = populated_results.violations.get("place::baseline", set())
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
