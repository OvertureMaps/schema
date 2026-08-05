"""Tests for FieldPath, the structural path type for nested schemas."""

from __future__ import annotations

import re

import pytest

from overture.schema.system.field_path import (
    ArraySegment,
    Direct,
    Iterated,
    MapProjection,
    MapSegment,
    StructSegment,
    coerce,
    parse,
    promote_terminal,
    terminal_run_start,
)


class TestParseAndRoundTrip:
    def test_empty_path_parses_to_empty_direct(self) -> None:
        assert parse("") == Direct(segments=())

    def test_single_segment(self) -> None:
        path = parse("name")
        assert path == Direct(segments=(StructSegment(name="name"),))

    def test_dotted_path(self) -> None:
        path = parse("bbox.xmin")
        assert path == Direct(
            segments=(StructSegment(name="bbox"), StructSegment(name="xmin"))
        )

    def test_array_segment(self) -> None:
        path = parse("items[]")
        assert path == Iterated(segments=(ArraySegment(name="items"),))

    def test_array_with_nested_field(self) -> None:
        path = parse("items[].value")
        assert path == Iterated(
            segments=(
                ArraySegment(name="items"),
                StructSegment(name="value"),
            )
        )

    def test_nested_list_parses_to_anonymous_segments(self) -> None:
        assert parse("hierarchies[][]") == Iterated(
            segments=(
                ArraySegment(name="hierarchies"),
                ArraySegment(name=""),
            )
        )

    def test_nested_list_with_leaf(self) -> None:
        path = parse("hierarchies[][].value")
        assert path == Iterated(
            segments=(
                ArraySegment(name="hierarchies"),
                ArraySegment(name=""),
                StructSegment(name="value"),
            )
        )

    def test_is_anonymous_property(self) -> None:
        assert ArraySegment(name="").is_anonymous is True
        assert ArraySegment(name="grid").is_anonymous is False
        assert MapSegment(name="", projection=MapProjection.VALUE).is_anonymous is True
        assert (
            MapSegment(name="subs", projection=MapProjection.VALUE).is_anonymous
            is False
        )

    def test_nested_list_round_trips(self) -> None:
        assert str(parse("hierarchies[][]")) == "hierarchies[][]"

    def test_nested_list_with_leaf_round_trips(self) -> None:
        assert str(parse("hierarchies[][].value")) == "hierarchies[][].value"

    def test_complex_path(self) -> None:
        path = parse("speed_limits[].when.vehicle[].dimension")
        assert path == Iterated(
            segments=(
                ArraySegment(name="speed_limits"),
                StructSegment(name="when"),
                ArraySegment(name="vehicle"),
                StructSegment(name="dimension"),
            )
        )

    @pytest.mark.parametrize(
        "encoded",
        [
            "",
            "name",
            "bbox.xmin",
            "items[]",
            "items[].value",
            "hierarchies[][]",
            "hierarchies[][].value",
            "speed_limits[].when.vehicle[].dimension",
            "tags_min_length",
            "tags{key}",
            "tags{value}",
            "names.common{key}",
            "subs{value}.label",
        ],
    )
    def test_str_round_trip(self, encoded: str) -> None:
        assert str(parse(encoded)) == encoded


class TestTypes:
    def test_types(self) -> None:
        assert isinstance(parse("a.b.c"), Direct)
        assert isinstance(parse("a.b[].c"), Iterated)
        assert isinstance(parse("names.common{key}"), Iterated)

    def test_empty_is_direct(self) -> None:
        assert isinstance(parse(""), Direct)

    def test_map_first_is_iterated(self) -> None:
        assert isinstance(parse("tags{value}"), Iterated)


