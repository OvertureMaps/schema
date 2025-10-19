"""Tests for serialization/deserialization functionality in overture-schema-core.

Tests mode switching and geometry format support with synthetic data.
"""

import json
from typing import Any, Literal

import pytest
from deepdiff import DeepDiff
from overture.schema.core import OvertureFeature, parse_feature
from pydantic import Field
from shapely.geometry import Point


class Place(OvertureFeature):
    """Simple stubbed place model for testing serde functionality."""

    theme: Literal["places"]
    type: Literal["place"]

    names: dict[str, str] | None = Field(None, description="Place names")
    categories: dict[str, str] | None = Field(None, description="Place categories")
    confidence: float | None = Field(None, description="Confidence score")


# Note: StubPlace is not registered in the parser union type,
# so it will only work if it matches the existing Place model structure


def deep_compare_dicts(
    original: dict[str, Any], parsed: dict[str, Any]
) -> tuple[bool, str]:
    """Perform deep comparison between original and parsed dictionaries.

    Returns (is_equal, differences_report).
    """
    diff = DeepDiff(original, parsed, ignore_order=True, significant_digits=15)

    if not diff:
        return True, ""

    # Format differences for readable output
    differences = []

    if "values_changed" in diff:
        differences.append("Value changes:")
        for key, change in diff["values_changed"].items():
            differences.append(
                f"  {key}: {change['old_value']} -> {change['new_value']}"
            )

    if "dictionary_item_added" in diff:
        differences.append("Added items:")
        for item in diff["dictionary_item_added"]:
            differences.append(f"  {item}")

    if "dictionary_item_removed" in diff:
        differences.append("Removed items:")
        for item in diff["dictionary_item_removed"]:
            differences.append(f"  {item}")

    if "type_changes" in diff:
        differences.append("Type changes:")
        for key, change in diff["type_changes"].items():
            differences.append(f"  {key}: {change['old_type']} -> {change['new_type']}")

    return False, "\n".join(differences)


# Synthetic test data
SAMPLE_FLAT_FEATURE = {
    "id": "test-feature-123",
    "geometry": {"type": "Point", "coordinates": [-122.4194, 37.7749]},
    "theme": "places",
    "type": "place",
    "version": 1,
    "names": {"primary": "Test Place"},
    "categories": {"primary": "restaurant"},
    "confidence": 0.95,
}

SAMPLE_GEOJSON_FEATURE = {
    "type": "Feature",
    "id": "test-feature-123",
    "geometry": {"type": "Point", "coordinates": [-122.4194, 37.7749]},
    "properties": {
        "theme": "places",
        "type": "place",
        "version": 1,
        "names": {"primary": "Test Place"},
        "categories": {"primary": "restaurant"},
        "confidence": 0.95,
    },
}


