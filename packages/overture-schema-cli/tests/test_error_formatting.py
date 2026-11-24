"""Tests for error formatting and grouping logic."""

from io import StringIO
from typing import Annotated, Literal, cast
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from rich.console import Console

from overture.schema.cli.commands import cli, handle_validation_error
from overture.schema.cli.error_formatting import (
    _branch_rejections,
    _is_redundant_tag_error,
    format_path,
    group_errors_by_discriminator,
    select_most_likely_errors,
)
from overture.schema.cli.type_analysis import introspect_union
from overture.schema.cli.types import ErrorLocation, ValidationErrorDict


class TestErrorGrouping:
    """Tests for error grouping and selection logic."""

    def test_sibling_tag_not_found_noise_does_not_cause_false_tie(self) -> None:
        """Sibling-branch union_tag_not_found noise must not tie with a real match.

        When validating a list against a union that mixes a tagged-union with
        another discriminated member (e.g. Segment), each item that cleanly
        matches one branch still emits a `union_tag_not_found` error from the
        sibling branch. Those empty-path `()` errors must not form a group that
        ties with the real discriminator group and raises a false "Ambiguous"
        warning. Regression guard for a union-shape invariant: error grouping
        must not depend on how many non-discriminated members the union
        contains.
        """
        # Two list items, each with one real 'missing' error (building) plus one
        # sibling-branch union_tag_not_found error (empty discriminator path).
        error_groups = cast(
            dict[ErrorLocation, list[ValidationErrorDict]],
            {
                ("building",): [
                    {
                        "loc": (0, "tagged-union[type]", "building", "id"),
                        "msg": "Field required",
                        "type": "missing",
                    },
                    {
                        "loc": (1, "tagged-union[type]", "building", "id"),
                        "msg": "Field required",
                        "type": "missing",
                    },
                ],
                (): [
                    {
                        "loc": (0, "tagged-union[subtype]"),
                        "msg": "Unable to extract tag",
                        "type": "union_tag_not_found",
                    },
                    {
                        "loc": (1, "tagged-union[subtype]"),
                        "msg": "Unable to extract tag",
                        "type": "union_tag_not_found",
                    },
                ],
            },
        )

        selected, is_tied, is_heterogeneous, _ = select_most_likely_errors(error_groups)

        assert not is_tied, "Sibling tag-not-found noise must not create a tie"
        assert not is_heterogeneous
        # Only the real building errors survive; the () noise group is dropped.
        assert len(selected) == 2
        assert all(error["type"] == "missing" for error in selected)

    def test_only_tag_not_found_errors_are_preserved(self) -> None:
        """An item whose ONLY errors are union_tag_not_found must be preserved.

        The sibling-noise suppression must not strip tag-not-found errors from a
        genuinely undiscriminatable item (one with no concrete match), otherwise
        there would be nothing to report for it.
        """
        error_groups = cast(
            dict[ErrorLocation, list[ValidationErrorDict]],
            {
                (): [
                    {
                        "loc": (2, "tagged-union[type]"),
                        "msg": "Unable to extract tag",
                        "type": "union_tag_not_found",
                    },
                ],
            },
        )

        selected, is_tied, _, _ = select_most_likely_errors(error_groups)

        assert not is_tied
        assert len(selected) == 1
        assert selected[0]["type"] == "union_tag_not_found"

    def test_genuine_tie_between_real_types_is_still_reported(self) -> None:
        """A genuine tie between two real candidate types must still be reported.

        When the union contains a plain (non-discriminated) member alongside
        discriminated types, data can match two real types equally well (each
        with the same number of concrete `missing` errors), producing
        legitimate ambiguity. The sibling-noise suppression only removes
        `union_tag_not_found` errors, so a genuine tie built from concrete
        errors must remain a tie. Guards against the suppression logic being
        broadened to swallow real ambiguity.
        """
        # Two real candidate groups, equal concrete 'missing' counts, no noise.
        error_groups = cast(
            dict[ErrorLocation, list[ValidationErrorDict]],
            {
                ("building",): [
                    {
                        "loc": ("building", "id"),
                        "msg": "Field required",
                        "type": "missing",
                    },
                    {
                        "loc": ("building", "height"),
                        "msg": "Field required",
                        "type": "missing",
                    },
                ],
                ("Sources",): [
                    {
                        "loc": ("Sources", "datasets"),
                        "msg": "Field required",
                        "type": "missing",
                    },
                    {
                        "loc": ("Sources", "license_priority"),
                        "msg": "Field required",
                        "type": "missing",
                    },
                ],
            },
        )

        selected, is_tied, is_heterogeneous, _ = select_most_likely_errors(error_groups)

        assert is_tied, "A genuine tie between two real types must still be reported"
        assert not is_heterogeneous
        # All errors from both tied groups are returned.
        assert len(selected) == 4

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

        result = cli_runner.invoke(
            cli, ["validate", "--tag", "overture:theme=buildings", filename]
        )

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


