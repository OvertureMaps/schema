"""Tests for the conformance test helpers."""

from __future__ import annotations

from typing import Any

import pytest

from ._support.helpers import PathTraversalError, deep_merge, set_at_path


class TestSetAtPath:
    def test_simple_field(self) -> None:
        row = {"name": "Alice"}
        result = set_at_path("name", "Bob")(row)
        assert result["name"] == "Bob"

    def test_does_not_mutate_original(self) -> None:
        row = {"name": "Alice"}
        set_at_path("name", "Bob")(row)
        assert row["name"] == "Alice"

    def test_nested_field(self) -> None:
        row = {"outer": {"inner": "old"}}
        result = set_at_path("outer.inner", "new")(row)
        assert result["outer"]["inner"] == "new"

    def test_array_index_zero(self) -> None:
        row = {"items": [{"value": 1}, {"value": 2}]}
        result = set_at_path("items[].value", 99)(row)
        assert result["items"][0]["value"] == 99
        assert result["items"][1]["value"] == 2  # untouched

    def test_set_to_none(self) -> None:
        row = {"country": "US"}
        result = set_at_path("country", None)(row)
        assert result["country"] is None

    def test_nested_array(self) -> None:
        row = {"rules": [{"tags": [{"v": "x"}]}]}
        result = set_at_path("rules[].tags[].v", "y")(row)
        assert result["rules"][0]["tags"][0]["v"] == "y"

    def test_deep_nested(self) -> None:
        row = {"a": {"b": {"c": {"d": "old"}}}}
        result = set_at_path("a.b.c.d", "new")(row)
        assert result["a"]["b"]["c"]["d"] == "new"

    def test_returns_callable(self) -> None:
        mutate = set_at_path("a.b", 1)
        assert callable(mutate)
        assert mutate({"a": {"b": 0}}) == {"a": {"b": 1}}


class TestSetAtPathTraversalErrors:
    def test_raises_on_empty_array(self) -> None:
        row: dict[str, Any] = {"items": []}
        with pytest.raises(PathTraversalError):
            set_at_path("items[].value", "x")(row)

    def test_raises_on_empty_nested_array(self) -> None:
        row: dict[str, Any] = {"names": {"rules": []}}
        with pytest.raises(PathTraversalError):
            set_at_path("names.rules[].value", "x")(row)

    def test_error_message_empty_array_names_path(self) -> None:
        row: dict[str, Any] = {"names": {"rules": []}}
        with pytest.raises(PathTraversalError, match="rules"):
            set_at_path("names.rules[].value", "x")(row)

    def test_raises_on_empty_path(self) -> None:
        mutator = set_at_path("", "x")
        with pytest.raises(PathTraversalError, match="Empty path"):
            mutator({})


class TestSetAtPathScaffolding:
    def test_null_struct_intermediate_scaffolded(self) -> None:
        row = {"id": "x", "names": None}
        result = set_at_path("names.primary", "test")(row)
        assert result["names"]["primary"] == "test"

    def test_null_array_intermediate_scaffolded(self) -> None:
        row = {"id": "x", "rules": None}
        result = set_at_path("rules[].value", "test")(row)
        assert result["rules"][0]["value"] == "test"

    def test_null_nested_struct_in_array_scaffolded(self) -> None:
        row = {"id": "x", "items": [{"nested": None}]}
        result = set_at_path("items[].nested.field", "test")(row)
        assert result["items"][0]["nested"]["field"] == "test"

    def test_deep_null_chain_scaffolded(self) -> None:
        row = {"id": "x", "a": None}
        result = set_at_path("a.b[].c", "test")(row)
        assert result["a"]["b"][0]["c"] == "test"

    def test_chained_calls_preserve_prior_content(self) -> None:
        """Chaining set_at_path preserves values set by prior calls."""
        row = {"items": None}
        with_kind = set_at_path("items[].kind", "height")(row)
        with_both = set_at_path("items[].value", 5.2)(with_kind)
        assert with_both["items"][0]["kind"] == "height"
        assert with_both["items"][0]["value"] == 5.2

    def test_chained_calls_through_deep_null_path(self) -> None:
        """Chained calls scaffold and preserve through deeply nested nulls."""
        row = {"outer": None}
        with_disc = set_at_path("outer[].inner[].dimension", "height")(row)
        with_value = set_at_path("outer[].inner[].value", None)(with_disc)
        assert with_value["outer"][0]["inner"][0]["dimension"] == "height"
        assert with_value["outer"][0]["inner"][0]["value"] is None


