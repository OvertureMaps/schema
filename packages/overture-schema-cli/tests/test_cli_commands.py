"""Tests for CLI commands (list-types, json-schema)."""

import json

from click.testing import CliRunner
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