class TestInterleavedGrammar:
    @pytest.mark.parametrize(
        "encoded",
        [
            "hierarchies[][]",
            "subs{value}[]",
            "items[]{value}",
            "a{value}{value}",
            "subs{value}.label",
            "items[].tags{value}",
            "names.common{key}",
            "dict_field{value}.label",
        ],
    )
    def test_interleaved_round_trip(self, encoded: str) -> None:
        assert str(parse(encoded)) == encoded

    def test_dict_of_list_segments(self) -> None:
        assert parse("subs{value}[]").segments == (
            MapSegment(name="subs", projection=MapProjection.VALUE),
            ArraySegment(name=""),
        )

    def test_list_of_dict_segments(self) -> None:
        assert parse("items[]{value}").segments == (
            ArraySegment(name="items"),
            MapSegment(name="", projection=MapProjection.VALUE),
        )

    def test_map_of_map_segments(self) -> None:
        assert parse("a{value}{value}").segments == (
            MapSegment(name="a", projection=MapProjection.VALUE),
            MapSegment(name="", projection=MapProjection.VALUE),
        )

    def test_named_map_in_array_segments(self) -> None:
        assert parse("items[].tags{value}").segments == (
            ArraySegment(name="items"),
            MapSegment(name="tags", projection=MapProjection.VALUE),
        )

    def test_map_with_struct_leaf_segments(self) -> None:
        assert parse("subs{value}.label").segments == (
            MapSegment(name="subs", projection=MapProjection.VALUE),
            StructSegment(name="label"),
        )


class TestStr:
    def test_empty_renders_as_empty(self) -> None:
        assert str(Direct()) == ""

    def test_direct_renders_dotted(self) -> None:
        path = Direct(segments=(StructSegment(name="bbox"), StructSegment(name="xmin")))
        assert str(path) == "bbox.xmin"

    def test_iterated_renders_with_brackets(self) -> None:
        path = Iterated(
            segments=(
                ArraySegment(name="speed_limits"),
                StructSegment(name="when"),
            )
        )
        assert str(path) == "speed_limits[].when"

    def test_iterated_renders_multi_depth(self) -> None:
        path = Iterated(
            segments=(ArraySegment(name="hierarchies"), ArraySegment(name=""))
        )
        assert str(path) == "hierarchies[][]"

    def test_map_renders_with_projection(self) -> None:
        path = Iterated(
            segments=(
                StructSegment(name="names"),
                MapSegment(name="common", projection=MapProjection.KEY),
            )
        )
        assert str(path) == "names.common{key}"


class TestAppendStruct:
    def test_direct_append_struct_returns_direct(self) -> None:
        path = Direct().append_struct("name")
        assert path == parse("name")
        assert isinstance(path, Direct)

    def test_direct_chain_struct(self) -> None:
        path = Direct().append_struct("bbox").append_struct("xmin")
        assert path == parse("bbox.xmin")

    def test_iterated_append_struct_returns_iterated(self) -> None:
        path = parse("items[]")
        assert isinstance(path, Iterated)
        result = path.append_struct("value")
        assert result == parse("items[].value")
        assert isinstance(result, Iterated)

    def test_map_append_struct_extends_leaf(self) -> None:
        path = parse("subs{value}")
        assert isinstance(path, Iterated)
        result = path.append_struct("label")
        assert result == parse("subs{value}.label")


class TestAppendArray:
    def test_direct_append_array_returns_iterated(self) -> None:
        path = Direct().append_array("items")
        assert path == parse("items[]")
        assert isinstance(path, Iterated)

    def test_direct_append_array_after_struct(self) -> None:
        path = Direct().append_struct("outer").append_array("items")
        assert path == parse("outer.items[]")

    def test_iterated_append_array(self) -> None:
        path = parse("outer[]")
        assert isinstance(path, Iterated)
        result = path.append_array("inner")
        assert result == parse("outer[].inner[]")


