# Auto-generated — do not edit.

"""Generated conformance tests for sources."""

from __future__ import annotations

import pytest
from overture.schema.pyspark.expressions.generated.overture.schema.annex.sources import (
    SOURCES_SCHEMA,
    sources_checks,
)
from pyspark.sql import SparkSession

from ....._support.harness import (
    ValidationResults,
    run_validation_pipeline,
)
from ....._support.helpers import set_at_path
from ....._support.mutations import mutate_map_key, mutate_map_value
from ....._support.scenarios import Scenario

BASE_ROW_SPARSE: dict = {
    "datasets": [
        {
            "source_name": "",
            "source_dataset_name": "",
            "data_url": "https://example.com/",
            "data_url_archived": "https://example.com/",
            "license_url": "https://example.com/",
            "license_url_archived": "https://example.com/",
            "license_type": "",
            "license_text": "",
            "license_attribution": "",
            "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
        }
    ],
    "license_priority": {"ODbL-1.0": 0},
}


BASE_ROW_POPULATED: dict = {
    "datasets": [
        {
            "source_name": "",
            "source_dataset_name": "",
            "data_url": "https://example.com/",
            "data_url_archived": "https://example.com/",
            "license_url": "https://example.com/",
            "license_url_archived": "https://example.com/",
            "license_type": "",
            "license_text": "",
            "license_attribution": "",
            "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
            "inception_date": "2024-01-01",
            "url": "https://example.com/",
            "url_archived": "https://example.com/",
            "data_download_url": ["https://example.com/"],
            "countries": ["US"],
            "coverage_description": "",
            "data_layer_name": "",
            "oa_path": [""],
            "address_levels": [""],
            "file_format": "",
            "update_frequency": "",
            "build_source": "OpenAddresses",
            "update_type": "continuous",
            "update_schedule": [""],
            "known_issues": "",
            "notes": "",
            "requires_attribution": "",
        }
    ],
    "license_priority": {"ODbL-1.0": 0},
}


