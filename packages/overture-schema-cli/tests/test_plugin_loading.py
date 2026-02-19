"""Tests for CLI plugin loading via entry points."""

from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner
from overture.schema.cli.commands import cli, load_plugins


class TestLoadPlugins:
    """Tests for the load_plugins function."""

    def test_discovers_and_registers_entry_points(self) -> None:
        """Plugins from entry points are registered as subcommands."""
        test_cmd = click.Command("test-plugin", callback=lambda: None)
        mock_ep = MagicMock()
        mock_ep.name = "test-plugin"
        mock_ep.load.return_value = test_cmd

        group = click.Group()
        with patch("overture.schema.cli.commands.entry_points", return_value=[mock_ep]):
            load_plugins(group)

        assert "test-plugin" in group.commands

    def test_broken_plugin_warns_and_skips(self, capsys: pytest.CaptureFixture) -> None:
        """Broken entry points emit a warning and don't prevent CLI startup."""
        mock_ep = MagicMock()
        mock_ep.name = "broken-plugin"
        mock_ep.load.side_effect = ImportError("missing dependency")

        group = click.Group()
        with patch("overture.schema.cli.commands.entry_points", return_value=[mock_ep]):
            load_plugins(group)

        assert "broken-plugin" not in group.commands
        captured = capsys.readouterr()
        assert "broken-plugin" in captured.err
        assert "missing dependency" in captured.err

    def test_plugin_does_not_clobber_builtin(self) -> None:
        """Plugin names that collide with built-ins don't replace the built-in."""
        builtin_cmd = click.Command(
            "list-types", callback=lambda: click.echo("builtin")
        )
        plugin_cmd = click.Command("list-types", callback=lambda: click.echo("plugin"))

        group = click.Group()
        group.add_command(builtin_cmd, "list-types")

        mock_ep = MagicMock()
        mock_ep.name = "list-types"
        mock_ep.load.return_value = plugin_cmd

        with patch("overture.schema.cli.commands.entry_points", return_value=[mock_ep]):
            load_plugins(group)

        assert group.commands["list-types"] is builtin_cmd


class TestPluginLoadingIntegration:
    """Integration tests for plugin loading with the actual CLI group."""

    def test_builtin_commands_work_without_plugins(self) -> None:
        """list-types and json-schema work when no plugins are installed."""
        runner = CliRunner()
        result = runner.invoke(cli, ["list-types"])
        assert result.exit_code == 0

    def test_help_lists_builtin_commands(self) -> None:
        """--help shows built-in commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "list-types" in result.output
        assert "json-schema" in result.output