class _Water(BaseModel):
    theme: Literal["base"]
    type: Literal["water"]
    subtype: str


class _Building(BaseModel):
    theme: Literal["buildings"]
    type: Literal["building"]


class _RoadSegment(BaseModel):
    theme: Literal["transportation"]
    type: Literal["segment"]
    subtype: Literal["road"]


class _WaterSegment(BaseModel):
    theme: Literal["transportation"]
    type: Literal["segment"]
    subtype: Literal["water"]


# The shape of the feature union: types discriminated on `type` beside segments
# discriminated on `subtype`, two siblings that share the value "water".
_TypeUnion = Annotated[_Water | _Building, Field(discriminator="type")]
_SegmentUnion = Annotated[_RoadSegment | _WaterSegment, Field(discriminator="subtype")]
_FeatureUnion = _TypeUnion | _SegmentUnion
_TYPE_UNION = TypeAdapter(_TypeUnion).validator.title
_SEGMENT_UNION = TypeAdapter(_SegmentUnion).validator.title


def _select(data: dict) -> tuple[list[ValidationErrorDict], bool]:
    metadata = introspect_union(_FeatureUnion)
    with pytest.raises(ValidationError) as raised:
        TypeAdapter(_FeatureUnion).validate_python(data)
    errors = cast(list[ValidationErrorDict], raised.value.errors())
    groups = group_errors_by_discriminator(errors, metadata)
    selected, is_tied, _, _ = select_most_likely_errors(groups, metadata)
    return selected, is_tied


def _error(loc: ErrorLocation, error_type: str, **ctx: str) -> ValidationErrorDict:
    return cast(ValidationErrorDict, {"loc": loc, "type": error_type, "ctx": ctx})


class TestUnionMetadataTags:
    def test_tag_values_name_each_literal_field(self) -> None:
        metadata = introspect_union(_FeatureUnion)
        # `_Water.subtype` is a plain str, so only segments name a subtype.
        assert metadata.tag_values == {
            "theme": {"base", "buildings", "transportation"},
            "type": {"water", "building", "segment"},
            "subtype": {"road", "water"},
        }

    def test_tag_values_without_literal_fields(self) -> None:
        class Untagged(BaseModel):
            name: str

        assert introspect_union(Untagged).tag_values == {}

    @pytest.mark.parametrize(
        "union_marker,field",
        [
            pytest.param(_TYPE_UNION, "type", id="type_union"),
            pytest.param(_SEGMENT_UNION, "subtype", id="segment_union"),
            pytest.param(None, None, id="outer_union"),
            pytest.param("unknown-marker", None, id="unknown_marker"),
        ],
    )
    def test_discriminator_field_for(
        self, union_marker: str | None, field: str | None
    ) -> None:
        metadata = introspect_union(_FeatureUnion)
        assert metadata.discriminator_field_for(union_marker) == field


