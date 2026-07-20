"""Tests for model-level mutation functions."""

from typing import Any

import pytest

from ._support.helpers import PathTraversalError
from ._support.mutations import (
    _get_nested,
    _set_nested,
    _walk_strict,
    mutate_forbid_if,
    mutate_map_key,
    mutate_map_value,
    mutate_min_fields_set,
    mutate_radio_group,
    mutate_require_any_of,
    mutate_require_any_true,
    mutate_require_if,
    mutate_unique_items,
)


class TestMutateMapKey:
    def test_replaces_key_preserving_value(self) -> None:
        row = {"names": {"en": "clean"}}
        result = mutate_map_key(row, "names", "123")
        assert result["names"] == {"123": "clean"}

    def test_nested_path(self) -> None:
        row = {"names": {"common": {"en": "clean"}}}
        result = mutate_map_key(row, "names.common", "123")
        assert result["names"]["common"] == {"123": "clean"}

    def test_does_not_mutate_original(self) -> None:
        row = {"names": {"en": "clean"}}
        mutate_map_key(row, "names", "123")
        assert row["names"] == {"en": "clean"}

    def test_missing_map_raises(self) -> None:
        with pytest.raises(PathTraversalError):
            mutate_map_key({"other": 1}, "names", "123")

    def test_empty_map_raises(self) -> None:
        with pytest.raises(PathTraversalError):
            mutate_map_key({"names": {}}, "names", "123")


class TestMutateMapValue:
    def test_replaces_value_preserving_key(self) -> None:
        row = {"names": {"en": "clean"}}
        result = mutate_map_value(row, "names", " has spaces ")
        assert result["names"] == {"en": " has spaces "}

    def test_nested_path(self) -> None:
        row = {"names": {"common": {"en": "clean"}}}
        result = mutate_map_value(row, "names.common", " bad ")
        assert result["names"]["common"] == {"en": " bad "}

    def test_does_not_mutate_original(self) -> None:
        row = {"names": {"en": "clean"}}
        mutate_map_value(row, "names", " bad ")
        assert row["names"] == {"en": "clean"}

    def test_missing_map_raises(self) -> None:
        with pytest.raises(PathTraversalError):
            mutate_map_value({"other": 1}, "names", " bad ")


class TestMutateRequireAnyOf:
    def test_nulls_all_named_fields(self) -> None:
        row = {"a": 1, "b": 2, "c": 3}
        result = mutate_require_any_of(row, ["a", "b"])
        assert result["a"] is None
        assert result["b"] is None
        assert result["c"] == 3

    def test_does_not_mutate_original(self) -> None:
        row = {"a": 1, "b": 2}
        mutate_require_any_of(row, ["a"])
        assert row["a"] == 1


class TestMutateRadioGroup:
    def test_sets_two_fields_to_true(self) -> None:
        row = {"is_land": True, "is_territorial": False, "other": "x"}
        result = mutate_radio_group(row, ["is_land", "is_territorial"])
        assert result["is_land"] is True
        assert result["is_territorial"] is True

    def test_does_not_mutate_original(self) -> None:
        row = {"a": False, "b": False}
        mutate_radio_group(row, ["a", "b"])
        assert row["a"] is False


class TestMutateRequireAnyTrue:
    def test_sets_each_field_to_disabling_value(self) -> None:
        row = {"is_land": True, "is_territorial": True, "other": "x"}
        result = mutate_require_any_true(
            row, {"is_land": False, "is_territorial": False}
        )
        assert result["is_land"] is False
        assert result["is_territorial"] is False
        assert result["other"] == "x"

    def test_does_not_mutate_original(self) -> None:
        row = {"is_land": True, "is_territorial": True}
        mutate_require_any_true(row, {"is_land": False, "is_territorial": False})
        assert row["is_land"] is True