class TestPromoteTerminal:
    def test_struct_terminal_becomes_array(self) -> None:
        assert promote_terminal(parse("tags")) == parse("tags[]")

    def test_struct_prefix_is_preserved(self) -> None:
        assert promote_terminal(parse("outer.tags")) == parse("outer.tags[]")

    def test_struct_terminal_inside_iterated(self) -> None:
        assert promote_terminal(parse("items[].tags")) == parse("items[].tags[]")

    def test_promote_array_terminal_appends_anonymous(self) -> None:
        assert promote_terminal(parse("tags[]")) == parse("tags[][]")
        assert promote_terminal(parse("tags[]")).segments == (
            ArraySegment(name="tags"),
            ArraySegment(name=""),
        )

    def test_consecutive_promotions_stack(self) -> None:
        assert promote_terminal(promote_terminal(parse("grid"))) == parse("grid[][]")

    def test_array_terminal_inside_iterated(self) -> None:
        assert promote_terminal(parse("items[].grid[]")) == parse("items[].grid[][]")

    def test_struct_terminal_becomes_map_key(self) -> None:
        assert promote_terminal(parse("tags"), projection=MapProjection.KEY) == parse(
            "tags{key}"
        )

    def test_struct_prefix_preserved_for_map_value(self) -> None:
        assert promote_terminal(
            parse("names.common"), projection=MapProjection.VALUE
        ) == parse("names.common{value}")

    def test_promote_terminal_to_array_on_map(self) -> None:  # dict[K, list]
        assert promote_terminal(parse("subs{value}")).segments[-1] == ArraySegment(
            name=""
        )

    def test_promote_terminal_to_map_on_array(self) -> None:  # list[dict]
        assert promote_terminal(
            parse("items[]"), projection=MapProjection.VALUE
        ).segments[-1] == MapSegment(name="", projection=MapProjection.VALUE)

    def test_empty_path_raises(self) -> None:
        with pytest.raises(ValueError, match="empty path"):
            promote_terminal(Direct())

    def test_empty_path_raises_for_map(self) -> None:
        with pytest.raises(ValueError, match="empty path"):
            promote_terminal(Direct(), projection=MapProjection.KEY)


class TestOuterColumn:
    @staticmethod
    def _outer_column(encoded: str) -> str:
        path = parse(encoded)
        assert isinstance(path, Iterated)
        return path.outer_column

    def test_array_at_start(self) -> None:
        assert self._outer_column("items[].value") == "items"

    def test_struct_prefix_before_array(self) -> None:
        assert self._outer_column("parent.items[].value") == "parent.items"

    def test_map_outer_column(self) -> None:
        assert self._outer_column("names.common{value}.label") == "names.common"

    def test_map_at_start(self) -> None:
        assert self._outer_column("tags{key}") == "tags"


class TestColumnPrefix:
    def test_array_at_start_has_empty_prefix(self) -> None:
        path = parse("items[].value")
        assert isinstance(path, Iterated)
        assert path.column_prefix == Direct(())

    def test_struct_prefix_before_array(self) -> None:
        path = parse("parent.items[].value")
        assert isinstance(path, Iterated)
        assert path.column_prefix == parse("parent")

    def test_dotted_struct_prefix(self) -> None:
        path = parse("a.b.c[].d")
        assert isinstance(path, Iterated)
        assert path.column_prefix == parse("a.b")

    def test_struct_prefix_before_map(self) -> None:
        path = parse("names.common{value}")
        assert isinstance(path, Iterated)
        assert path.column_prefix == parse("names")


class TestLeaf:
    def test_no_leaf_after_array(self) -> None:
        path = parse("items[]")
        assert isinstance(path, Iterated)
        assert path.leaf == ()

    def test_single_struct_leaf(self) -> None:
        path = parse("items[].value")
        assert isinstance(path, Iterated)
        assert path.leaf == ("value",)

    def test_nested_struct_leaf(self) -> None:
        path = parse("items[].nested.value")
        assert isinstance(path, Iterated)
        assert path.leaf == ("nested", "value")

    def test_uses_last_iterating_segment(self) -> None:
        path = parse("speed_limits[].when.vehicle[].dimension")
        assert isinstance(path, Iterated)
        assert path.leaf == ("dimension",)

    def test_map_leaf(self) -> None:
        path = parse("subs{value}.inner.label")
        assert isinstance(path, Iterated)
        assert path.leaf == ("inner", "label")

    def test_bare_map_has_empty_leaf(self) -> None:
        path = parse("subs{value}")
        assert isinstance(path, Iterated)
        assert path.leaf == ()


