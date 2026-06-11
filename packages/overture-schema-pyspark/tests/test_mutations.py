"""Tests for model-level mutation functions."""

import pytest

from ._support.helpers import PathTraversalError
from ._support.mutations import (
    mutate_forbid_if,
    mutate_min_fields_set,
    mutate_radio_group,
    mutate_require_any_of,
    mutate_require_if,
    mutate_unique_items,
)


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