class TestMutateMinFieldsSet:
    def test_nulls_all_named_fields(self) -> None:
        row = {"a": 1, "b": 2, "c": 3}
        result = mutate_min_fields_set(row, ["a", "b", "c"])
        assert result["a"] is None
        assert result["b"] is None
        assert result["c"] is None

    def test_leaves_unlisted_fields_alone(self) -> None:
        row = {"a": 1, "b": 2, "other": "keep"}
        result = mutate_min_fields_set(row, ["a", "b"])
        assert result["other"] == "keep"

    def test_does_not_mutate_original(self) -> None:
        row = {"a": 1, "b": 2}
        mutate_min_fields_set(row, ["a", "b"])
        assert row["a"] == 1

    def test_with_array_path_nulls_inside_each_element(self) -> None:
        row = {"items": [{"a": 1, "b": 2}, {"a": 3, "b": 4}]}
        result = mutate_min_fields_set(row, ["a", "b"], array_path="items")
        assert result["items"] == [{"a": None, "b": None}, {"a": None, "b": None}]


class TestMutateRequireIf:
    def test_sets_condition_and_nulls_targets(self) -> None:
        row = {"subtype": "other", "admin_level": 5}
        result = mutate_require_if(row, ["admin_level"], "subtype", "country")
        assert result["subtype"] == "country"
        assert result["admin_level"] is None

    def test_does_not_mutate_original(self) -> None:
        row = {"subtype": "other", "admin_level": 5}
        mutate_require_if(row, ["admin_level"], "subtype", "country")
        assert row["subtype"] == "other"


class TestMutateForbidIf:
    def test_sets_condition_and_ensures_non_null(self) -> None:
        row = {"subtype": "other", "admin_level": None}
        result = mutate_forbid_if(row, ["admin_level"], "subtype", "country")
        assert result["subtype"] == "country"
        assert result["admin_level"] is not None

    def test_preserves_existing_non_null(self) -> None:
        row = {"subtype": "other", "admin_level": 5}
        result = mutate_forbid_if(row, ["admin_level"], "subtype", "country")
        assert result["admin_level"] == 5

    def test_uses_fill_value_for_array_field(self) -> None:
        row = {"subtype": "other", "destinations": None}
        result = mutate_forbid_if(
            row,
            ["destinations"],
            "subtype",
            "road",
            fill_values={"destinations": [{}]},
        )
        assert result["destinations"] == [{}]

    def test_uses_fill_value_for_struct_field(self) -> None:
        row = {"subtype": "other", "road_surface": None}
        result = mutate_forbid_if(
            row,
            ["road_surface"],
            "subtype",
            "road",
            fill_values={"road_surface": {}},
        )
        assert result["road_surface"] == {}

    def test_fill_value_ignored_when_field_already_non_null(self) -> None:
        row = {"subtype": "other", "destinations": [{"id": "x"}]}
        result = mutate_forbid_if(
            row,
            ["destinations"],
            "subtype",
            "road",
            fill_values={"destinations": [{}]},
        )
        assert result["destinations"] == [{"id": "x"}]


class TestMutateRequireAnyOfNested:
    def test_nulls_fields_within_array_elements(self) -> None:
        row = {
            "items": [
                {"a": 1, "b": 2, "c": 3},
                {"a": 4, "b": 5, "c": 6},
            ]
        }
        result = mutate_require_any_of(row, ["a", "b"], array_path="items")
        for item in result["items"]:
            assert item["a"] is None
            assert item["b"] is None
            assert item["c"] is not None

    def test_nulls_fields_within_nested_struct(self) -> None:
        row = {
            "items": [
                {"when": {"a": 1, "b": 2}},
            ]
        }
        result = mutate_require_any_of(
            row, ["a", "b"], array_path="items", struct_path="when"
        )
        assert result["items"][0]["when"]["a"] is None
        assert result["items"][0]["when"]["b"] is None

    def test_creates_stub_element_when_array_is_null(self) -> None:
        row = {"items": None}
        result = mutate_require_any_of(row, ["a", "b"], array_path="items")
        assert isinstance(result["items"], list)
        assert len(result["items"]) == 1
        assert result["items"][0]["a"] is None
        assert result["items"][0]["b"] is None

    def test_creates_stub_with_struct_path_when_null(self) -> None:
        row = {"items": None}
        result = mutate_require_any_of(
            row, ["a", "b"], array_path="items", struct_path="when"
        )
        assert result["items"][0]["when"]["a"] is None
        assert result["items"][0]["when"]["b"] is None

    def test_does_not_mutate_original(self) -> None:
        row = {"items": [{"a": 1, "b": 2}]}
        mutate_require_any_of(row, ["a", "b"], array_path="items")
        assert row["items"][0]["a"] == 1


