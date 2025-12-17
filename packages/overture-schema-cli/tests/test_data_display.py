"""Tests for data display functionality in verbose error output."""

from io import StringIO

from conftest import build_feature
from overture.schema.cli.data_display import (
    create_feature_display,
    extract_feature_data,
    format_field_value,
    select_context_fields,
)
from rich.console import Console


class TestExtractFeatureData:
    """Test extracting flattened feature data from various input formats."""

    def test_extract_from_single_feature(self) -> None:
        """Should extract data from a single feature dict."""
        data = build_feature(
            id="test-1",
            theme="places",
            type="place",
            geometry_type="Point",
            coordinates=[1.0, 2.0],
        )
        result = extract_feature_data(data, item_index=None)

        # Should flatten properties to top level
        assert result["id"] == "test-1"
        assert result["theme"] == "places"
        assert result["type"] == "place"
        assert result["geometry"]["type"] == "Point"

    def test_extract_from_list_by_index(self) -> None:
        """Should extract specific feature from a list."""
        data = [
            build_feature(id="first", theme="places", type="place"),
            build_feature(id="second", theme="buildings", type="building"),
        ]
        result = extract_feature_data(data, item_index=1)

        assert result["id"] == "second"
        assert result["theme"] == "buildings"

    def test_extract_from_feature_collection(self) -> None:
        """Should extract feature from GeoJSON FeatureCollection."""
        data = {
            "type": "FeatureCollection",
            "features": [
                build_feature(id="first", theme="places", type="place"),
            ],
        }
        result = extract_feature_data(data, item_index=0)

        assert result["id"] == "first"
        assert result["theme"] == "places"

    def test_extract_returns_empty_dict_on_invalid_index(self) -> None:
        """Should return empty dict for out-of-bounds index."""
        data = [build_feature(id="first")]
        result = extract_feature_data(data, item_index=10)
        assert result == {}

    def test_extract_returns_empty_dict_on_negative_index(self) -> None:
        """Should return empty dict for negative index."""
        data = [build_feature(id="first")]
        result = extract_feature_data(data, item_index=-1)
        assert result == {}

    def test_extract_returns_empty_dict_on_malformed_collection(self) -> None:
        """Should return empty dict for malformed FeatureCollection."""
        data = {"type": "FeatureCollection"}  # Missing 'features' key
        result = extract_feature_data(data, item_index=0)
        assert result == {}

    def test_extract_returns_empty_dict_on_invalid_type(self) -> None:
        """Should return empty dict for invalid input type."""
        result = extract_feature_data("not a dict or list", item_index=None)
        assert result == {}

        result = extract_feature_data(123, item_index=None)
        assert result == {}


