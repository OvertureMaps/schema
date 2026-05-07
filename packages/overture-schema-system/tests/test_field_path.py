"""Tests for FieldPath, the structural path type for nested schemas."""

from __future__ import annotations

import re

import pytest

from overture.schema.system.field_path import (
    ArrayPath,
    ArraySegment,
    MapPath,
    MapProjection,
    MapSegment,
    ScalarPath,
    StructSegment,
    coerce,
    parse,
    promote_terminal_array,
    promote_terminal_map,
)


class TestParseAndRoundTrip:
    def test_empty_path_parses_to_empty_scalar(self) -> None:
        assert parse("") == ScalarPath(segments=())

    def test_single_segment(self) -> None:
        path = parse("name")
        assert path == ScalarPath(segments=(StructSegment(name="name"),))

    def test_dotted_path(self) -> None:
        path = parse("bbox.xmin")
        assert path == ScalarPath(
            segments=(StructSegment(name="bbox"), StructSegment(name="xmin"))
        )

    def test_array_segment(self) -> None:
        path = parse("items[]")
        assert path == ArrayPath(segments=(ArraySegment(name="items", iter_count=1),))

    def test_array_with_nested_field(self) -> None:
        path = parse("items[].value")
        assert path == ArrayPath(
            segments=(
                ArraySegment(name="items", iter_count=1),
                StructSegment(name="value"),
            )
        )

    def test_nested_list_depth(self) -> None:
        path = parse("hierarchies[][]")
        assert path == ArrayPath(
            segments=(ArraySegment(name="hierarchies", iter_count=2),)
        )

    def test_nested_list_with_leaf(self) -> None:
        path = parse("hierarchies[][].value")
        assert path == ArrayPath(
            segments=(
                ArraySegment(name="hierarchies", iter_count=2),
                StructSegment(name="value"),
            )
        )

    def test_complex_path(self) -> None:
        path = parse("speed_limits[].when.vehicle[].dimension")
        assert path == ArrayPath(
            segments=(
                ArraySegment(name="speed_limits", iter_count=1),
                StructSegment(name="when"),
                ArraySegment(name="vehicle", iter_count=1),
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
        ],
    )
    def test_str_round_trip(self, encoded: str) -> None:
        assert str(parse(encoded)) == encoded


class TestScalarVsArrayPartition:
    def test_no_array_returns_scalar_path(self) -> None:
        assert isinstance(parse("a.b.c"), ScalarPath)

    def test_with_array_returns_array_path(self) -> None:
        assert isinstance(parse("a.b[].c"), ArrayPath)

    def test_empty_is_scalar(self) -> None:
        assert isinstance(parse(""), ScalarPath)


class TestStr:
    def test_empty_renders_as_empty(self) -> None:
        assert str(ScalarPath()) == ""

    def test_scalar_path_renders_dotted(self) -> None:
        path = ScalarPath(
            segments=(StructSegment(name="bbox"), StructSegment(name="xmin"))
        )
        assert str(path) == "bbox.xmin"

    def test_array_path_renders_with_brackets(self) -> None:
        path = ArrayPath(
            segments=(
                ArraySegment(name="speed_limits", iter_count=1),
                StructSegment(name="when"),
            )
        )
        assert str(path) == "speed_limits[].when"

    def test_array_path_renders_multi_depth(self) -> None:
        path = ArrayPath(segments=(ArraySegment(name="hierarchies", iter_count=2),))
        assert str(path) == "hierarchies[][]"


class TestAppendStruct:
    def test_scalar_append_struct_returns_scalar(self) -> None:
        path = ScalarPath().append_struct("name")
        assert path == parse("name")
        assert isinstance(path, ScalarPath)

    def test_scalar_chain_struct(self) -> None:
        path = ScalarPath().append_struct("bbox").append_struct("xmin")
        assert path == parse("bbox.xmin")

    def test_array_append_struct_returns_array(self) -> None:
        path = parse("items[]")
        assert isinstance(path, ArrayPath)
        result = path.append_struct("value")
        assert result == parse("items[].value")
        assert isinstance(result, ArrayPath)