class TestMutateMapValueModelConstraint:
    """`map_path` threads a model mutation into a `dict[K, Model]` value model.

    A model-level constraint on a map's value model targets the value, not
    the row root. `map_path` names the map column; the mutation corrupts the
    single entry's value (stubbing one when the map is absent), so the
    generated `::invalid` row actually trips the value-model constraint.
    """

    def test_require_any_of_nulls_fields_in_map_value(self) -> None:
        row = {"subs": {"en": {"foo": 1, "bar": "x"}}}
        result = mutate_require_any_of(row, ["foo", "bar"], map_path="subs")
        assert result["subs"]["en"] == {"foo": None, "bar": None}

    def test_require_any_of_preserves_map_key(self) -> None:
        row = {"subs": {"en": {"foo": 1, "bar": "x"}}}
        result = mutate_require_any_of(row, ["foo", "bar"], map_path="subs")
        assert list(result["subs"]) == ["en"]

    def test_require_any_of_stubs_missing_map(self) -> None:
        row: dict = {"subs": None}
        result = mutate_require_any_of(row, ["foo", "bar"], map_path="subs")
        assert isinstance(result["subs"], dict) and result["subs"]
        assert next(iter(result["subs"].values())) == {"foo": None, "bar": None}

    def test_struct_path_descends_into_map_value(self) -> None:
        row = {"subs": {"en": {"inner": {"foo": 1, "bar": 2}}}}
        result = mutate_require_any_of(
            row, ["foo", "bar"], map_path="subs", struct_path="inner"
        )
        assert result["subs"]["en"]["inner"] == {"foo": None, "bar": None}

    def test_dotted_map_path(self) -> None:
        row = {"outer": {"subs": {"en": {"foo": 1, "bar": 2}}}}
        result = mutate_require_any_of(row, ["foo", "bar"], map_path="outer.subs")
        assert result["outer"]["subs"]["en"] == {"foo": None, "bar": None}

    def test_require_any_of_does_not_mutate_original(self) -> None:
        row = {"subs": {"en": {"foo": 1, "bar": 2}}}
        mutate_require_any_of(row, ["foo", "bar"], map_path="subs")
        assert row["subs"]["en"]["foo"] == 1

    def test_min_fields_set_nulls_fields_in_map_value(self) -> None:
        row = {"subs": {"en": {"a": 1, "b": 2}}}
        result = mutate_min_fields_set(row, ["a", "b"], map_path="subs")
        assert result["subs"]["en"] == {"a": None, "b": None}

    def test_require_if_sets_condition_and_nulls_in_map_value(self) -> None:
        row = {"subs": {"en": {"subtype": "other", "admin_level": 5}}}
        result = mutate_require_if(
            row, ["admin_level"], "subtype", "country", map_path="subs"
        )
        value = result["subs"]["en"]
        assert value["subtype"] == "country"
        assert value["admin_level"] is None

    def test_require_if_stubs_missing_map(self) -> None:
        row: dict = {"subs": None}
        result = mutate_require_if(
            row, ["admin_level"], "subtype", "country", map_path="subs"
        )
        value = next(iter(result["subs"].values()))
        assert value["subtype"] == "country"
        assert value["admin_level"] is None

    def test_forbid_if_sets_condition_and_ensures_non_null_in_map_value(self) -> None:
        row = {"subs": {"en": {"subtype": "other", "admin_level": None}}}
        result = mutate_forbid_if(
            row, ["admin_level"], "subtype", "country", map_path="subs"
        )
        value = result["subs"]["en"]
        assert value["subtype"] == "country"
        assert value["admin_level"] is not None


