"""Tests for the wassirman walker."""

from __future__ import annotations

from typing import Annotated, Literal

from annotated_types import Ge, Le, MinLen
from overture.schema.codegen.extraction.model_extraction import (
    expand_model_tree,
    extract_model,
)
from overture.schema.codegen.wassirman.ir import RuleIR
from overture.schema.codegen.wassirman.walker import walk_feature
from overture.schema.system.field_constraint import UniqueItemsConstraint
from pydantic import BaseModel


def _walk(model: type[BaseModel], dataset_name: str) -> list[RuleIR]:
    spec = extract_model(model)
    expand_model_tree(spec)
    return walk_feature(spec, dataset_name)


class ScalarModel(BaseModel):
    """Model with scalar fields for testing basic rule emission."""

    theme: Literal["test"] = "test"
    type: Literal["scalar"] = "scalar"
    id: str
    version: Annotated[int, Ge(0)]
    name: str | None = None
    score: Annotated[float, Ge(0.0), Le(1.0)] | None = None


class TestSkippedFields:
    def test_theme_skipped(self) -> None:
        rules = _walk(ScalarModel, "scalar")
        names = [r.name for r in rules]
        assert not any("theme" in n for n in names)

    def test_type_skipped(self) -> None:
        rules = _walk(ScalarModel, "scalar")
        names = [r.name for r in rules]
        assert not any(n.startswith("scalar.type") for n in names)


class TestNotNullRules:
    def test_required_field(self) -> None:
        rules = _walk(ScalarModel, "scalar")
        not_null_rules = [r for r in rules if r.name == "scalar.id.not_null"]
        assert len(not_null_rules) == 1
        assert not_null_rules[0].check == "not_null"
        assert not_null_rules[0].column == "id"
        assert not_null_rules[0].when is None

    def test_optional_field_no_not_null(self) -> None:
        rules = _walk(ScalarModel, "scalar")
        assert not any(r.name == "scalar.name.not_null" for r in rules)


class TestNumericBounds:
    def test_ge_emits_gte(self) -> None:
        rules = _walk(ScalarModel, "scalar")
        version_rules = [r for r in rules if r.column == "version" and r.check == "gte"]
        assert len(version_rules) == 1
        assert version_rules[0].value == 0

    def test_ge_le_collapses_to_between(self) -> None:
        rules = _walk(ScalarModel, "scalar")
        between_rules = [
            r for r in rules if r.column == "score" and r.check == "between"
        ]
        assert len(between_rules) == 1
        assert between_rules[0].value == [0.0, 1.0]


class NestedChild(BaseModel):
    value: Annotated[str, MinLen(1)]
    variant: Literal["a", "b"]


class ListParent(BaseModel):
    theme: Literal["test"] = "test"
    type: Literal["listy"] = "listy"
    id: str
    items: Annotated[list[NestedChild], MinLen(1), UniqueItemsConstraint()] | None = (
        None
    )


class OptionalParent(BaseModel):
    theme: Literal["test"] = "test"
    type: Literal["opty"] = "opty"
    id: str
    nested: NestedChild | None = None


class TestListColumns:
    def test_list_field_min_list_length(self) -> None:
        rules = _walk(ListParent, "listy")
        min_len_rules = [
            r for r in rules if r.column == "items" and r.check == "min_list_length"
        ]
        assert len(min_len_rules) == 1
        assert min_len_rules[0].value == 1
        # Container-level check: no list_columns (items itself isn't inside another list)
        assert min_len_rules[0].list_columns is None

    def test_list_element_gets_list_columns(self) -> None:
        rules = _walk(ListParent, "listy")
        value_rules = [r for r in rules if r.column == "items.value"]
        assert len(value_rules) > 0
        for r in value_rules:
            if r.list_columns is not None:
                assert "items" in r.list_columns

    def test_unique_on_list(self) -> None:
        rules = _walk(ListParent, "listy")
        unique_rules = [r for r in rules if r.column == "items" and r.check == "unique"]
        assert len(unique_rules) == 1


class TestParentOptionalityGuard:
    def test_required_child_under_optional_parent(self) -> None:
        rules = _walk(OptionalParent, "opty")
        value_not_null = [
            r for r in rules if r.column == "nested.value" and r.check == "not_null"
        ]
        assert len(value_not_null) == 1
        assert value_not_null[0].when is not None
        assert value_not_null[0].when.column == "nested"
        assert value_not_null[0].when.check == "not_null"

    def test_required_child_under_required_parent_no_guard(self) -> None:
        class RequiredParent(BaseModel):
            theme: Literal["test"] = "test"
            type: Literal["reqp"] = "reqp"
            id: str
            nested: NestedChild

        rules = _walk(RequiredParent, "reqp")
        value_not_null = [
            r for r in rules if r.column == "nested.value" and r.check == "not_null"
        ]
        assert len(value_not_null) == 1
        assert value_not_null[0].when is None