class TestAppendArray:
    def test_scalar_append_array_returns_array_path(self) -> None:
        path = ScalarPath().append_array("items")
        assert path == parse("items[]")
        assert isinstance(path, ArrayPath)

    def test_scalar_append_array_after_struct(self) -> None:
        path = ScalarPath().append_struct("outer").append_array("items")
        assert path == parse("outer.items[]")

    def test_scalar_append_array_multi_depth(self) -> None:
        path = ScalarPath().append_array("hierarchies", iter_count=2)
        assert path == parse("hierarchies[][]")

    def test_array_append_array(self) -> None:
        path = parse("outer[]")
        assert isinstance(path, ArrayPath)
        result = path.append_array("inner")
        assert result == parse("outer[].inner[]")


class TestPromoteTerminalArray:
    def test_scalar_struct_terminal_becomes_array(self) -> None:
        assert promote_terminal_array(parse("tags")) == parse("tags[]")

    def test_struct_prefix_is_preserved(self) -> None:
        assert promote_terminal_array(parse("outer.tags")) == parse("outer.tags[]")

    def test_struct_terminal_inside_array_path(self) -> None:
        assert promote_terminal_array(parse("items[].tags")) == parse("items[].tags[]")

    def test_array_terminal_increments_iter_count(self) -> None:
        assert promote_terminal_array(parse("tags[]")) == parse("tags[][]")

    def test_consecutive_promotions_stack(self) -> None:
        assert promote_terminal_array(promote_terminal_array(parse("grid"))) == parse(
            "grid[][]"
        )

    def test_array_terminal_inside_array_path(self) -> None:
        assert promote_terminal_array(parse("items[].grid[]")) == parse(
            "items[].grid[][]"
        )

    def test_empty_path_raises(self) -> None:
        with pytest.raises(ValueError, match="empty path"):
            promote_terminal_array(ScalarPath())

    def test_map_path_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="map"):
            promote_terminal_array(parse("subs{value}.inner"))


class TestColumnPrefix:
    def test_array_at_start_has_empty_prefix(self) -> None:
        path = parse("items[].value")
        assert isinstance(path, ArrayPath)
        assert path.column_prefix == ScalarPath(())

    def test_struct_prefix_before_array(self) -> None:
        path = parse("parent.items[].value")
        assert isinstance(path, ArrayPath)
        assert path.column_prefix == parse("parent")

    def test_dotted_struct_prefix(self) -> None:
        path = parse("a.b.c[].d")
        assert isinstance(path, ArrayPath)
        assert path.column_prefix == parse("a.b")


class TestLeaf:
    def test_no_leaf_after_array(self) -> None:
        path = parse("items[]")
        assert isinstance(path, ArrayPath)
        assert path.leaf == ()

    def test_single_struct_leaf(self) -> None:
        path = parse("items[].value")
        assert isinstance(path, ArrayPath)
        assert path.leaf == ("value",)

    def test_nested_struct_leaf(self) -> None:
        path = parse("items[].nested.value")
        assert isinstance(path, ArrayPath)
        assert path.leaf == ("nested", "value")

    def test_uses_last_array(self) -> None:
        path = parse("speed_limits[].when.vehicle[].dimension")
        assert isinstance(path, ArrayPath)
        assert path.leaf == ("dimension",)


class TestArrayChunks:
    def test_single_top_level_array(self) -> None:
        path = parse("items[]")
        assert isinstance(path, ArrayPath)
        assert path.array_chunks == (((), "items", 1),)

    def test_single_array_with_struct_prefix(self) -> None:
        path = parse("parent.items[].value")
        assert isinstance(path, ArrayPath)
        assert path.array_chunks == ((("parent",), "items", 1),)

    def test_nested_arrays(self) -> None:
        path = parse("speed_limits[].when.vehicle[].dimension")
        assert isinstance(path, ArrayPath)
        assert path.array_chunks == (
            ((), "speed_limits", 1),
            (("when",), "vehicle", 1),
        )

    def test_multi_depth_array(self) -> None:
        path = parse("hierarchies[][].value")
        assert isinstance(path, ArrayPath)
        assert path.array_chunks == (((), "hierarchies", 2),)