class TestSelectContextFields:
    """Test selecting relevant fields for display."""

    def test_selects_error_field_with_context(self) -> None:
        """Should select error field and neighboring fields."""
        feature = build_feature(
            id="test-1", theme="places", type="place", geojson_format=False
        )
        # Error at "theme" field
        selected = select_context_fields(feature, error_path=["theme"], context_size=1)

        # Should include field before (geometry), error field (theme), and field after (type)
        assert "geometry" in selected
        assert "theme" in selected
        assert "type" in selected
        # Should not include fields further away
        assert "id" not in selected
        assert "version" not in selected

    def test_handles_nested_error_path(self) -> None:
        """Should select parent object when error is nested."""
        feature = build_feature(
            id="test-1",
            theme="places",
            type="place",
            geometry_type="InvalidType",
            coordinates=[1.0, 2.0],
            geojson_format=False,
        )
        # Error at "geometry.type"
        selected = select_context_fields(
            feature, error_path=["geometry", "type"], context_size=1
        )

        # Should include entire geometry object and neighbors
        assert "geometry" in selected
        assert selected["geometry"]["type"] == "InvalidType"

    def test_handles_missing_field(self) -> None:
        """Should handle error for field that doesn't exist."""
        feature = build_feature(
            id="test-1", theme="places", type="place", geojson_format=False
        )
        # Error for missing "operating_status"
        selected = select_context_fields(
            feature, error_path=["operating_status"], context_size=1
        )

        # Should select some neighboring fields (exact fields depend on position)
        assert len(selected) > 1  # Not just the missing field
        # Missing field should be included as None or similar marker
        assert "operating_status" in selected

    def test_context_size_zero_shows_only_error(self) -> None:
        """Should show only error field when context_size=0."""
        feature = build_feature(
            id="test-1", theme="places", type="place", geojson_format=False
        )
        selected = select_context_fields(feature, error_path=["theme"], context_size=0)

        assert "theme" in selected
        assert len(selected) == 1

    def test_missing_field_included_as_none(self) -> None:
        """Missing field should be included with None value."""
        feature = build_feature(
            id="test-1", theme="places", type="place", geojson_format=False
        )
        selected = select_context_fields(
            feature, error_path=["operating_status"], context_size=1
        )

        # Missing field should be present in selected dict
        assert "operating_status" in selected
        # With None as the value
        assert selected["operating_status"] is None

    def test_handles_array_in_error_path(self) -> None:
        """Should handle error paths with array indices by showing nested path."""
        feature = build_feature(
            id="test-1", theme="places", type="place", geojson_format=False
        )
        # Add sources array
        feature["sources"] = [
            {"dataset": "osm", "record_id": "123"},
            {"dataset": "osm", "record_id": None},  # Error here
        ]

        # Error path includes array index: ["sources", 1, "record_id"]
        selected = select_context_fields(
            feature, error_path=["sources", 1, "record_id"], context_size=1
        )

        # Should include nested path with array index: sources[1].record_id
        assert "sources[1].record_id" in selected
        assert selected["sources[1].record_id"] is None

    def test_context_at_feature_boundaries(self) -> None:
        """Context window should work at start and end of feature."""
        feature = build_feature(
            id="test-1", theme="places", type="place", geojson_format=False
        )
        fields = list(feature.keys())

        # Error at first field
        selected = select_context_fields(
            feature, error_path=[fields[0]], context_size=2
        )
        assert fields[0] in selected

        # Error at last field
        selected = select_context_fields(
            feature, error_path=[fields[-1]], context_size=2
        )
        assert fields[-1] in selected

    def test_nested_elision_in_array_items(self) -> None:
        """Should include elision markers for skipped fields within array items."""
        feature = build_feature(
            id="test-1", theme="buildings", type="building", geojson_format=False
        )
        # Add sources array with 3 fields each
        feature["sources"] = [
            {"property": "", "dataset": "msft", "confidence": 1.5},
            {"property": "/height", "dataset": "meta", "confidence": -0.1},
        ]

        # Error at sources[0].confidence - should select dataset and confidence
        # but NOT property (which is outside context_size=1)
        selected = select_context_fields(
            feature, error_path=["sources", 0, "confidence"], context_size=1
        )

        # Should have sources[0].dataset and sources[0].confidence
        assert "sources[0].dataset" in selected
        assert "sources[0].confidence" in selected
        # Should NOT have sources[0].property (outside context window)
        assert "sources[0].property" not in selected
        # But SHOULD have elision marker for the skipped field
        # This is the key assertion - currently failing
        nested_keys = [k for k in selected.keys() if k.startswith("sources[0]")]
        # If we're showing only partial fields from sources[0], should have elision
        if len(nested_keys) < 3:  # 3 fields total in sources[0]
            # Look for elision marker in nested context
            has_elision = any("..." in k for k in nested_keys)
            assert has_elision, f"Expected elision marker in {nested_keys}"


class TestFormatFieldValue:
    """Test formatting field values for display."""

    def test_formats_simple_values(self) -> None:
        """Should format primitive values as strings."""
        assert format_field_value("test") == '"test"'
        assert format_field_value(42) == "42"
        assert format_field_value(True) == "True"
        assert format_field_value(None) == "<missing>"

    def test_summarizes_geometry(self) -> None:
        """Should summarize geometry objects."""
        geom = {"type": "Point", "coordinates": [1.0, 2.0]}
        result = format_field_value(geom)
        assert "Point" in result

        geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
        result = format_field_value(geom)
        assert "Polygon" in result

    def test_summarizes_nested_objects(self) -> None:
        """Should summarize nested objects."""
        obj = {"primary": "restaurant", "alternate": ["cafe", "bistro"]}
        result = format_field_value(obj)
        assert 'primary: "restaurant"' in result

    def test_truncates_long_values(self) -> None:
        """Should truncate very long values."""
        long_string = "x" * 100
        result = format_field_value(long_string, max_length=50)
        # With quotes: "xxx...xxx..." (opening quote + 50 chars + ...")
        assert len(result) <= 55  # " + 50 + ..." = 54 chars
        assert result.startswith('"')
        assert result.endswith('..."')

    def test_formats_empty_collections(self) -> None:
        """Empty collections should have clear representation."""
        assert format_field_value([]) == "[]"
        assert format_field_value({}) == "{}"

    def test_formats_array_values(self) -> None:
        """Should format arrays appropriately."""
        arr = [{"dataset": "osm"}, {"dataset": "msft"}]
        result = format_field_value(arr)
        # Should indicate it's an array (exact format TBD)
        assert result  # Not empty
        # Could be "[...2 items]" or similar in future