class TestSiblingTagErrors:
    """A tag error from a sibling union prints only when nothing states it better."""

    def test_a_misspelled_type_a_branch_corrects(self) -> None:
        # The road segment rejects only `type`, the field the type union reads.
        selected, is_tied = _select(
            {"theme": "transportation", "type": "segmnt", "subtype": "road"}
        )
        assert not is_tied
        assert [(e["type"], e["loc"][-1]) for e in selected] == [
            ("literal_error", "type")
        ]

    def test_a_misspelled_type_no_branch_accepts(self) -> None:
        # The water segment rejects `theme` too: the item is no segment.
        selected, is_tied = _select(
            {"theme": "base", "type": "watr", "subtype": "water"}
        )
        assert not is_tied
        assert [(e["type"], e.get("ctx", {}).get("tag")) for e in selected] == [
            ("union_tag_invalid", "watr")
        ]

    def test_a_valid_tag_beside_a_missing_one(self) -> None:
        # "segment" is a type some model takes; the missing subtype is the mistake.
        selected, _ = _select({"theme": "transportation", "type": "segment"})
        assert [e["type"] for e in selected] == ["union_tag_not_found"]

    @pytest.mark.parametrize(
        "rejected,redundant",
        [
            pytest.param(set(), True, id="branch_accepts_the_item"),
            pytest.param({"type"}, True, id="branch_rejects_the_same_field"),
            pytest.param({"theme", "type"}, False, id="branch_rejects_another_field"),
        ],
    )
    def test_redundant_by_branch_rejections(
        self, rejected: set[str], redundant: bool
    ) -> None:
        error = _error((_TYPE_UNION,), "union_tag_invalid", tag="segmnt")
        metadata = introspect_union(_FeatureUnion)
        assert _is_redundant_tag_error(error, [rejected], metadata) is redundant

    def test_redundant_without_metadata_only_when_a_branch_accepts(self) -> None:
        error = _error((_TYPE_UNION,), "union_tag_invalid", tag="segment")
        assert _is_redundant_tag_error(error, [set()], None)
        assert not _is_redundant_tag_error(error, [{"type"}], None)
        assert not _is_redundant_tag_error(error, [], None)

    def test_branch_rejections_count_literal_errors_on_tag_fields(self) -> None:
        error_groups: dict[ErrorLocation, list[ValidationErrorDict]] = {
            ("_RoadSegment",): [
                _error((0, _SEGMENT_UNION, "road", "type"), "literal_error"),
                _error((0, _SEGMENT_UNION, "road", "kind"), "literal_error"),
                _error(
                    (0, _SEGMENT_UNION, "road", "rules", 0, "theme"), "literal_error"
                ),
                _error((1, _SEGMENT_UNION, "road", "class"), "enum"),
            ],
            ("_WaterSegment",): [
                _error((0, _SEGMENT_UNION, "water", "theme"), "literal_error"),
                _error((0, _SEGMENT_UNION, "water", "type"), "literal_error"),
            ],
            (): [_error((0, _TYPE_UNION), "union_tag_invalid", tag="segmnt")],
        }
        rejections = _branch_rejections(error_groups, introspect_union(_FeatureUnion))
        assert rejections == {
            0: {
                ("_RoadSegment",): {"type"},
                ("_WaterSegment",): {"theme", "type"},
                (): set(),
            },
            1: {("_RoadSegment",): set()},
        }