SCENARIOS: list[Scenario] = [
    Scenario(
        id="sources::datasets:required",
        scaffold={},
        mutate=set_at_path("datasets", None),
        expected_field="datasets",
        expected_check="required",
    ),
    Scenario(
        id="sources::datasets[].source_name:required",
        scaffold={
            "datasets": [
                {
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "source_name": "",
                }
            ]
        },
        mutate=set_at_path("datasets[].source_name", None),
        expected_field="datasets[].source_name",
        expected_check="required",
    ),
    Scenario(
        id="sources::datasets[].source_dataset_name:required",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "source_dataset_name": "",
                }
            ]
        },
        mutate=set_at_path("datasets[].source_dataset_name", None),
        expected_field="datasets[].source_dataset_name",
        expected_check="required",
    ),
    Scenario(
        id="sources::datasets[].data_url:required",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "data_url": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path("datasets[].data_url", None),
        expected_field="datasets[].data_url",
        expected_check="required",
    ),
    Scenario(
        id="sources::datasets[].data_url:url_format",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "data_url": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path("datasets[].data_url", "not-a-url"),
        expected_field="datasets[].data_url",
        expected_check="url_format",
    ),
    Scenario(
        id="sources::datasets[].data_url:url_length",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "data_url": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path(
            "datasets[].data_url",
            "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        ),
        expected_field="datasets[].data_url",
        expected_check="url_length",
    ),
    Scenario(
        id="sources::datasets[].data_url_archived:required",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "data_url_archived": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path("datasets[].data_url_archived", None),
        expected_field="datasets[].data_url_archived",
        expected_check="required",
    ),
    Scenario(
        id="sources::datasets[].data_url_archived:url_format",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "data_url_archived": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path("datasets[].data_url_archived", "not-a-url"),
        expected_field="datasets[].data_url_archived",
        expected_check="url_format",
    ),
    Scenario(
        id="sources::datasets[].data_url_archived:url_length",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "data_url_archived": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path(
            "datasets[].data_url_archived",
            "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        ),
        expected_field="datasets[].data_url_archived",
        expected_check="url_length",
    ),
    Scenario(
        id="sources::datasets[].license_url:required",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "license_url": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path("datasets[].license_url", None),
        expected_field="datasets[].license_url",
        expected_check="required",
    ),
    Scenario(
        id="sources::datasets[].license_url:url_format",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "license_url": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path("datasets[].license_url", "not-a-url"),
        expected_field="datasets[].license_url",
        expected_check="url_format",
    ),
    Scenario(
        id="sources::datasets[].license_url:url_length",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "license_url": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path(
            "datasets[].license_url",
            "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        ),
        expected_field="datasets[].license_url",
        expected_check="url_length",
    ),
    Scenario(
        id="sources::datasets[].license_url_archived:required",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "license_url_archived": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path("datasets[].license_url_archived", None),
        expected_field="datasets[].license_url_archived",
        expected_check="required",
    ),
    Scenario(
        id="sources::datasets[].license_url_archived:url_format",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "license_url_archived": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path("datasets[].license_url_archived", "not-a-url"),
        expected_field="datasets[].license_url_archived",
        expected_check="url_format",
    ),
    Scenario(
        id="sources::datasets[].license_url_archived:url_length",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "license_url_archived": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path(
            "datasets[].license_url_archived",
            "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        ),
        expected_field="datasets[].license_url_archived",
        expected_check="url_length",
    ),
    Scenario(
        id="sources::datasets[].license_type:required",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "license_type": "",
                }
            ]
        },
        mutate=set_at_path("datasets[].license_type", None),
        expected_field="datasets[].license_type",
        expected_check="required",
    ),
    Scenario(
        id="sources::datasets[].license_text:required",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "license_text": "",
                }
            ]
        },
        mutate=set_at_path("datasets[].license_text", None),
        expected_field="datasets[].license_text",
        expected_check="required",
    ),
    Scenario(
        id="sources::datasets[].license_attribution:required",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "license_attribution": "",
                }
            ]
        },
        mutate=set_at_path("datasets[].license_attribution", None),
        expected_field="datasets[].license_attribution",
        expected_check="required",
    ),
    Scenario(
        id="sources::datasets[].coverage_bbox:required",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                }
            ]
        },
        mutate=set_at_path("datasets[].coverage_bbox", None),
        expected_field="datasets[].coverage_bbox",
        expected_check="required",
    ),
    Scenario(
        id="sources::datasets[].coverage_bbox_min_length:array_min_length",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                }
            ]
        },
        mutate=set_at_path("datasets[].coverage_bbox", []),
        expected_field="datasets[].coverage_bbox_min_length",
        expected_check="array_min_length",
    ),
    Scenario(
        id="sources::datasets[].coverage_bbox_max_length:array_max_length",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                }
            ]
        },
        mutate=set_at_path("datasets[].coverage_bbox", [{}, {}, {}, {}, {}]),
        expected_field="datasets[].coverage_bbox_max_length",
        expected_check="array_max_length",
    ),
    Scenario(
        id="sources::datasets[].url:url_format",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "url": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path("datasets[].url", "not-a-url"),
        expected_field="datasets[].url",
        expected_check="url_format",
    ),
    Scenario(
        id="sources::datasets[].url:url_length",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "url": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path(
            "datasets[].url",
            "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        ),
        expected_field="datasets[].url",
        expected_check="url_length",
    ),
    Scenario(
        id="sources::datasets[].url_archived:url_format",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "url_archived": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path("datasets[].url_archived", "not-a-url"),
        expected_field="datasets[].url_archived",
        expected_check="url_format",
    ),
    Scenario(
        id="sources::datasets[].url_archived:url_length",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "url_archived": "https://example.com/",
                }
            ]
        },
        mutate=set_at_path(
            "datasets[].url_archived",
            "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        ),
        expected_field="datasets[].url_archived",
        expected_check="url_length",
    ),
    Scenario(
        id="sources::datasets[].data_download_url[]:url_format",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "data_download_url": ["https://example.com/"],
                }
            ]
        },
        mutate=set_at_path("datasets[].data_download_url[]", "not-a-url"),
        expected_field="datasets[].data_download_url[]",
        expected_check="url_format",
    ),
    Scenario(
        id="sources::datasets[].data_download_url[]:url_length",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "data_download_url": ["https://example.com/"],
                }
            ]
        },
        mutate=set_at_path(
            "datasets[].data_download_url[]",
            "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        ),
        expected_field="datasets[].data_download_url[]",
        expected_check="url_length",
    ),
    Scenario(
        id="sources::datasets[].countries[]:country_code_alpha2",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "countries": ["US"],
                }
            ]
        },
        mutate=set_at_path("datasets[].countries[]", "99"),
        expected_field="datasets[].countries[]",
        expected_check="country_code_alpha2",
    ),
    Scenario(
        id="sources::datasets[].build_source:enum",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "build_source": "OpenAddresses",
                }
            ]
        },
        mutate=set_at_path("datasets[].build_source", "__INVALID__"),
        expected_field="datasets[].build_source",
        expected_check="enum",
    ),
    Scenario(
        id="sources::datasets[].update_type:enum",
        scaffold={
            "datasets": [
                {
                    "source_name": "",
                    "source_dataset_name": "",
                    "data_url": "https://example.com/",
                    "data_url_archived": "https://example.com/",
                    "license_url": "https://example.com/",
                    "license_url_archived": "https://example.com/",
                    "license_type": "",
                    "license_text": "",
                    "license_attribution": "",
                    "coverage_bbox": [0.0, 0.0, 0.0, 0.0],
                    "update_type": "continuous",
                }
            ]
        },
        mutate=set_at_path("datasets[].update_type", "__INVALID__"),
        expected_field="datasets[].update_type",
        expected_check="enum",
    ),
    Scenario(
        id="sources::license_priority:required",
        scaffold={},
        mutate=set_at_path("license_priority", None),
        expected_field="license_priority",
        expected_check="required",
    ),
    Scenario(
        id="sources::license_priority{key}:pattern",
        scaffold={},
        mutate=lambda row: mutate_map_key(row, "license_priority", "bad license!"),
        expected_field="license_priority{key}",
        expected_check="pattern",
    ),
    Scenario(
        id="sources::license_priority{value}:bounds",
        scaffold={},
        mutate=lambda row: mutate_map_value(row, "license_priority", -1),
        expected_field="license_priority{value}",
        expected_check="bounds",
    ),
]


