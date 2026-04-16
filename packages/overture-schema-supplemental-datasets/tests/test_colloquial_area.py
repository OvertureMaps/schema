"""Tests for ColloquialArea feature type."""

import pytest
from overture.schema.supplemental import ColloquialArea
from pydantic import ValidationError


def test_colloquial_area_minimal() -> None:
    """Test minimal valid colloquial area."""
    data = {
        "id": "test:area:1",
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-74.01, 40.71],
                [-74.00, 40.71],
                [-74.00, 40.72],
                [-74.01, 40.72],
                [-74.01, 40.71],
            ]],
        },
        "properties": {
            "type": "colloquial_area",
            "version": 1,
            "names": {
                "primary": "Test Area",
            },
            "sources": [
                {
                    "property": "",
                    "dataset": "test_dataset",
                }
            ],
        },
    }

    area = ColloquialArea.model_validate(data)
    assert area.id == "test:area:1"
    assert area.properties.names.primary == "Test Area"
    assert area.properties.type == "colloquial_area"


def test_colloquial_area_full() -> None:
    """Test colloquial area with all optional properties."""
    data = {
        "id": "test:area:east_asia",
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [100.0, 10.0],
                [145.0, 10.0],
                [145.0, 50.0],
                [100.0, 50.0],
                [100.0, 10.0],
            ]],
        },
        "properties": {
            "type": "colloquial_area",
            "version": 1,
            "names": {
                "primary": "East Asia",
                "common": {
                    "en": "East Asia",
                    "zh-CN": "东亚",
                },
            },
            "bbox": [100.0, 10.0, 145.0, 50.0],
            "center_point": {
                "type": "Point",
                "coordinates": [122.5, 30.0],
            },
            "wikipedia_url": "https://en.wikipedia.org/wiki/East_Asia",
            "wikidata": "Q27231",
            "sources": [
                {
                    "property": "",
                    "dataset": "test_dataset",
                    "license": "ODbL-1.0",
                }
            ],
        },
    }

    area = ColloquialArea.model_validate(data)
    assert area.properties.wikidata == "Q27231"
    assert area.properties.center_point is not None
    assert area.properties.center_point.to_geo_json()["coordinates"] == (122.5, 30.0)


def test_colloquial_area_invalid_geometry() -> None:
    """Test that Point geometry is rejected."""
    data = {
        "id": "test:area:invalid",
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-74.00, 40.71],
        },
        "properties": {
            "type": "colloquial_area",
            "version": 1,
            "names": {
                "primary": "Invalid",
            },
            "sources": [{"property": "", "dataset": "test"}],
        },
    }

    with pytest.raises(ValidationError):
        ColloquialArea.model_validate(data)


def test_colloquial_area_missing_names() -> None:
    """Test that missing names property fails validation."""
    data = {
        "id": "test:area:invalid",
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-74.01, 40.71],
                [-74.00, 40.71],
                [-74.00, 40.72],
                [-74.01, 40.72],
                [-74.01, 40.71],
            ]],
        },
        "properties": {
            "type": "colloquial_area",
            "version": 1,
            "sources": [{"property": "", "dataset": "test"}],
        },
    }

    with pytest.raises(ValidationError):
        ColloquialArea.model_validate(data)