class TestSerializationModes:
    """Test serialization mode functionality."""

    def test_python_mode_output_structure(self) -> None:
        """Test that Python mode returns flattened structure."""
        result = parse_feature(SAMPLE_FLAT_FEATURE, Place, mode="python")
        assert result is not None

        # Should be flattened (no properties key)
        assert "properties" not in result
        assert "id" in result
        assert "geometry" in result
        assert "theme" in result
        assert "type" in result
        assert result["id"] == "test-feature-123"
        assert result["theme"] == "places"
        assert result["type"] == "place"

    def test_json_mode_output_structure(self) -> None:
        """Test that JSON mode returns GeoJSON structure."""
        result = parse_feature(SAMPLE_FLAT_FEATURE, Place, mode="json")
        assert result is not None

        # Should be GeoJSON
        assert result["type"] == "Feature"
        assert "properties" in result
        assert "id" in result
        assert "geometry" in result

        # Properties should contain theme and type
        properties = result["properties"]
        assert properties is not None
        assert "theme" in properties
        assert "type" in properties
        assert properties["theme"] == "places"
        assert properties["type"] == "place"

    def test_mode_data_consistency(self) -> None:
        """Test that both modes contain the same data, just structured differently."""
        python_result = parse_feature(SAMPLE_FLAT_FEATURE, Place, mode="python")
        json_result = parse_feature(SAMPLE_FLAT_FEATURE, Place, mode="json")
        assert python_result is not None
        assert json_result is not None

        # Flatten JSON result for comparison
        flattened_from_json = {
            "id": json_result["id"],
            "geometry": json_result["geometry"],
            **json_result["properties"],
        }

        # Handle geometry objects for comparison
        python_normalized = python_result.copy()
        if "geometry" in python_normalized and hasattr(
            python_normalized["geometry"], "to_geo_json"
        ):
            python_normalized["geometry"] = python_normalized["geometry"].to_geo_json()

        # Normalize both through JSON for comparison
        python_json = json.loads(json.dumps(python_normalized, default=str))
        flattened_json = json.loads(json.dumps(flattened_from_json, default=str))

        is_equal, diff_report = deep_compare_dicts(python_json, flattened_json)
        assert is_equal, (
            f"Python and JSON modes should contain same data:\n{diff_report}"
        )

    def test_roundtrip_consistency(self) -> None:
        """Test that Python->JSON->Python roundtrip preserves data."""
        # Parse in Python mode
        python_output = parse_feature(SAMPLE_FLAT_FEATURE, Place, mode="python")

        # Parse in JSON mode, then back to Python
        json_output = parse_feature(SAMPLE_FLAT_FEATURE, Place, mode="json")
        assert json_output is not None
        roundtrip_output = parse_feature(json_output, Place, mode="python")

        assert python_output is not None
        assert roundtrip_output is not None

        # Normalize both for comparison
        python_normalized = python_output.copy()
        if "geometry" in python_normalized and hasattr(
            python_normalized["geometry"], "to_geo_json"
        ):
            python_normalized["geometry"] = python_normalized["geometry"].to_geo_json()
        python_normalized = json.loads(json.dumps(python_normalized, default=str))

        roundtrip_normalized = roundtrip_output.copy()
        if "geometry" in roundtrip_normalized and hasattr(
            roundtrip_normalized["geometry"], "to_geo_json"
        ):
            roundtrip_normalized["geometry"] = roundtrip_normalized[
                "geometry"
            ].to_geo_json()
        roundtrip_normalized = json.loads(json.dumps(roundtrip_normalized, default=str))

        is_equal, diff_report = deep_compare_dicts(
            python_normalized, roundtrip_normalized
        )
        assert is_equal, f"Roundtrip should preserve data:\n{diff_report}"

    def test_input_format_independence(self) -> None:
        """Test that flat vs GeoJSON input produces same output."""
        # Parse both input formats in both modes
        python_from_flat = parse_feature(SAMPLE_FLAT_FEATURE, Place, mode="python")
        json_from_flat = parse_feature(SAMPLE_FLAT_FEATURE, Place, mode="json")
        python_from_geojson = parse_feature(
            SAMPLE_GEOJSON_FEATURE, Place, mode="python"
        )
        json_from_geojson = parse_feature(SAMPLE_GEOJSON_FEATURE, Place, mode="json")

        assert python_from_flat is not None
        assert json_from_flat is not None
        assert python_from_geojson is not None
        assert json_from_geojson is not None

        # Results should be identical regardless of input format
        is_equal, diff_report = deep_compare_dicts(
            python_from_flat, python_from_geojson
        )
        assert is_equal, (
            f"Python mode should produce same result from flat/GeoJSON input:\n{diff_report}"
        )

        is_equal, diff_report = deep_compare_dicts(json_from_flat, json_from_geojson)
        assert is_equal, (
            f"JSON mode should produce same result from flat/GeoJSON input:\n{diff_report}"
        )


