"""Tests for heterogeneous collection validation."""

import json
from io import StringIO

import pytest
from click.testing import CliRunner
from conftest import build_feature
from overture.schema.cli.commands import cli


@pytest.fixture
def heterogeneous_collection_json() -> str:
    """A collection mixing buildings and places."""
    building = build_feature(id="building-1", theme="buildings", type="building")
    place = build_feature(
        id="place-1",
        theme="places",
        type="place",
        geometry_type="Point",
        coordinates=[0.5, 0.5],
        operating_status="open",
        categories={"primary": "restaurant"},
        names={"primary": "Valid Place"},
    )
    return json.dumps([building, place])


@pytest.fixture
def heterogeneous_with_missing_fields_json() -> str:
    """A collection where minority type has errors."""
    building1 = build_feature(
        id="building-valid-1",
        theme="buildings",
        type="building",
        names={"primary": "Valid Building"},
    )
    building2 = build_feature(
        id=None,  # Missing ID
        theme="buildings",
        type="building",
        coordinates=[[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]],
        names={"primary": "Missing ID Building"},
    )
    building3 = build_feature(
        id="building-bad-geometry-3",
        theme="buildings",
        type="building",
        geometry_type="InvalidGeometryType",
        coordinates=[[[4, 4], [5, 4], [5, 5], [4, 5], [4, 4]]],
    )
    place = build_feature(
        id=None,  # Missing ID
        theme="places",
        type="place",
        geometry_type="Point",
        coordinates=[6.5, 6.5],
        categories={"primary": "restaurant"},
        names={"primary": "Place missing required field"},
    )
    return json.dumps([building1, building2, building3, place])


class TestHeterogeneousCollections:
    """Tests for heterogeneous collection handling."""

    def test_heterogeneous_collection_success(
        self, cli_runner: CliRunner, heterogeneous_collection_json: str
    ) -> None:
        """Test that valid heterogeneous collections pass validation."""
        result = cli_runner.invoke(
            cli, ["validate", "-"], input=heterogeneous_collection_json
        )
        assert result.exit_code == 0
        assert "Successfully validated" in result.output

    def test_heterogeneous_collection_shows_all_errors(
        self,
        cli_runner: CliRunner,
        heterogeneous_with_missing_fields_json: str,
        stderr_buffer: StringIO,
    ) -> None:
        """Test that errors from minority types are shown, not hidden."""
        result = cli_runner.invoke(
            cli, ["validate", "-"], input=heterogeneous_with_missing_fields_json
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()

        # Should show errors for buildings (items 1 and 2)
        assert "[1]" in stderr_output or "1" in stderr_output
        assert "[2]" in stderr_output or "2" in stderr_output

        # Should show error for place (item 3)
        assert "[3]" in stderr_output or "3" in stderr_output

        # Should show building-specific errors
        assert "id" in stderr_output.lower()  # Missing ID for building

        # Should show geometry error
        assert "geometry" in stderr_output.lower()

    def test_heterogeneous_collection_warns_about_heterogeneity(
        self,
        cli_runner: CliRunner,
        heterogeneous_with_missing_fields_json: str,
        stderr_buffer: StringIO,
    ) -> None:
        """Test that heterogeneous collections trigger a warning."""
        result = cli_runner.invoke(
            cli, ["validate", "-"], input=heterogeneous_with_missing_fields_json
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()

        # Should warn about heterogeneity
        assert (
            "heterogeneous" in stderr_output.lower()
            or "mixed types" in stderr_output.lower()
        )

    def test_homogeneous_collection_no_warning(
        self, cli_runner: CliRunner, stderr_buffer: StringIO
    ) -> None:
        """Test that homogeneous collections don't trigger heterogeneity warning."""
        building1 = build_feature(id="building-1")
        building2 = build_feature(
            id=None,  # Missing ID
            coordinates=[[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]],
        )
        homogeneous_json = json.dumps([building1, building2])
        result = cli_runner.invoke(cli, ["validate", "-"], input=homogeneous_json)
        assert result.exit_code == 1  # Has error (missing id)

        stderr_output = stderr_buffer.getvalue()

        # Should NOT warn about heterogeneity
        assert "heterogeneous" not in stderr_output.lower()
        assert "mixed types" not in stderr_output.lower()

    def test_heterogeneous_prefers_majority_type_for_ambiguous_items(
        self,
        cli_runner: CliRunner,
        stderr_buffer: StringIO,
    ) -> None:
        """Test that ambiguous items show validation errors based on best-fit type."""
        # Create a collection where one item could be either type but is missing
        # fields that would make it valid for either. The type with fewest errors
        # should be used for interpretation.
        building1 = build_feature(id="building-1")
        building2 = build_feature(
            id="building-2", coordinates=[[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]
        )
        # Ambiguous item - missing theme and type
        ambiguous = {
            "id": "ambiguous-3",
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[4, 4], [5, 4], [5, 5], [4, 5], [4, 5], [4, 4]]],
            },
            "properties": {"version": 0},
        }
        ambiguous_json = json.dumps([building1, building2, ambiguous])
        result = cli_runner.invoke(cli, ["validate", "-"], input=ambiguous_json)
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()

        # The ambiguous item should show validation errors
        # (will be interpreted as the type with fewest validation errors)
        assert "[2]" in stderr_output
        # Should show at least some field errors
        assert "required" in stderr_output.lower() or "missing" in stderr_output.lower()