class TestCreateFeatureDisplay:
    """Test creating Rich Table display."""

    def test_creates_panel_with_table(self) -> None:
        """Should create a Panel wrapping a borderless table."""
        fields = {"id": "test-1", "theme": "places", "type": "place"}
        errors: list[tuple[list[str | int], str]] = [(["theme"], "Field required")]

        result = create_feature_display(fields, errors)

        # Verify result is a Panel
        from rich.panel import Panel

        assert isinstance(result, Panel)

    def test_includes_error_annotation(self) -> None:
        """Should annotate error field with arrow and message."""
        fields = {"id": "test-1", "theme": None, "type": "place"}
        errors: list[tuple[list[str | int], str]] = [(["theme"], "Field required")]

        panel = create_feature_display(fields, errors)

        # Render and check that error annotation is present
        buffer = StringIO()
        test_console = Console(file=buffer, force_terminal=False, width=120)
        test_console.print(panel)
        output = buffer.getvalue()

        assert "Field required" in output
        assert "←" in output

    def test_handles_nested_error_path(self) -> None:
        """Should format nested paths correctly."""
        fields = {
            "id": "test-1",
            "geometry": {"type": "InvalidType", "coordinates": []},
        }
        errors: list[tuple[list[str | int], str]] = [
            (["geometry", "type"], "Invalid geometry type")
        ]

        panel = create_feature_display(fields, errors)

        # Render and verify nested path is formatted correctly
        buffer = StringIO()
        test_console = Console(file=buffer, force_terminal=False, width=120)
        test_console.print(panel)
        output = buffer.getvalue()

        assert "geometry" in output
        assert "Invalid geometry type" in output

    def test_table_contains_field_values(self) -> None:
        """Verify panel contains actual field values."""
        fields = {"id": "test-123", "theme": "buildings", "type": "building"}
        errors: list[tuple[list[str | int], str]] = [(["theme"], "Field required")]

        panel = create_feature_display(fields, errors)

        # Render panel to string to inspect content
        buffer = StringIO()
        test_console = Console(file=buffer, force_terminal=False, width=120)
        test_console.print(panel)
        output = buffer.getvalue()

        # Verify field values are present (with quotes for strings)
        assert "test-123" in output
        assert "buildings" in output
        assert "building" in output

    def test_error_annotation_includes_message(self) -> None:
        """Error annotation should include the error message and arrow."""
        fields = {"theme": None}
        errors: list[tuple[list[str | int], str]] = [(["theme"], "Field required")]

        panel = create_feature_display(fields, errors)

        # Render panel to check content
        buffer = StringIO()
        test_console = Console(file=buffer, force_terminal=False, width=120)
        test_console.print(panel)
        output = buffer.getvalue()

        # Verify error message and arrow are present
        assert "Field required" in output
        assert "←" in output  # Left arrow indicator

    def test_table_preserves_field_order(self) -> None:
        """Panel should preserve insertion order of fields."""
        # Use ordered fields
        fields = {"first": "a", "second": "b", "third": "c"}
        errors: list[tuple[list[str | int], str]] = [(["second"], "Error")]

        panel = create_feature_display(fields, errors)

        # Render and check order
        buffer = StringIO()
        test_console = Console(file=buffer, force_terminal=False, width=120)
        test_console.print(panel)
        output = buffer.getvalue()

        # Check that fields appear in order (first before second before third)
        first_pos = output.find("first")
        second_pos = output.find("second")
        third_pos = output.find("third")

        assert first_pos < second_pos < third_pos


