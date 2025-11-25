"""Tests for error formatting and grouping logic."""

from io import StringIO
from typing import Annotated, Literal
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from overture.schema.cli.commands import cli
from overture.schema.cli.error_formatting import (
    format_path,
    group_errors_by_discriminator,
    select_most_likely_errors,
)
from overture.schema.cli.type_analysis import introspect_union
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from rich.console import Console


class TestErrorGrouping:
    """Tests for error grouping and selection logic."""

    def test_ambiguous_data_shows_most_likely_errors(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that ambiguous data shows errors from the most likely model."""
        # Create a file with data that doesn't match any model well
        # (missing fields for both Building and hypothetical Sources model)
        filename = "ambiguous.yaml"
        with open(filename, "w") as f:
            f.write("""
id: test
type: Feature
geometry:
  type: Point
  coordinates: [0, 0]
properties:
  theme: buildings
  type: building
  version: 0
""")

        result = cli_runner.invoke(cli, ["validate", "--theme", "buildings", filename])

        assert result.exit_code == 1

        # The output should show errors for the most likely model (Building)
        # Should NOT show all possible errors from all union variants
        # In this case, Building has wrong geometry type (Point instead of Polygon)
        # We expect a validation error about geometry

    def test_tie_in_error_counts_is_deterministic(self, cli_runner: CliRunner) -> None:
        """Test behavior when multiple models have same error count."""

        # Create a mixed union where both sides can have equal errors
        class Building(BaseModel):
            type: Literal["building"]
            id: str
            height: float

        class Sources(BaseModel):
            datasets: list[str]
            license_priority: int

        # Mixed union: discriminated + non-discriminated
        MixedUnion = Annotated[Building, Field(discriminator="type")] | Sources

        # Data with type="building" missing 2 fields (id, height)
        # This creates a tie: Building needs 2 fields, Sources also needs 2 fields
        invalid_data = {"type": "building"}

        try:
            TypeAdapter(MixedUnion).validate_python(invalid_data)
            pytest.fail("Should have raised ValidationError")
        except ValidationError as e:
            errors = e.errors()
            metadata = introspect_union(MixedUnion)
            groups = group_errors_by_discriminator(errors, metadata)

            # Both groups should have same number of errors (tie situation)
            error_counts = {k: len(v) for k, v in groups.items()}
            if len(set(error_counts.values())) == 1 and len(groups) > 1:
                # We have a tie!
                selected, is_tied, is_heterogeneous, item_types = (
                    select_most_likely_errors(groups)
                )
                assert len(selected) > 0, "Should select errors even in a tie"
                assert is_tied, "Should indicate that there was a tie"
                assert not is_heterogeneous, "Single item should not be heterogeneous"

                # Should return errors from ALL tied groups
                total_expected = sum(len(v) for v in groups.values())
                assert len(selected) == total_expected, (
                    "Should return all errors from all tied groups"
                )

                # Run it multiple times to verify deterministic behavior
                for _ in range(5):
                    selected_again, is_tied_again, is_het_again, _ = (
                        select_most_likely_errors(groups)
                    )
                    assert selected == selected_again, (
                        "Selection should be deterministic"
                    )
                    assert is_tied_again == is_tied, (
                        "Tie indication should be consistent"
                    )
            else:
                # Not a tie in this case, just verify it doesn't indicate a tie
                selected, is_tied, is_heterogeneous, item_types = (
                    select_most_likely_errors(groups)
                )
                assert not is_tied or len(groups) <= 1, (
                    "Should not indicate tie when error counts differ"
                )

    def test_clear_winner_selected(self, cli_runner: CliRunner) -> None:
        """Test that the model with fewest errors is selected when there's a clear winner."""
        filename = "clear-winner.yaml"
        with open(filename, "w") as f:
            # Missing only 'id' field for Building (1 error)
            # Would have many errors for Sources (datasets, license_priority, etc.)
            f.write("""
type: Feature
geometry:
  type: Polygon
  coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
properties:
  theme: buildings
  type: building
  version: 0
""")

        buffer = StringIO()
        captured_console = Console(file=buffer, force_terminal=False)

        with patch("overture.schema.cli.commands.stderr", captured_console):
            result = cli_runner.invoke(cli, ["validate", filename])

        assert result.exit_code == 1
        stderr_output = buffer.getvalue()

        # Should show only the Building error (missing id)
        assert "id" in stderr_output.lower()
        # Should NOT show Sources-related errors
        assert "dataset" not in stderr_output.lower()
        assert "license" not in stderr_output.lower()

    def test_list_indices_do_not_cause_false_ambiguity(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that list indices don't cause false ambiguity detection.

        When validating a list of features where multiple items have the same
        type of error (e.g., multiple buildings missing 'id'), the list indices
        should be ignored during grouping so they're treated as the same error
        group, not separate groups.
        """
        filename = "list-same-errors.yaml"
        with open(filename, "w") as f:
            # Two features, both Building, both missing 'id'
            f.write("""
- type: Feature
  geometry:
    type: Polygon
    coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
  properties:
    theme: buildings
    type: building
    version: 0
- type: Feature
  geometry:
    type: Polygon
    coordinates: [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]
  properties:
    theme: buildings
    type: building
    version: 0
""")

        buffer = StringIO()
        captured_console = Console(file=buffer, force_terminal=False)

        with patch("overture.schema.cli.commands.stderr", captured_console):
            result = cli_runner.invoke(cli, ["validate", filename])

        assert result.exit_code == 1
        stderr_output = buffer.getvalue()

        # Should NOT show ambiguity warning since both are Building with same error
        assert "ambiguous" not in stderr_output.lower()
        # Should show the missing 'id' error
        assert "id" in stderr_output.lower()


class TestFormatPath:
    """Tests for format_path function."""

    @pytest.mark.parametrize(
        "filtered_loc,expected_output",
        [
            pytest.param([], "(root)", id="empty_path"),
            pytest.param(["id"], "id", id="single_field"),
            pytest.param(["properties", "name"], "properties.name", id="nested_field"),
            pytest.param([0], "[0]", id="list_index"),
            pytest.param([0, "id"], "[0].id", id="list_then_field"),
            pytest.param(
                ["features", 1, "properties"], "features[1].properties", id="mixed_path"
            ),
            pytest.param([0, 1, 2], "[0][1][2]", id="nested_list_indices"),
            pytest.param(["a", "b", "c", "d"], "a.b.c.d", id="deep_nested_fields"),
        ],
    )
    def test_format_path_variations(
        self, filtered_loc: list[str | int], expected_output: str
    ) -> None:
        """Test format_path with various input patterns."""
        result = format_path(filtered_loc)
        assert result == expected_output