class TestMutateCompositeElementPath:
    """`element_path` threads a model mutation through mixed map/array nesting.

    Neither a scalar `array_path` nor `map_path` expresses a container-after-
    container descent. `element_path` carries the full descent to the target
    model, walked generically: array segments iterate every element, map
    `{value}` segments take the sole entry's value, struct segments navigate a
    field. It composes in either order -- map-then-array (`subs{value}[]`,
    dict[K, list[Model]]) and array-then-map (`items[].configs{value}`,
    list[dict[K, Model]]) -- reaching the model where fields are nulled. With
    only struct segments (`details`) it descends a plain struct-nested model.
    """

    def test_require_any_of_plain_struct(self) -> None:
        """A struct-only `element_path` nulls a struct-nested model's fields.

        A model constraint on a submodel reached through a plain struct field
        (`details`, no array or map) emits `element_path="details"`; the descent
        navigates the struct and nulls each field in place.
        """
        row = {"details": {"foo": 1, "bar": "x"}}
        result = mutate_require_any_of(row, ["foo", "bar"], element_path="details")
        assert result["details"] == {"foo": None, "bar": None}

    def test_require_any_of_map_then_array(self) -> None:
        row = {"subs": {"k": [{"foo": 1, "bar": 2}]}}
        result = mutate_require_any_of(
            row, ["foo", "bar"], element_path="subs{value}[]"
        )
        assert result["subs"]["k"] == [{"foo": None, "bar": None}]

    def test_require_any_of_map_then_array_preserves_map_key(self) -> None:
        row = {"subs": {"k": [{"foo": 1, "bar": 2}]}}
        result = mutate_require_any_of(
            row, ["foo", "bar"], element_path="subs{value}[]"
        )
        assert list(result["subs"]) == ["k"]

    def test_require_any_of_array_then_map(self) -> None:
        row = {"items": [{"configs": {"k": {"foo": 1, "bar": 2}}}]}
        result = mutate_require_any_of(
            row, ["foo", "bar"], element_path="items[].configs{value}"
        )
        assert result["items"][0]["configs"]["k"] == {"foo": None, "bar": None}

    def test_require_any_of_array_then_map_nulls_every_element(self) -> None:
        row = {
            "items": [
                {"configs": {"k": {"foo": 1, "bar": 2}}},
                {"configs": {"j": {"foo": 3, "bar": 4}}},
            ]
        }
        result = mutate_require_any_of(
            row, ["foo", "bar"], element_path="items[].configs{value}"
        )
        assert result["items"][0]["configs"]["k"] == {"foo": None, "bar": None}
        assert result["items"][1]["configs"]["j"] == {"foo": None, "bar": None}

    def test_require_any_of_composite_does_not_mutate_original(self) -> None:
        row = {"subs": {"k": [{"foo": 1, "bar": 2}]}}
        mutate_require_any_of(row, ["foo", "bar"], element_path="subs{value}[]")
        assert row["subs"]["k"] == [{"foo": 1, "bar": 2}]

    def test_min_fields_set_composite_descent(self) -> None:
        row = {"subs": {"k": [{"a": 1, "b": 2}]}}
        result = mutate_min_fields_set(row, ["a", "b"], element_path="subs{value}[]")
        assert result["subs"]["k"] == [{"a": None, "b": None}]

    def test_require_if_array_then_map(self) -> None:
        row = {"items": [{"configs": {"k": {"subtype": "other", "admin_level": 5}}}]}
        result = mutate_require_if(
            row,
            ["admin_level"],
            "subtype",
            "country",
            element_path="items[].configs{value}",
        )
        value = result["items"][0]["configs"]["k"]
        assert value["subtype"] == "country"
        assert value["admin_level"] is None

    def test_require_any_of_map_then_array_stubs_absent_map(self) -> None:
        """An absent map-then-array target stubs a list-shaped map value.

        `subs{value}[]` (`dict[K, list[Model]]`) with no `subs` key at all:
        the map's sole stubbed entry must itself be a list, since the map
        value type is `list[Model]`, not `Model`. Before the shape-aware
        stub, `_element_map_value` always stubbed a dict, and the trailing
        anonymous array segment then required its parent to already be a
        non-empty list -- raising `PathTraversalError` on this absent-map
        case instead of producing a mutated row.
        """
        row: dict = {}
        result = mutate_require_any_of(
            row, ["foo", "bar"], element_path="subs{value}[]"
        )
        value = next(iter(result["subs"].values()))
        assert value == [{"foo": None, "bar": None}]

    def test_require_any_of_map_then_array_then_struct_leaf(self) -> None:
        """`subs{value}[].inner` (map, array, then a struct field) also composes.

        Backs the report's "generalizes for free" claim for a composite
        descent with a trailing struct leaf, on both a present and an absent
        map -- the absent case exercises the shape-aware stub together with
        `_scaffold_struct_child`'s struct navigation.
        """
        row = {"subs": {"k": [{"inner": {"foo": 1, "bar": 2}}]}}
        result = mutate_require_any_of(
            row, ["foo", "bar"], element_path="subs{value}[].inner"
        )
        assert result["subs"]["k"] == [{"inner": {"foo": None, "bar": None}}]

    def test_require_any_of_map_then_array_then_struct_leaf_stubs_absent_map(
        self,
    ) -> None:
        row: dict = {}
        result = mutate_require_any_of(
            row, ["foo", "bar"], element_path="subs{value}[].inner"
        )
        value = next(iter(result["subs"].values()))
        assert value == [{"inner": {"foo": None, "bar": None}}]

    def test_forbid_if_composite_element_path_array_then_map(self) -> None:
        """`forbid_if` walks a composite `element_path` (array-then-map) too.

        Backs the report's "generalizes for free" claim: `mutate_forbid_if`
        takes the same `element_path` kwarg as `mutate_require_any_of` /
        `mutate_require_if`, threaded through the same `_apply_to_targets` ->
        `_descend_to_targets` machinery.
        """
        row = {"items": [{"configs": {"k": {"subtype": "other", "extra": None}}}]}
        result = mutate_forbid_if(
            row,
            ["extra"],
            "subtype",
            "country",
            element_path="items[].configs{value}",
        )
        value = result["items"][0]["configs"]["k"]
        assert value["subtype"] == "country"
        assert value["extra"] is not None