class TestIterStructPaths:
    def test_single_iteration_is_empty(self) -> None:
        path = parse("items[].value")
        assert isinstance(path, ArrayPath)
        assert path.iter_struct_paths == ()

    def test_nested_arrays_emit_navigation_path(self) -> None:
        path = parse("speed_limits[].when.vehicle[].dimension")
        assert isinstance(path, ArrayPath)
        assert path.iter_struct_paths == (("when", "vehicle"),)

    def test_multi_depth_array_expands_extra_iterations(self) -> None:
        path = parse("hierarchies[][].value")
        assert isinstance(path, ArrayPath)
        assert path.iter_struct_paths == ((),)

    def test_multi_depth_inner_array_combines_navigation_and_expansion(self) -> None:
        path = parse("rules[].tags[][].value")
        assert isinstance(path, ArrayPath)
        assert path.iter_struct_paths == (("tags",), ())


class TestElementRelativeGate:
    def test_gate_inside_same_outer_array(self) -> None:
        target = parse("items[].value")
        gate = parse("items[].nested")
        assert isinstance(target, ArrayPath)
        assert target.element_relative_gate(gate) == ("nested",)

    def test_gate_at_outer_array_root_returns_empty(self) -> None:
        target = parse("items[].value")
        gate = parse("items[]")
        assert isinstance(target, ArrayPath)
        assert target.element_relative_gate(gate) == ()

    def test_gate_with_dotted_struct_inside_element(self) -> None:
        target = parse("items[].value")
        gate = parse("items[].a.b")
        assert isinstance(target, ArrayPath)
        assert target.element_relative_gate(gate) == ("a", "b")

    def test_scalar_gate_returns_none(self) -> None:
        target = parse("items[].value")
        gate = parse("other")
        assert isinstance(target, ArrayPath)
        assert target.element_relative_gate(gate) is None

    def test_different_outer_array_returns_none(self) -> None:
        target = parse("items[].value")
        gate = parse("other[].x")
        assert isinstance(target, ArrayPath)
        assert target.element_relative_gate(gate) is None

    def test_struct_prefix_must_match(self) -> None:
        target = parse("parent.items[].value")
        gate = parse("items[].x")
        assert isinstance(target, ArrayPath)
        assert target.element_relative_gate(gate) is None

    def test_matching_struct_prefix(self) -> None:
        target = parse("parent.items[].value")
        gate = parse("parent.items[].x")
        assert isinstance(target, ArrayPath)
        assert target.element_relative_gate(gate) == ("x",)

    def test_inner_array_segment_raises(self) -> None:
        target = parse("items[].value")
        gate = parse("items[].nested[]")
        assert isinstance(target, ArrayPath)
        with pytest.raises(NotImplementedError, match="nested array segment"):
            target.element_relative_gate(gate)

    def test_mismatched_iter_count_returns_none(self) -> None:
        # target iterates items[] (iter_count=1); gate enters items[][] (iter_count=2)
        # -- same name, different iteration depth -- not the same element scope
        target = parse("items[].value")
        gate = parse("items[][].nested")
        assert isinstance(target, ArrayPath)
        assert target.element_relative_gate(gate) is None

    def test_matching_iter_count_still_returns_element_relative_tuple(self) -> None:
        # regression: matching iter_count must remain reachable after the fix
        target = parse("items[][].value")
        gate = parse("items[][].nested")
        assert isinstance(target, ArrayPath)
        assert target.element_relative_gate(gate) == ("nested",)


class TestArrayPathInvariant:
    def test_rejects_segments_without_array(self) -> None:
        with pytest.raises(ValueError, match="at least one ArraySegment"):
            ArrayPath(segments=(StructSegment(name="a"),))


class TestEqualityAndHashing:
    def test_paths_with_same_segments_are_equal(self) -> None:
        assert parse("items[].value") == parse("items[].value")

    def test_different_paths_unequal(self) -> None:
        assert parse("items[].value") != parse("items[].other")

    def test_scalar_array_unequal(self) -> None:
        assert parse("items") != parse("items[]")

    def test_hashable(self) -> None:
        s = {parse("a.b"), parse("a.b"), parse("c")}
        assert len(s) == 2

    def test_string_is_not_equal_to_path(self) -> None:
        assert parse("items[].value") != "items[].value"


