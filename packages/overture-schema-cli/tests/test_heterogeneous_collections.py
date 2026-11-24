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
        names={"primary": "Place missing required field"},
    )
    return json.dumps([building1, building2, building3, place])


def _base_water_with_bad_fields(count: int) -> dict:
    """Build a base water with `subtype: water` and *count* invalid fields."""
    water = build_feature(
        theme="base", type="water", geometry_type="LineString", subtype="water"
    )
    invalid = [
        ("class", "not-a-class"),
        ("level", "x"),
        ("is_salt", "q"),
        ("is_intermittent", "q"),
    ]
    water["properties"].update(invalid[:count])
    return water


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


class TestSharedDiscriminatorValue:
    """A value two nested unions share names a different type in each.

    Base `water` is discriminated on `type`, and transportation's water segment on
    `subtype`; both take the value "water".
    """

    @pytest.mark.parametrize(
        "selection",
        [
            pytest.param([], id="every_type"),
            # Three base types and the three segment subtypes: the feature union
            # and the segment union then have validators of the same shape.
            pytest.param(
                [
                    *("--type", "water"),
                    *("--type", "land"),
                    *("--type", "infrastructure"),
                    *("--type", "segment"),
                ],
                id="unions_of_one_shape",
            ),
        ],
    )
    def test_items_typed_by_their_own_union(
        self, cli_runner: CliRunner, stderr_buffer: StringIO, selection: list[str]
    ) -> None:
        water = build_feature(
            id="water-1",
            theme="base",
            type="water",
            geometry_type="LineString",
            subtype="river",
        )
        water["properties"]["class"] = "not-a-class"
        water_segment = build_feature(
            id="segment-1",
            theme="transportation",
            type="segment",
            geometry_type="LineString",
            version=-1,
            subtype="water",
            connectors=[{"connector_id": "a", "at": 0}, {"connector_id": "b", "at": 1}],
        )
        result = cli_runner.invoke(
            cli,
            ["validate", *selection, "-"],
            input=json.dumps([water, water_segment]),
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        assert "[0] (Water)" in stderr_output
        assert "[1] (WaterSegment)" in stderr_output
        # Item 0's only error is its class; the water segment's complaints about it
        # (theme, type, connectors) belong to a type it is not.
        item0 = stderr_output.split("[1] (WaterSegment)")[0]
        assert "not-a-class" in item0
        assert "Field required" not in item0
        assert "Input should be 'segment'" not in item0

    def test_both_types_are_best_fit_candidates(
        self, cli_runner: CliRunner, stderr_buffer: StringIO
    ) -> None:
        # With neither `type` nor `subtype`, no union can select a branch, so the
        # item is re-validated against every candidate model.
        water = build_feature(id="water-1", theme="base", geometry_type="LineString")
        water["properties"]["class"] = "river"
        del water["properties"]["type"]
        result = cli_runner.invoke(cli, ["validate", "-"], input=json.dumps([water]))
        assert result.exit_code == 1

        assert "[0] (Water)" in stderr_buffer.getvalue()

    @pytest.mark.parametrize("bad_fields", [1, 3, 4])
    def test_a_base_water_keeps_only_its_own_errors(
        self, cli_runner: CliRunner, stderr_buffer: StringIO, bad_fields: int
    ) -> None:
        # The water segment always has three errors (theme, type, connectors), but
        # it rejects the item's theme and type, so it loses however many of its
        # own fields the base water gets wrong.
        water = _base_water_with_bad_fields(bad_fields)
        result = cli_runner.invoke(cli, ["validate", "-"], input=json.dumps(water))
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        assert "not-a-class" in stderr_output
        assert "Ambiguous" not in stderr_output
        assert "Field required" not in stderr_output
        assert "Input should be 'segment'" not in stderr_output

    def test_a_base_water_in_a_mixed_list_is_titled_by_its_own_type(
        self, cli_runner: CliRunner, stderr_buffer: StringIO
    ) -> None:
        building = build_feature(id="building-1", theme="buildings", type="building")
        building["properties"]["height"] = -1
        water = _base_water_with_bad_fields(4)
        result = cli_runner.invoke(
            cli, ["validate", "-"], input=json.dumps([building, water])
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        assert "[0] (Building)" in stderr_output
        assert "[1] (Water)" in stderr_output
        assert "WaterSegment" not in stderr_output
        assert "Input should be 'segment'" not in stderr_output


class TestSelectionOfOneTypeAndSegment:
    """A lone selected type is validated as a plain model, not a tagged-union arm."""

    # Without connectors the road branch has as many errors as the connector branch
    # it is validated against too; the connector branch rejects its type and loses.
    @pytest.mark.parametrize("with_connectors", [True, False])
    def test_every_item_keeps_its_errors(
        self, cli_runner: CliRunner, stderr_buffer: StringIO, with_connectors: bool
    ) -> None:
        connector = build_feature(
            id="connector-1",
            theme="transportation",
            type="connector",
            geometry_type="Point",
            version=-1,
        )
        road = build_feature(
            id="road-1",
            theme="transportation",
            type="segment",
            geometry_type="LineString",
            subtype="road",
        )
        road["properties"]["class"] = "sidewalk"
        if with_connectors:
            road["properties"]["connectors"] = [
                {"connector_id": "a", "at": 0},
                {"connector_id": "b", "at": 1},
            ]
        result = cli_runner.invoke(
            cli,
            ["validate", "--tag", "overture:theme=transportation", "-"],
            input=json.dumps([connector, road]),
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        assert "[0]" in stderr_output
        assert "greater than or equal to 0" in stderr_output
        assert "[1] (RoadSegment)" in stderr_output
        assert "Input should be 'motorway'" in stderr_output
        assert "Ambiguous" not in stderr_output

    def test_a_misspelled_segment_type_stays_a_segment(
        self, cli_runner: CliRunner, stderr_buffer: StringIO
    ) -> None:
        # Base water, the plain model beside the segment union, rejects theme and
        # type; the road segment rejects only type.
        road = build_feature(
            theme="transportation",
            type="segmnt",
            geometry_type="LineString",
            subtype="road",
            connectors=[{"connector_id": "a", "at": 0}, {"connector_id": "b", "at": 1}],
        )
        road["properties"]["class"] = "motorway"
        result = cli_runner.invoke(
            cli,
            ["validate", "--type", "water", "--type", "segment", "-"],
            input=json.dumps(road),
        )
        assert result.exit_code == 1

        stderr_output = stderr_buffer.getvalue()
        assert "Input should be 'segment'" in stderr_output
        assert "Input should be 'base'" not in stderr_output
        assert "Ambiguous" not in stderr_output