@pytest.fixture(scope="module")
def checks() -> list:
    return sources_checks()


@pytest.fixture(scope="module")
def sparse_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        SOURCES_SCHEMA,
        checks,
        BASE_ROW_SPARSE,
        SCENARIOS,
        model_name="sources",
    )


@pytest.fixture(scope="module")
def populated_results(spark: SparkSession, checks: list) -> ValidationResults:
    return run_validation_pipeline(
        spark,
        SOURCES_SCHEMA,
        checks,
        BASE_ROW_POPULATED,
        SCENARIOS,
        model_name="sources",
    )


def test_baseline_sparse(sparse_results: ValidationResults) -> None:
    """Sparse base row passes every check the codegen produced.

    Catches drift between base_row synthesis, schema_builder, and
    check_builder -- if any of those produce output inconsistent with
    the others (e.g. a check that rejects values the synthesizer emits
    for required-only fields), the baseline fails here before any
    scenario runs.
    """
    baseline = sparse_results.violations.get("sources::baseline", set())
    assert baseline == set(), f"Sparse baseline has violations: {baseline}"


def test_baseline_populated(populated_results: ValidationResults) -> None:
    """Fully-populated base row passes every check the codegen produced.

    Mirrors `test_baseline_sparse` but with all optional fields
    filled, exercising codegen paths that only fire when a value is
    present.
    """
    baseline = populated_results.violations.get("sources::baseline", set())
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