class TestCoerce:
    def test_passes_through_scalar(self) -> None:
        path = parse("a.b")
        assert coerce(path) is path

    def test_passes_through_array(self) -> None:
        path = parse("items[].value")
        assert coerce(path) is path

    def test_parses_string(self) -> None:
        assert coerce("items[].value") == parse("items[].value")


class TestMapPath:
    def test_str_top_level_key(self) -> None:
        path = MapPath(
            segments=(MapSegment(name="tags", projection=MapProjection.KEY),)
        )
        assert str(path) == "tags{key}"

    def test_str_top_level_value(self) -> None:
        path = MapPath(
            segments=(MapSegment(name="tags", projection=MapProjection.VALUE),)
        )
        assert str(path) == "tags{value}"

    def test_str_nested_under_struct(self) -> None:
        path = MapPath(
            segments=(
                StructSegment(name="names"),
                MapSegment(name="common", projection=MapProjection.KEY),
            )
        )
        assert str(path) == "names.common{key}"

    def test_projection_property(self) -> None:
        path = MapPath(
            segments=(MapSegment(name="tags", projection=MapProjection.VALUE),)
        )
        assert path.projection is MapProjection.VALUE

    def test_map_column_top_level(self) -> None:
        path = MapPath(
            segments=(MapSegment(name="tags", projection=MapProjection.KEY),)
        )
        assert path.map_column == "tags"

    def test_map_column_nested(self) -> None:
        path = MapPath(
            segments=(
                StructSegment(name="names"),
                MapSegment(name="common", projection=MapProjection.VALUE),
            )
        )
        assert path.map_column == "names.common"

    def test_must_contain_a_map_segment(self) -> None:
        with pytest.raises(ValueError, match="MapSegment"):
            MapPath(segments=(StructSegment(name="names"),))

    def test_rejects_array_segment_before_map(self) -> None:
        with pytest.raises(ValueError, match="struct"):
            MapPath(
                segments=(  # type: ignore[arg-type]  # invalid by design: runtime guard under test
                    ArraySegment(name="items"),
                    MapSegment(name="tags", projection=MapProjection.KEY),
                )
            )

    def test_rejects_two_map_segments(self) -> None:
        with pytest.raises(ValueError, match="MapSegment"):
            MapPath(
                segments=(
                    MapSegment(name="a", projection=MapProjection.KEY),
                    MapSegment(name="b", projection=MapProjection.VALUE),
                )
            )

    @pytest.mark.parametrize(
        "encoded",
        ["tags{key}", "tags{value}", "names.common{key}", "names.common{value}"],
    )
    def test_str_round_trip(self, encoded: str) -> None:
        assert str(parse(encoded)) == encoded

    def test_parse_returns_map_path(self) -> None:
        assert isinstance(parse("names.common{key}"), MapPath)

    def test_parse_key(self) -> None:
        assert parse("tags{key}") == MapPath(
            segments=(MapSegment(name="tags", projection=MapProjection.KEY),)
        )

    def test_parse_nested_value(self) -> None:
        assert parse("names.common{value}") == MapPath(
            segments=(
                StructSegment(name="names"),
                MapSegment(name="common", projection=MapProjection.VALUE),
            )
        )