class TestIterFrames:
    def test_single_top_level_array(self) -> None:
        path = parse("items[]")
        assert isinstance(path, Iterated)
        assert path.iter_frames == (((), ArraySegment(name="items")),)

    def test_single_array_with_struct_prefix(self) -> None:
        path = parse("parent.items[].value")
        assert isinstance(path, Iterated)
        assert path.iter_frames == ((("parent",), ArraySegment(name="items")),)

    def test_nested_arrays(self) -> None:
        path = parse("speed_limits[].when.vehicle[].dimension")
        assert isinstance(path, Iterated)
        assert path.iter_frames == (
            ((), ArraySegment(name="speed_limits")),
            (("when",), ArraySegment(name="vehicle")),
        )

    def test_multi_depth_folds_anonymous(self) -> None:
        path = parse("hierarchies[][].value")
        assert isinstance(path, Iterated)
        assert path.iter_frames == (((), ArraySegment(name="hierarchies")),)

    def test_map_frame(self) -> None:
        path = parse("names.common{key}")
        assert isinstance(path, Iterated)
        assert path.iter_frames == (
            (("names",), MapSegment(name="common", projection=MapProjection.KEY)),
        )

    def test_mixed_map_in_array(self) -> None:
        path = parse("items[].tags{value}")
        assert isinstance(path, Iterated)
        assert path.iter_frames == (
            ((), ArraySegment(name="items")),
            ((), MapSegment(name="tags", projection=MapProjection.VALUE)),
        )


class TestIterStructPaths:
    def test_single_iteration_is_empty(self) -> None:
        path = parse("items[].value")
        assert isinstance(path, Iterated)
        assert path.iter_struct_paths == ()

    def test_nested_arrays_emit_navigation_path(self) -> None:
        path = parse("speed_limits[].when.vehicle[].dimension")
        assert isinstance(path, Iterated)
        assert path.iter_struct_paths == (("when", "vehicle"),)

    def test_multi_depth_iter_struct_paths(self) -> None:
        # inner anonymous frame contributes () (no navigation)
        path = parse("hierarchies[][].value")
        assert isinstance(path, Iterated)
        assert path.iter_struct_paths == ((),)

    def test_multi_depth_inner_array_combines_navigation_and_expansion(self) -> None:
        path = parse("rules[].tags[][].value")
        assert isinstance(path, Iterated)
        assert path.iter_struct_paths == (("tags",), ())

    def test_mixed_map_in_array_navigation(self) -> None:
        path = parse("items[].tags{value}")
        assert isinstance(path, Iterated)
        assert path.iter_struct_paths == (("tags",),)


class TestTerminalRunStart:
    def test_named_array_terminal(self) -> None:
        path = parse("items[]")
        assert terminal_run_start(path.segments) == 0

    def test_multi_bracket_terminal_starts_at_named_segment(self) -> None:
        path = parse("hierarchies[][]")
        assert terminal_run_start(path.segments) == 0

    def test_struct_leaf_after_array_is_its_own_run(self) -> None:
        path = parse("items[].value")
        assert terminal_run_start(path.segments) == 1

    def test_struct_only_path_returns_last_index(self) -> None:
        path = parse("a.b.c")
        assert terminal_run_start(path.segments) == 2

    def test_single_segment_returns_zero(self) -> None:
        path = parse("a")
        assert terminal_run_start(path.segments) == 0