class TestIntegration:
    """Integration tests for full error display flow."""

    def test_complete_flow_missing_field(self) -> None:
        """Test complete flow for missing field error."""
        # Simulate feature collection with error at [1].id
        data = {
            "type": "FeatureCollection",
            "features": [
                build_feature(id="valid-1", theme="places", type="place"),
                build_feature(
                    id=None, theme="places", type="place"
                ),  # Missing id (None will omit it)
            ],
        }

        # Extract feature
        feature = extract_feature_data(data, item_index=1)
        assert feature.get("id") is None

        # Select fields
        selected = select_context_fields(feature, error_path=["id"], context_size=1)
        assert "id" in selected

        # Create display
        panel = create_feature_display(selected, [(["id"], "Field required")])
        assert panel is not None

    def test_complete_flow_invalid_value(self) -> None:
        """Test complete flow for invalid value error."""
        data = build_feature(
            id="test-1",
            theme="buildings",
            type="building",
            geometry_type="InvalidGeometryType",
            coordinates=[],
        )

        # Extract and process
        feature = extract_feature_data(data, item_index=None)
        selected = select_context_fields(
            feature, error_path=["geometry", "type"], context_size=1
        )

        # Create display
        panel = create_feature_display(
            selected, [(["geometry", "type"], "Invalid geometry type")]
        )
        assert panel is not None


class TestSelectContextFieldsBugs:
    """Regression tests for select_context_fields bugs."""

    def test_missing_field_in_nested_array_generates_nested_path(self) -> None:
        """Bug 1: Missing field errors in nested arrays should generate nested path keys.

        When a field is missing (like license_type in datasets[0]), navigation fails
        because the field doesn't exist. The function should still generate nested
        path keys like 'datasets[0].license_type' so errors can be matched and displayed.
        """
        # Simulate a Sources-like structure with datasets array
        feature = {
            "datasets": [
                {
                    "source_name": "Test Source",
                    "data_url": "https://example.com",
                    # license_type is MISSING - this is the error
                },
                {
                    "source_name": "Another Source",
                    "license_type": "CC-BY-4.0",
                },
            ],
            "license_priority": {},
        }

        # Error path for missing license_type in datasets[0]
        selected = select_context_fields(
            feature, error_path=["datasets", 0, "license_type"], context_size=1
        )

        # Should include nested path key for the missing field
        assert "datasets[0].license_type" in selected
        # The value should be None since the field is missing
        assert selected["datasets[0].license_type"] is None

    def test_array_index_as_target_generates_parent_context(self) -> None:
        """Bug 2: Array index errors should not return empty context.

        When the last element of an error path is an array index (integer),
        the function was returning {} because it expected a string field name.
        It should handle this case and show context around the array item.
        """
        # Simulate a structure where an array item itself has an error
        feature = {
            "datasets": [
                {
                    "data_download_url": ["invalid-url"],  # Error at index 0
                },
            ],
            "license_priority": {},
        }

        # Error path ends with array index: data_download_url[0] is invalid
        selected = select_context_fields(
            feature, error_path=["datasets", 0, "data_download_url", 0], context_size=1
        )

        # Should NOT return empty dict
        assert selected != {}
        # Should include context showing the problematic array item
        # Either as nested path or parent array
        has_data_download_url = any(
            "data_download_url" in key for key in selected.keys()
        )
        assert has_data_download_url, (
            f"Expected data_download_url context in {selected}"
        )

    def test_deeply_nested_missing_field(self) -> None:
        """Missing field deep in nested structure should still generate path."""
        feature = {
            "items": [
                {
                    "nested": {
                        "existing_field": "value",
                        # missing_field is not here
                    },
                },
            ],
        }

        selected = select_context_fields(
            feature, error_path=["items", 0, "nested", "missing_field"], context_size=1
        )

        # Should include the missing field with nested path
        assert "items[0].nested.missing_field" in selected
        assert selected["items[0].nested.missing_field"] is None

    def test_array_index_error_with_context(self) -> None:
        """Array index error should show surrounding array items."""
        feature = {
            "values": ["good", "bad", "good"],
        }

        # Error at values[1]
        selected = select_context_fields(
            feature, error_path=["values", 1], context_size=1
        )

        # Should not be empty and should reference the values array
        assert selected != {}
        assert "values" in selected or any("values" in k for k in selected.keys())