class TestPerItemSelection:
    """Each list item's most likely group is chosen from its own errors."""

    def test_a_tie_in_one_item_leaves_another_alone(self) -> None:
        error_groups: dict[ErrorLocation, list[ValidationErrorDict]] = {
            ("Building",): [
                _error((0, "tagged-union[type]", "building", "id"), "missing"),
                _error((1, "tagged-union[type]", "building", "id"), "missing"),
            ],
            ("BuildingPart",): [
                _error((0, "tagged-union[type]", "building_part", "id"), "missing"),
                _error((1, "tagged-union[type]", "building_part", "id"), "missing"),
                _error((1, "tagged-union[type]", "building_part", "x"), "missing"),
            ],
        }
        selected, is_tied, _, _ = select_most_likely_errors(error_groups)
        assert is_tied
        assert [e["loc"] for e in selected] == [
            (0, "tagged-union[type]", "building", "id"),
            (0, "tagged-union[type]", "building_part", "id"),
            (1, "tagged-union[type]", "building", "id"),
        ]

    def test_a_small_group_in_one_item_hides_no_other_item(self) -> None:
        error_groups: dict[ErrorLocation, list[ValidationErrorDict]] = {
            ("Building",): [
                _error((0, "tagged-union[type]", "building", "id"), "missing"),
            ],
            ("BuildingPart",): [
                _error((1, "tagged-union[type]", "building_part", "id"), "missing"),
                _error((1, "tagged-union[type]", "building_part", "x"), "missing"),
            ],
        }
        selected, is_tied, _, _ = select_most_likely_errors(error_groups)
        assert not is_tied
        assert [e["loc"] for e in selected] == [
            (0, "tagged-union[type]", "building", "id"),
            (1, "tagged-union[type]", "building_part", "id"),
            (1, "tagged-union[type]", "building_part", "x"),
        ]

    def test_a_branch_that_rejects_the_items_tags_loses_to_one_with_more_errors(
        self,
    ) -> None:
        # A base water with `subtype: water` selects the water segment too, which
        # rejects its theme and type: it is not the item's type, however few
        # errors it has.
        water_errors = [
            _error((0, _TYPE_UNION, "water", field), "enum")
            for field in ("class", "level", "is_salt", "is_intermittent")
        ]
        error_groups: dict[ErrorLocation, list[ValidationErrorDict]] = {
            ("_Water",): water_errors,
            ("_WaterSegment",): [
                _error((0, _SEGMENT_UNION, "water", "theme"), "literal_error"),
                _error((0, _SEGMENT_UNION, "water", "type"), "literal_error"),
                _error((0, _SEGMENT_UNION, "water", "connectors"), "missing"),
            ],
        }
        metadata = introspect_union(_FeatureUnion)
        selected, is_tied, _, item_types = select_most_likely_errors(
            error_groups, metadata
        )
        assert not is_tied
        assert selected == water_errors
        assert item_types == {0: _Water}

    def test_item_types_name_each_items_selected_type(self) -> None:
        error_groups: dict[ErrorLocation, list[ValidationErrorDict]] = {
            ("_Building",): [
                _error((0, _TYPE_UNION, "building", "id"), "missing"),
                _error((2, _TYPE_UNION, "building", "id"), "missing"),
            ],
            ("_RoadSegment",): [
                _error((1, _SEGMENT_UNION, "road", "class"), "enum"),
                _error((2, _SEGMENT_UNION, "road", "class"), "enum"),
            ],
        }
        metadata = introspect_union(_FeatureUnion)
        _, is_tied, is_heterogeneous, item_types = select_most_likely_errors(
            error_groups, metadata
        )
        # Item 2 ties, so it has no type.
        assert is_tied
        assert is_heterogeneous
        assert item_types == {0: _Building, 1: _RoadSegment, 2: None}


class TestHandleValidationError:
    def test_a_tie_in_a_mixed_list_is_reported_as_ambiguous(self) -> None:
        data = [
            {"theme": "base", "type": "water"},
            {"theme": "buildings", "type": "segment", "subtype": "road"},
            # Water rejects the theme, a road segment the type: a tie.
            {"theme": "transportation", "type": "water", "subtype": "road"},
        ]
        with pytest.raises(ValidationError) as raised:
            TypeAdapter(list[_FeatureUnion]).validate_python(data)
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=False, width=200)

        handle_validation_error(raised.value, _FeatureUnion, console, data)

        output = buffer.getvalue()
        assert "Heterogeneous collection" in output
        assert "Ambiguous" in output


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