class TestElementRelativeGate:
    def test_gate_inside_same_outer_array(self) -> None:
        target = parse("items[].value")
        gate = parse("items[].nested")
        assert isinstance(target, Iterated)
        assert target.element_relative_gate(gate) == ("nested",)

    def test_gate_at_outer_array_root_returns_empty(self) -> None:
        target = parse("items[].value")
        gate = parse("items[]")
        assert isinstance(target, Iterated)
        assert target.element_relative_gate(gate) == ()

    def test_gate_with_dotted_struct_inside_element(self) -> None:
        target = parse("items[].value")
        gate = parse("items[].a.b")
        assert isinstance(target, Iterated)
        assert target.element_relative_gate(gate) == ("a", "b")

    def test_scalar_gate_returns_none(self) -> None:
        target = parse("items[].value")
        gate = parse("other")
        assert isinstance(target, Iterated)
        assert target.element_relative_gate(gate) is None

    def test_different_outer_array_returns_none(self) -> None:
        target = parse("items[].value")
        gate = parse("other[].x")
        assert isinstance(target, Iterated)
        assert target.element_relative_gate(gate) is None

    def test_struct_prefix_must_match(self) -> None:
        target = parse("parent.items[].value")
        gate = parse("items[].x")
        assert isinstance(target, Iterated)
        assert target.element_relative_gate(gate) is None

    def test_matching_struct_prefix(self) -> None:
        target = parse("parent.items[].value")
        gate = parse("parent.items[].x")
        assert isinstance(target, Iterated)
        assert target.element_relative_gate(gate) == ("x",)

    def test_inner_array_segment_raises(self) -> None:
        target = parse("items[].value")
        gate = parse("items[].nested[]")
        assert isinstance(target, Iterated)
        with pytest.raises(NotImplementedError, match="nested array segment"):
            target.element_relative_gate(gate)

    def test_mismatched_iteration_depth_returns_none(self) -> None:
        target = parse("items[].value")
        gate = parse("items[][].nested")
        assert isinstance(target, Iterated)
        assert target.element_relative_gate(gate) is None

    def test_matching_iteration_depth_still_returns_element_relative_tuple(
        self,
    ) -> None:
        target = parse("items[][].value")
        gate = parse("items[][].nested")
        assert isinstance(target, Iterated)
        assert target.element_relative_gate(gate) == ("nested",)


class TestIteratedInvariant:
    def test_iterated_requires_iterating_segment(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            Iterated(segments=(StructSegment(name="a"),))

    def test_first_iterating_segment_named_invariant(self) -> None:
        with pytest.raises(ValueError, match="first"):
            Iterated(segments=(ArraySegment(name=""),))

    def test_first_iterating_map_segment_named_invariant(self) -> None:
        with pytest.raises(ValueError, match="first"):
            Iterated(segments=(MapSegment(name="", projection=MapProjection.VALUE),))

    def test_struct_prefix_before_first_iterating_is_allowed(self) -> None:
        # a struct PREFIX before the first iterating segment is fine
        path = Iterated(
            segments=(StructSegment(name="parent"), ArraySegment(name="items"))
        )
        assert path.outer_column == "parent.items"


class TestEqualityAndHashing:
    def test_paths_with_same_segments_are_equal(self) -> None:
        assert parse("items[].value") == parse("items[].value")

    def test_different_paths_unequal(self) -> None:
        assert parse("items[].value") != parse("items[].other")

    def test_direct_iterated_unequal(self) -> None:
        assert parse("items") != parse("items[]")

    def test_hashable(self) -> None:
        s = {parse("a.b"), parse("a.b"), parse("c")}
        assert len(s) == 2

    def test_string_is_not_equal_to_path(self) -> None:
        assert parse("items[].value") != "items[].value"


class TestCoerce:
    def test_passes_through_direct(self) -> None:
        path = parse("a.b")
        assert coerce(path) is path

    def test_passes_through_iterated(self) -> None:
        path = parse("items[].value")
        assert coerce(path) is path

    def test_parses_string(self) -> None:
        assert coerce("items[].value") == parse("items[].value")


class TestParseRejectsEmptyParts:
    @pytest.mark.parametrize("encoded", [".a", "a..b", "[]", "a.[]", ".[]", "a.{key}"])
    def test_raises_value_error_on_empty_part(self, encoded: str) -> None:
        with pytest.raises(ValueError, match="empty name"):
            parse(encoded)

    @pytest.mark.parametrize("encoded", [".a", "a..b", "[]"])
    def test_error_includes_input_string(self, encoded: str) -> None:
        with pytest.raises(ValueError, match=re.escape(repr(encoded))):
            parse(encoded)