class TestMutateForbidIfNegate:
    def test_negate_changes_condition_value(self) -> None:
        """negate=True sets condition_field to something != condition_value."""
        row = {"subtype": "road", "destinations": [{"id": "x"}]}
        result = mutate_forbid_if(row, ["destinations"], "subtype", "road", negate=True)
        assert result["subtype"] != "road"
        assert result["destinations"] is not None

    def test_negate_preserves_non_matching_value(self) -> None:
        """When condition_field already != condition_value, leave it."""
        row = {"subtype": "water", "class": "canal"}
        result = mutate_forbid_if(row, ["class"], "subtype", "road", negate=True)
        assert result["subtype"] == "water"


class TestMutateRequireIfNegate:
    def test_negate_changes_condition_value(self) -> None:
        """negate=True sets condition_field to something != condition_value."""
        row = {"subtype": "road", "class": "motorway"}
        result = mutate_require_if(row, ["class"], "subtype", "road", negate=True)
        assert result["subtype"] != "road"
        assert result["class"] is None

    def test_negate_preserves_non_matching_value(self) -> None:
        """When condition_field already != condition_value, leave it."""
        row = {"subtype": "water", "class": "canal"}
        result = mutate_require_if(row, ["class"], "subtype", "road", negate=True)
        assert result["subtype"] == "water"
        assert result["class"] is None