class TestSetAtPathMapProjection:
    """A trailing `{value}` / `{key}` marker mutates the map's single entry.

    An array-first map leaf (`items[].tags{value}`) descends the array to
    element 0, then corrupts the inner map in place -- preserving the other
    side of the entry so the check under test is the only violation.
    """

    def test_map_value_in_array(self) -> None:
        row = {"items": [{"tags": {"k": "abc"}}]}
        result = set_at_path("items[].tags{value}", "XY")(row)
        assert result["items"][0]["tags"] == {"k": "XY"}

    def test_map_value_does_not_mutate_original(self) -> None:
        row = {"items": [{"tags": {"k": "abc"}}]}
        set_at_path("items[].tags{value}", "XY")(row)
        assert row["items"][0]["tags"] == {"k": "abc"}

    def test_map_key_in_array_preserves_value(self) -> None:
        row = {"items": [{"tags": {"k": "abc"}}]}
        result = set_at_path("items[].tags{key}", "BAD")(row)
        assert result["items"][0]["tags"] == {"BAD": "abc"}

    def test_map_value_top_level(self) -> None:
        row = {"tags": {"k": "abc"}}
        result = set_at_path("tags{value}", "XY")(row)
        assert result["tags"] == {"k": "XY"}

    def test_raises_on_missing_map(self) -> None:
        row: dict[str, Any] = {"items": [{"tags": None}]}
        with pytest.raises(PathTraversalError, match="tags"):
            set_at_path("items[].tags{value}", "XY")(row)


class TestSetAtPathNonTerminalProjection:
    """A non-terminal `{value}` descends the sole entry's value and continues.

    `subs{value}[]` (dict[str, list[X]]) projects to the sole map value, then
    indexes element 0 of that list; `subs{value}{value}` (dict[str, dict[str,
    X]]) projects twice, reaching the inner map's sole value. A non-terminal
    `{key}` can't be descended -- a key is an immutable scalar -- so it raises.
    """

    def test_map_value_then_array(self) -> None:
        row = {"subs": {"k": ["abc"]}}
        result = set_at_path("subs{value}[]", "")(row)
        assert result["subs"]["k"] == [""]

    def test_map_value_then_map_value(self) -> None:
        row = {"subs": {"k": {"j": 7}}}
        result = set_at_path("subs{value}{value}", -1)(row)
        assert result["subs"]["k"] == {"j": -1}

    def test_map_value_then_array_does_not_mutate_original(self) -> None:
        row = {"subs": {"k": ["abc"]}}
        set_at_path("subs{value}[]", "")(row)
        assert row["subs"]["k"] == ["abc"]

    def test_map_value_then_map_value_does_not_mutate_original(self) -> None:
        row = {"subs": {"k": {"j": 7}}}
        set_at_path("subs{value}{value}", -1)(row)
        assert row["subs"]["k"] == {"j": 7}

    def test_map_value_preserves_sibling_map_entries(self) -> None:
        row = {"subs": {"k": ["abc"], "other": ["keep"]}}
        result = set_at_path("subs{value}[]", "")(row)
        assert result["subs"]["other"] == ["keep"]

    def test_non_terminal_key_projection_raises(self) -> None:
        row = {"subs": {"k": ["abc"]}}
        with pytest.raises(PathTraversalError, match="key"):
            set_at_path("subs{key}[]", "")(row)

    def test_missing_map_at_non_terminal_raises(self) -> None:
        row: dict[str, Any] = {"subs": None}
        with pytest.raises(PathTraversalError, match="subs"):
            set_at_path("subs{value}[]", "")(row)

    def test_map_value_then_two_array_levels(self) -> None:
        """`subs{value}[][]` (dict[str, list[list[X]]]) descends map, then two
        anonymous array levels, each indexing element 0.

        Backs the report's "generalizes for free" claim: no code path is
        specific to a single trailing array level, since `_array_slot`
        handles an anonymous segment identically regardless of how many
        precede it.
        """
        row = {"subs": {"k": [["abc", "def"]]}}
        result = set_at_path("subs{value}[][]", "")(row)
        assert result["subs"]["k"] == [["", "def"]]


class TestDeepMerge:
    def test_flat_merge(self) -> None:
        base = {"a": 1, "b": 2}
        scaffold = {"b": 3, "c": 4}
        assert deep_merge(base, scaffold) == {"a": 1, "b": 3, "c": 4}

    def test_nested_dict_merge(self) -> None:
        base = {"a": {"x": 1, "y": 2}}
        scaffold = {"a": {"y": 3, "z": 4}}
        assert deep_merge(base, scaffold) == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_array_replace(self) -> None:
        base = {"items": [{"a": 1}]}
        scaffold = {"items": [{"b": 2}]}
        assert deep_merge(base, scaffold) == {"items": [{"b": 2}]}

    def test_does_not_mutate_base(self) -> None:
        base = {"a": {"x": 1}}
        scaffold = {"a": {"y": 2}}
        result = deep_merge(base, scaffold)
        assert "y" not in base["a"]
        assert result == {"a": {"x": 1, "y": 2}}

    def test_empty_scaffold(self) -> None:
        base = {"a": 1}
        assert deep_merge(base, {}) == {"a": 1}

    def test_scaffold_adds_new_key(self) -> None:
        base = {"a": 1}
        scaffold = {"speed_limits": [{"max_speed": {"value": 60}}]}
        result = deep_merge(base, scaffold)
        assert result["a"] == 1
        assert result["speed_limits"] == [{"max_speed": {"value": 60}}]