class TestGeometryFormats:
    """Test geometry format support."""

    def test_geojson_geometry_input(self) -> None:
        """Test parsing with GeoJSON geometry dict."""
        feature = SAMPLE_FLAT_FEATURE.copy()
        geometry_dict = feature["geometry"]
        assert isinstance(geometry_dict, dict)
        expected_coords = geometry_dict["coordinates"]

        result = parse_feature(feature, Place, mode="python")
        assert result is not None
        assert "geometry" in result

        # Check that geometry is properly parsed
        geometry = result["geometry"]
        assert hasattr(geometry, "to_geo_json")
        geo_json = geometry.to_geo_json()
        assert geo_json["type"] == "Point"
        assert list(geo_json["coordinates"]) == expected_coords

    def test_shapely_geometry_input(self) -> None:
        """Test parsing with Shapely geometry objects."""
        feature = SAMPLE_FLAT_FEATURE.copy()
        geometry_dict = feature["geometry"]
        assert isinstance(geometry_dict, dict)
        expected_coords = geometry_dict["coordinates"]
        feature["geometry"] = Point(expected_coords[0], expected_coords[1])

        result = parse_feature(feature, Place, mode="python")
        assert result is not None
        assert "geometry" in result

        # Check that geometry is properly parsed
        geometry = result["geometry"]
        assert hasattr(geometry, "to_geo_json")
        geo_json = geometry.to_geo_json()
        assert geo_json["type"] == "Point"
        assert list(geo_json["coordinates"]) == expected_coords

    def test_wkb_geometry_input(self) -> None:
        """Test parsing with WKB bytes."""
        feature = SAMPLE_FLAT_FEATURE.copy()
        geometry_dict = feature["geometry"]
        assert isinstance(geometry_dict, dict)
        expected_coords = geometry_dict["coordinates"]
        point = Point(expected_coords[0], expected_coords[1])
        feature["geometry"] = point.wkb

        result = parse_feature(feature, Place, mode="python")
        assert result is not None
        assert "geometry" in result

        # Check that geometry is properly parsed
        geometry = result["geometry"]
        assert hasattr(geometry, "to_geo_json")
        geo_json = geometry.to_geo_json()
        assert geo_json["type"] == "Point"
        assert list(geo_json["coordinates"]) == expected_coords

    def test_wkt_geometry_input(self) -> None:
        """Test parsing with WKT strings."""
        feature = SAMPLE_FLAT_FEATURE.copy()
        geometry_dict = feature["geometry"]
        assert isinstance(geometry_dict, dict)
        expected_coords = geometry_dict["coordinates"]
        point = Point(expected_coords[0], expected_coords[1])
        feature["geometry"] = point.wkt

        result = parse_feature(feature, Place, mode="python")
        assert result is not None
        assert "geometry" in result

        # Check that geometry is properly parsed
        geometry = result["geometry"]
        assert hasattr(geometry, "to_geo_json")
        geo_json = geometry.to_geo_json()
        assert geo_json["type"] == "Point"
        assert list(geo_json["coordinates"]) == expected_coords

    def test_different_geometry_types(self) -> None:
        """Test parsing with different Point geometry coordinates."""
        base_feature = {
            "id": "test-geom",
            "theme": "places",
            "type": "place",
            "version": 1,
            "names": {"primary": "Test"},
            "categories": {"primary": "restaurant"},
        }

        # Test different Point coordinates
        test_cases = [
            [-122.4, 37.7],
            [0.0, 0.0],
            [180.0, -90.0],
            [-180.0, 90.0],
        ]

        for point_coords in test_cases:
            point_feature = base_feature.copy()
            point_feature["geometry"] = Point(point_coords[0], point_coords[1])
            result = parse_feature(point_feature, Place, mode="python")
            assert result is not None
            geometry = result["geometry"]
            assert hasattr(geometry, "to_geo_json")
            geo_json = geometry.to_geo_json()
            assert geo_json["type"] == "Point"
            assert list(geo_json["coordinates"]) == point_coords

    def test_invalid_geometry_formats_fail(self) -> None:
        """Test that invalid geometry formats are rejected."""
        feature = SAMPLE_FLAT_FEATURE.copy()

        # Invalid GeoJSON geometry
        feature["geometry"] = {"type": "InvalidType", "coordinates": [1, 2]}
        with pytest.raises(ValueError):
            parse_feature(feature, Place)

        # Invalid WKT
        feature["geometry"] = "INVALID WKT STRING"
        with pytest.raises(ValueError):
            parse_feature(feature, Place)