class TestMapPathLeaf:
    """A `MapPath` may carry struct segments after the `MapSegment`.

    These name a value inside a `dict[K, Model]`'s value (or key) struct,
    mirroring `ArrayPath.leaf` for `list[Model]`. The `MapSegment` is the
    iteration boundary; the leaf is the struct navigation inside each
    projected element.
    """

    def test_leaf_empty_for_bare_projection(self) -> None:
        path = MapPath(
            segments=(MapSegment(name="subs", projection=MapProjection.VALUE),)
        )
        assert path.leaf == ()

    def test_leaf_names_struct_segments_after_map(self) -> None:
        path = MapPath(
            segments=(
                MapSegment(name="subs", projection=MapProjection.VALUE),
                StructSegment(name="label"),
            )
        )
        assert path.leaf == ("label",)

    def test_leaf_spans_nested_struct_navigation(self) -> None:
        path = MapPath(
            segments=(
                MapSegment(name="subs", projection=MapProjection.VALUE),
                StructSegment(name="inner"),
                StructSegment(name="label"),
            )
        )
        assert path.leaf == ("inner", "label")

    def test_map_column_excludes_leaf(self) -> None:
        path = MapPath(
            segments=(
                StructSegment(name="names"),
                MapSegment(name="common", projection=MapProjection.VALUE),
                StructSegment(name="label"),
            )
        )
        assert path.map_column == "names.common"

    def test_projection_found_with_leaf_present(self) -> None:
        path = MapPath(
            segments=(
                MapSegment(name="subs", projection=MapProjection.KEY),
                StructSegment(name="label"),
            )
        )
        assert path.projection is MapProjection.KEY

    def test_str_appends_leaf_after_marker(self) -> None:
        path = MapPath(
            segments=(
                MapSegment(name="subs", projection=MapProjection.VALUE),
                StructSegment(name="label"),
            )
        )
        assert str(path) == "subs{value}.label"

    def test_append_struct_extends_leaf(self) -> None:
        path = MapPath(
            segments=(MapSegment(name="subs", projection=MapProjection.VALUE),)
        )
        extended = path.append_struct("label")
        assert extended == MapPath(
            segments=(
                MapSegment(name="subs", projection=MapProjection.VALUE),
                StructSegment(name="label"),
            )
        )

    def test_rejects_array_segment_in_leaf(self) -> None:
        with pytest.raises(ValueError, match="struct"):
            MapPath(
                segments=(  # type: ignore[arg-type]  # invalid by design: runtime guard under test
                    MapSegment(name="subs", projection=MapProjection.VALUE),
                    ArraySegment(name="items"),
                )
            )

    @pytest.mark.parametrize(
        "encoded",
        ["subs{value}.label", "names.common{key}.tag", "subs{value}.inner.label"],
    )
    def test_str_round_trip_with_leaf(self, encoded: str) -> None:
        assert str(parse(encoded)) == encoded

    def test_parse_value_with_leaf(self) -> None:
        assert parse("subs{value}.label") == MapPath(
            segments=(
                MapSegment(name="subs", projection=MapProjection.VALUE),
                StructSegment(name="label"),
            )
        )

    def test_parse_rejects_array_marker_in_leaf(self) -> None:
        with pytest.raises(ValueError, match="map projection"):
            parse("subs{value}.items[]")


class TestPromoteTerminalMap:
    def test_top_level_struct_becomes_map_key(self) -> None:
        assert promote_terminal_map(parse("tags"), MapProjection.KEY) == parse(
            "tags{key}"
        )

    def test_struct_prefix_preserved_for_value(self) -> None:
        assert promote_terminal_map(
            parse("names.common"), MapProjection.VALUE
        ) == parse("names.common{value}")

    def test_empty_path_raises(self) -> None:
        with pytest.raises(ValueError, match="empty path"):
            promote_terminal_map(ScalarPath(), MapProjection.KEY)

    def test_array_path_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="list"):
            promote_terminal_map(parse("items[].tags"), MapProjection.KEY)

    def test_map_path_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="map"):
            promote_terminal_map(parse("subs{value}.inner"), MapProjection.VALUE)


class TestParseRejectsEmptyParts:
    @pytest.mark.parametrize("encoded", [".a", "a..b", "[]", "a.[]", ".[]"])
    def test_raises_value_error_on_empty_part(self, encoded: str) -> None:
        with pytest.raises(ValueError, match="empty name"):
            parse(encoded)

    @pytest.mark.parametrize("encoded", [".a", "a..b", "[]"])
    def test_error_includes_input_string(self, encoded: str) -> None:
        with pytest.raises(ValueError, match=re.escape(repr(encoded))):
            parse(encoded)
