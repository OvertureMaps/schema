"""Tests for CLI commands (validate, list-types, json-schema)."""

import json
from io import StringIO

import pytest
from click.testing import CliRunner
from conftest import build_feature
from overture.schema.cli.commands import cli


class TestListTypesCommand:
    """Tests for the list-types command."""

    def test_list_types_command(self, cli_runner: CliRunner) -> None:
        """Test the list-types command."""
        result = cli_runner.invoke(cli, ["list-types"])
        assert result.exit_code == 0
        # Should show theme names
        assert "BUILDINGS" in result.output or "buildings" in result.output
        # Should show type names
        assert "building" in result.output

    def test_list_types_command_help(self, cli_runner: CliRunner) -> None:
        """Test list-types command help."""
        result = cli_runner.invoke(cli, ["list-types", "--help"])
        assert result.exit_code == 0
        assert "list-types" in result.output.lower()


class TestJsonSchemaCommand:
    """Tests for the json-schema command."""

    def test_json_schema_generates_valid_output(self, cli_runner: CliRunner) -> None:
        """Test that json-schema command generates valid JSON."""
        result = cli_runner.invoke(cli, ["json-schema", "--theme", "buildings"])
        assert result.exit_code == 0

        # Should be valid JSON
        schema = json.loads(result.output)
        assert isinstance(schema, dict)


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_success_message_from_file(
        self, cli_runner: CliRunner, building_feature_yaml: str
    ) -> None:
        """Test that validation shows success message for valid file input."""
        result = cli_runner.invoke(cli, ["validate", building_feature_yaml])
        assert result.exit_code == 0
        assert "Successfully validated" in result.output

    def test_validate_flat_format_input(self, cli_runner: CliRunner) -> None:
        """Test that validation works with flat (non-GeoJSON) format."""
        flat_feature = build_feature(geojson_format=False)
        flat_json = json.dumps(flat_feature)
        result = cli_runner.invoke(
            cli, ["validate", "--theme", "buildings", "-"], input=flat_json
        )
        assert result.exit_code == 0
        assert "Successfully validated <stdin>" in result.output

    def test_validate_error_message_format(
        self,
        cli_runner: CliRunner,
        missing_id_yaml_content: str,
        stderr_buffer: StringIO,
    ) -> None:
        """Test that validation errors are formatted correctly."""
        result = cli_runner.invoke(
            cli, ["validate", "-"], input=missing_id_yaml_content
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        assert "Validation Failed" in stderr_output
        # Should show the field path
        assert "id" in stderr_output.lower()

    def test_validate_error_filters_tagged_union_from_path(
        self,
        cli_runner: CliRunner,
        missing_id_yaml_content: str,
        stderr_buffer: StringIO,
    ) -> None:
        """Test that validation error paths don't show internal tagged-union markers."""
        result = cli_runner.invoke(
            cli, ["validate", "-"], input=missing_id_yaml_content
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()

        # Should NOT show Pydantic's internal union markers in the path
        assert "tagged-union" not in stderr_output.lower()
        assert "union[" not in stderr_output.lower()

        # Should show the actual field name
        assert "id" in stderr_output.lower()

    def test_validate_error_with_invalid_type_value(
        self, cli_runner: CliRunner
    ) -> None:
        """Test validation error for invalid type value."""
        invalid_feature = build_feature(type="invalid_type")
        invalid_type_json = json.dumps(invalid_feature)
        result = cli_runner.invoke(cli, ["validate", "-"], input=invalid_type_json)
        assert result.exit_code == 1

    def test_validate_error_with_nested_field(self, cli_runner: CliRunner) -> None:
        """Test validation error message includes nested field path."""
        feature = build_feature(
            names={
                "common": [
                    {"value": "Test Building", "language": "invalid_language_code"}
                ]
            }
        )
        nested_field_json = json.dumps(feature)
        result = cli_runner.invoke(cli, ["validate", "-"], input=nested_field_json)
        assert result.exit_code == 1

    def test_validate_stdin_requires_dash_argument(
        self,
        cli_runner: CliRunner,
        building_feature_yaml_content: str,
    ) -> None:
        """Test validating from stdin requires explicit '-' argument."""
        # With dash argument - should work
        result = cli_runner.invoke(
            cli, ["validate", "-"], input=building_feature_yaml_content
        )
        assert result.exit_code == 0
        assert "Successfully validated <stdin>" in result.output

        # Without dash argument - should show help/usage
        result = cli_runner.invoke(
            cli, ["validate"], input=building_feature_yaml_content
        )
        assert result.exit_code == 2  # Usage error
        assert "Missing argument" in result.output or "Usage:" in result.output

    @pytest.mark.parametrize(
        "has_error,expected_exit_code,check_index",
        [
            pytest.param(False, 0, False, id="success"),
            pytest.param(True, 1, True, id="with_error"),
        ],
    )
    def test_validate_feature_list(
        self,
        cli_runner: CliRunner,
        stderr_buffer: StringIO,
        has_error: bool,
        expected_exit_code: int,
        check_index: bool,
    ) -> None:
        """Test validation of a list of features (success and error cases)."""
        feature1 = build_feature(id="test1")
        feature2_id = None if has_error else "test2"
        feature2 = build_feature(
            id=feature2_id, coordinates=[[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]
        )
        feature_list_json = json.dumps([feature1, feature2])
        result = cli_runner.invoke(cli, ["validate", "-"], input=feature_list_json)
        assert result.exit_code == expected_exit_code

        if check_index:
            stderr_output = stderr_buffer.getvalue()
            # Should show list index for the second feature
            assert "[1]" in stderr_output or "1" in stderr_output
        else:
            assert "Successfully validated <stdin>" in result.output

    @pytest.mark.parametrize(
        "first_feature_valid,second_feature_valid,expected_exit_code",
        [
            pytest.param(True, True, 0, id="both_valid"),
            pytest.param(True, False, 1, id="second_invalid"),
            pytest.param(False, False, 1, id="both_invalid"),
        ],
    )
    def test_validate_feature_collection(
        self,
        cli_runner: CliRunner,
        stderr_buffer: StringIO,
        first_feature_valid: bool,
        second_feature_valid: bool,
        expected_exit_code: int,
    ) -> None:
        """Test validation of a GeoJSON FeatureCollection with various validity states."""
        feature1 = build_feature(id="test1" if first_feature_valid else None)
        feature2 = build_feature(
            id="test2" if second_feature_valid else None,
            coordinates=[[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]],
        )
        feature_collection = {
            "type": "FeatureCollection",
            "features": [feature1, feature2],
        }
        result = cli_runner.invoke(
            cli, ["validate", "-"], input=json.dumps(feature_collection)
        )
        assert result.exit_code == expected_exit_code

        if expected_exit_code == 0:
            assert "Successfully validated <stdin>" in result.output
        else:
            stderr_output = stderr_buffer.getvalue()
            # Should show errors for list items
            if not first_feature_valid or not second_feature_valid:
                assert "[0]" in stderr_output or "[1]" in stderr_output

    def test_validate_with_nonexistent_filters_raises_error(
        self,
        cli_runner: CliRunner,
        building_feature_yaml_content: str,
    ) -> None:
        """Test that validation with filters matching no models raises a clear error."""
        # Try to validate with a nonexistent theme
        result = cli_runner.invoke(
            cli,
            ["validate", "--theme", "nonexistent_theme", "-"],
            input=building_feature_yaml_content,
        )
        # UsageError exits with code 2
        assert result.exit_code == 2
        assert "No models found matching the specified criteria" in result.output

    def test_validate_with_nonexistent_type_raises_error(
        self,
        cli_runner: CliRunner,
        building_feature_yaml_content: str,
    ) -> None:
        """Test that validation with nonexistent type raises a clear error."""
        # Try to validate with a nonexistent type
        result = cli_runner.invoke(
            cli,
            ["validate", "--type", "nonexistent_type", "-"],
            input=building_feature_yaml_content,
        )
        # UsageError exits with code 2
        assert result.exit_code == 2
        assert "No models found matching the specified criteria" in result.output

    def test_validate_with_valid_theme_invalid_type_raises_error(
        self,
        cli_runner: CliRunner,
        building_feature_yaml_content: str,
    ) -> None:
        """Test that validation with valid theme but invalid type raises an error."""
        # Try to validate buildings theme with a type that doesn't exist in that theme
        result = cli_runner.invoke(
            cli,
            ["validate", "--theme", "buildings", "--type", "segment", "-"],
            input=building_feature_yaml_content,
        )
        # UsageError exits with code 2
        assert result.exit_code == 2
        assert "No models found matching the specified criteria" in result.output


class TestShowFieldOption:
    """Tests for the --show-field option in validate command."""

    def test_show_field_displays_in_header_on_error(
        self, cli_runner: CliRunner, stderr_buffer: StringIO
    ) -> None:
        """Test that --show-field displays field value in error header."""
        # Create invalid feature with missing required field, but with id
        feature = build_feature(id="abc123", version=None)
        result = cli_runner.invoke(
            cli, ["validate", "--show-field", "id", "-"], input=json.dumps(feature)
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        # Header should include id value
        assert "id=abc123" in stderr_output

    def test_show_field_displays_in_context(
        self, cli_runner: CliRunner, stderr_buffer: StringIO
    ) -> None:
        """Test that --show-field pins field in context display."""
        # Create invalid feature with error far from id field
        feature = build_feature(id="test123", version=None)
        result = cli_runner.invoke(
            cli, ["validate", "--show-field", "id", "-"], input=json.dumps(feature)
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        # Should show id field in context even if error is elsewhere
        assert "id" in stderr_output
        assert "test123" in stderr_output

    def test_show_multiple_fields(
        self, cli_runner: CliRunner, stderr_buffer: StringIO
    ) -> None:
        """Test that multiple --show-field options work together."""
        feature = build_feature(id="xyz789", version=1, theme=None)
        result = cli_runner.invoke(
            cli,
            ["validate", "--show-field", "id", "--show-field", "version", "-"],
            input=json.dumps(feature),
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        # Header should include both field values
        assert "id=xyz789" in stderr_output
        assert "version=1" in stderr_output

    def test_show_field_with_missing_field(
        self, cli_runner: CliRunner, stderr_buffer: StringIO
    ) -> None:
        """Test that --show-field shows <missing> for non-existent fields."""
        feature = build_feature(version=None)
        # Don't include 'custom_field' in the feature
        result = cli_runner.invoke(
            cli,
            ["validate", "--show-field", "custom_field", "-"],
            input=json.dumps(feature),
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        # Should show <missing> for the non-existent field
        assert "custom_field" in stderr_output
        assert "<missing>" in stderr_output

    def test_show_field_truncates_long_values(
        self, cli_runner: CliRunner, stderr_buffer: StringIO
    ) -> None:
        """Test that long field values are truncated in header."""
        long_id = "x" * 100  # Very long ID
        feature = build_feature(id=long_id, version=None)
        result = cli_runner.invoke(
            cli, ["validate", "--show-field", "id", "-"], input=json.dumps(feature)
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        # Should show truncated value in header (with ellipsis)
        assert "id=" in stderr_output
        assert "..." in stderr_output
        # Should not show the full 100 character string
        assert long_id not in stderr_output

    def test_show_field_in_collection(
        self, cli_runner: CliRunner, stderr_buffer: StringIO
    ) -> None:
        """Test that --show-field works with feature collections."""
        feature1 = build_feature(id="first", version=None)
        feature2 = build_feature(id="second", theme=None)
        result = cli_runner.invoke(
            cli,
            ["validate", "--show-field", "id", "-"],
            input=json.dumps([feature1, feature2]),
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        # Should show id for both features
        assert "id=first" in stderr_output or "first" in stderr_output
        assert "id=second" in stderr_output or "second" in stderr_output