class TestMutateUniqueItems:
    def test_duplicates_first_element(self) -> None:
        row = {"ids": [{"value": "a"}, {"value": "b"}]}
        result = mutate_unique_items(row, "ids")
        assert result["ids"][0] == result["ids"][1]
        assert len(result["ids"]) == 3

    def test_nested_path(self) -> None:
        row = {"outer": {"ids": [{"v": 1}, {"v": 2}]}}
        result = mutate_unique_items(row, "outer.ids")
        assert result["outer"]["ids"][0] == result["outer"]["ids"][1]

    def test_does_not_mutate_original(self) -> None:
        row = {"ids": [{"value": "a"}, {"value": "b"}]}
        mutate_unique_items(row, "ids")
        assert len(row["ids"]) == 2

    def test_bracket_path_enters_array_element(self) -> None:
        row = {"restrictions": [{"when": {"mode": [{"type": "car"}, {"type": "bus"}]}}]}
        result = mutate_unique_items(row, "restrictions[].when.mode")
        mode = result["restrictions"][0]["when"]["mode"]
        assert mode[0] == mode[1]
        assert len(mode) == 3

    def test_empty_array_returns_unchanged(self) -> None:
        row: dict = {"items": []}
        result = mutate_unique_items(row, "items")
        assert result["items"] == []

    def test_none_array_raises_traversal_error(self) -> None:
        row: dict = {"ids": None}
        with pytest.raises(PathTraversalError):
            mutate_unique_items(row, "ids")

    def test_missing_key_raises_traversal_error(self) -> None:
        row: dict = {"other": "x"}
        with pytest.raises(PathTraversalError):
            mutate_unique_items(row, "missing.nested")

    def test_nested_bracket_deep(self) -> None:
        """Two levels of bracket nesting."""
        row: dict = {"outer": [{"inner": [{"vals": [{"x": 1}]}]}]}
        result = mutate_unique_items(row, "outer[].inner[].vals")
        vals = result["outer"][0]["inner"][0]["vals"]
        assert vals[0] == vals[1]

    def test_terminal_bracket_duplicates_inner_list(self) -> None:
        """Terminal `[]` targets the inner list at element 0 of the named field."""
        row: dict = {"hierarchies": [[{"a": 1}]]}
        result = mutate_unique_items(row, "hierarchies[]")
        inner = result["hierarchies"][0]
        assert inner[0] == inner[1]
        assert len(inner) == 2

    def test_terminal_bracket_non_list_inner_raises(self) -> None:
        """Terminal `[]` with non-list content at element 0 raises."""
        row: dict = {"hierarchies": [{"a": 1}]}
        with pytest.raises(PathTraversalError):
            mutate_unique_items(row, "hierarchies[]")


class TestWalkStrict:
    def test_simple_struct(self) -> None:
        row = {"a": {"b": {"c": 42}}}
        result = _walk_strict(row, "a.b")
        assert result == {"c": 42}

    def test_root_returns_row(self) -> None:
        row = {"x": 1}
        assert _walk_strict(row, "") == row

    def test_missing_key_raises(self) -> None:
        row = {"a": {"b": 1}}
        with pytest.raises(PathTraversalError, match="Missing"):
            _walk_strict(row, "a.c")

    def test_null_intermediate_raises(self) -> None:
        row = {"a": None}
        with pytest.raises(PathTraversalError, match="a"):
            _walk_strict(row, "a.b")

    def test_error_message_includes_segment_name(self) -> None:
        row = {"outer": {"inner": None}}
        with pytest.raises(PathTraversalError, match="inner"):
            _walk_strict(row, "outer.inner.leaf")

    def test_error_message_includes_full_path(self) -> None:
        row = {"outer": None}
        with pytest.raises(PathTraversalError, match="outer.inner"):
            _walk_strict(row, "outer.inner")

    def test_array_segment_descends_to_element_zero(self) -> None:
        row = {"items": [{"val": 5}]}
        result = _walk_strict(row, "items[]")
        assert result == {"val": 5}

    def test_array_segment_empty_raises(self) -> None:
        row: dict[str, Any] = {"items": []}
        with pytest.raises(PathTraversalError, match="items"):
            _walk_strict(row, "items[]")

    def test_array_segment_with_struct_after(self) -> None:
        row = {"rules": [{"when": {"mode": [{"type": "car"}]}}]}
        result = _walk_strict(row, "rules[].when")
        assert result == {"mode": [{"type": "car"}]}

    def test_nested_list_descends_each_bracket_level(self) -> None:
        row = {"grid": [[{"val": 7}]]}
        result = _walk_strict(row, "grid[][]")
        assert result == {"val": 7}

    def test_nested_list_empty_inner_raises(self) -> None:
        row: dict[str, Any] = {"grid": [[]]}
        with pytest.raises(PathTraversalError, match="grid"):
            _walk_strict(row, "grid[][]")


class TestGetNested:
    def test_simple_lookup(self) -> None:
        row = {"a": {"b": 3}}
        assert _get_nested(row, "a.b") == 3

    def test_missing_key_returns_none(self) -> None:
        row = {"a": 1}
        assert _get_nested(row, "b") is None

    def test_missing_nested_key_returns_none(self) -> None:
        row = {"a": {"b": 1}}
        assert _get_nested(row, "a.c") is None

    def test_none_intermediate_returns_none(self) -> None:
        row = {"a": None}
        assert _get_nested(row, "a.b") is None

    def test_non_dict_intermediate_returns_none(self) -> None:
        row = {"a": [1, 2, 3]}
        assert _get_nested(row, "a.b") is None

    def test_rejects_array_path(self) -> None:
        with pytest.raises(ValueError, match="struct-only"):
            _get_nested({"items": [{"v": 1}]}, "items[].v")


class TestSetNested:
    def test_set_simple_field(self) -> None:
        d = {"a": 1}
        _set_nested(d, "a", 2)
        assert d["a"] == 2

    def test_set_nested_field(self) -> None:
        d = {"outer": {"inner": "old"}}
        _set_nested(d, "outer.inner", "new")
        assert d["outer"]["inner"] == "new"

    def test_null_value_through_none_intermediate_silent(self) -> None:
        """Nulling through a None intermediate is a no-op — already null."""
        d = {"a": None}
        _set_nested(d, "a.b", None)
        assert d["a"] is None

    def test_null_value_through_missing_intermediate_silent(self) -> None:
        d: dict = {}
        _set_nested(d, "a.b", None)
        assert "a" not in d

    def test_non_null_through_none_intermediate_raises_path_traversal_error(
        self,
    ) -> None:
        d = {"a": None}
        with pytest.raises(PathTraversalError, match="a"):
            _set_nested(d, "a.b", "value")

    def test_create_scaffolds_missing_intermediate(self) -> None:
        d: dict = {}
        _set_nested(d, "a.b", "v", create=True)
        assert d["a"]["b"] == "v"

    def test_create_scaffolds_none_intermediate(self) -> None:
        d: dict = {"a": None}
        _set_nested(d, "a.b", "v", create=True)
        assert d["a"]["b"] == "v"

    def test_rejects_array_path(self) -> None:
        with pytest.raises(ValueError, match="struct-only"):
            _set_nested({"items": []}, "items[].v", "x")
