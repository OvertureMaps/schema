"""Tests for markdown type formatting."""

from enum import Enum
from pathlib import PurePosixPath
from typing import Literal, NewType

from overture.schema.codegen.link_computation import LinkContext
from overture.schema.codegen.markdown_type_format import (
    format_dict_type,
    format_type,
    format_underlying_type,
)
from overture.schema.codegen.specs import FieldSpec
from overture.schema.codegen.type_analyzer import TypeInfo, TypeKind, analyze_type
from overture.schema.system.primitive import int32
from pydantic import BaseModel


class _ModelA(BaseModel):
    x: int


class _ModelB(BaseModel):
    y: str


class TestFormatType:
    """Tests for format_type."""

    def test_plain_str_renders_as_string(self) -> None:
        ti = analyze_type(str)
        field = FieldSpec(name="x", type_info=ti, description=None, is_required=True)
        assert format_type(field) == "`string`"

    def test_optional_adds_qualifier(self) -> None:
        ti = analyze_type(str | None)
        field = FieldSpec(name="x", type_info=ti, description=None, is_required=False)
        assert format_type(field) == "`string` (optional)"

    def test_literal_renders_as_quoted_value(self) -> None:
        ti = analyze_type(Literal["places"])
        field = FieldSpec(name="x", type_info=ti, description=None, is_required=True)
        assert format_type(field) == '`"places"`'

    def test_enum_without_context_renders_as_code(self) -> None:
        class Color(str, Enum):
            RED = "red"

        ti = analyze_type(Color)
        field = FieldSpec(name="x", type_info=ti, description=None, is_required=True)
        assert format_type(field) == "`Color`"

    def test_enum_with_link_context(self) -> None:
        class Color(str, Enum):
            RED = "red"

        ti = analyze_type(Color)
        field = FieldSpec(name="x", type_info=ti, description=None, is_required=True)
        ctx = LinkContext(
            page_path=PurePosixPath("buildings/building/building.md"),
            registry={"Color": PurePosixPath("types/enums/color.md")},
        )
        assert format_type(field, ctx) == "[`Color`](../../types/enums/color.md)"

    def test_list_of_primitives(self) -> None:
        ti = analyze_type(list[str])
        field = FieldSpec(name="x", type_info=ti, description=None, is_required=True)
        assert format_type(field) == "`list<string>`"

    def test_registered_primitive_not_linked(self) -> None:
        ti = analyze_type(int32)
        field = FieldSpec(name="x", type_info=ti, description=None, is_required=True)
        result = format_type(field)
        assert result == "`int32`"
        assert "](int32.md)" not in result


class TestFormatDictType:
    """Tests for format_dict_type."""

    def test_simple_dict_renders_as_map(self) -> None:
        ti = analyze_type(dict[str, int])
        result = format_dict_type(ti)
        assert result == "map<string, int64>"

    def test_dict_with_newtype_shows_semantic_name(self) -> None:
        MyKey = NewType("MyKey", str)
        ti = analyze_type(dict[MyKey, int])
        result = format_dict_type(ti)
        assert result == "map<MyKey, int64>"


def _make_union_field(ti: TypeInfo, *, is_required: bool = True) -> FieldSpec:
    """Build a FieldSpec wrapping a union TypeInfo for test convenience."""
    return FieldSpec(name="x", type_info=ti, description=None, is_required=is_required)


class TestFormatUnionType:
    """Tests for UNION-kind TypeInfo in format_type."""

    def test_union_renders_all_members(self) -> None:
        ti = analyze_type(_ModelA | _ModelB)
        result = format_type(_make_union_field(ti))
        assert "`_ModelA`" in result
        assert "`_ModelB`" in result
        # Pipe separator escaped for table cells
        assert r"\|" in result

    def test_union_with_link_context_links_each_member(self) -> None:
        ti = analyze_type(_ModelA | _ModelB)
        ctx = LinkContext(
            page_path=PurePosixPath("theme/feature/feature.md"),
            registry={
                "_ModelA": PurePosixPath("theme/feature/types/model_a.md"),
                "_ModelB": PurePosixPath("theme/feature/types/model_b.md"),
            },
        )
        result = format_type(_make_union_field(ti), ctx)
        assert "[`_ModelA`](types/model_a.md)" in result
        assert "[`_ModelB`](types/model_b.md)" in result

    def test_optional_union_adds_qualifier(self) -> None:
        ti = analyze_type(_ModelA | _ModelB | None)
        result = format_type(_make_union_field(ti, is_required=False))
        assert "(optional)" in result
        assert "`_ModelA`" in result
        assert "`_ModelB`" in result

    def test_list_of_union_adds_qualifier(self) -> None:
        ti = TypeInfo(
            base_type="_ModelA",
            kind=TypeKind.UNION,
            is_list=True,
            union_members=(_ModelA, _ModelB),
        )
        result = format_type(_make_union_field(ti))
        assert "(list)" in result
        assert "`_ModelA`" in result
        assert "`_ModelB`" in result

    def test_union_members_unlinked_without_context(self) -> None:
        ti = analyze_type(_ModelA | _ModelB)
        result = format_type(_make_union_field(ti))
        # No markdown links without context
        assert "]()" not in result
        assert "[`" not in result

    def test_union_partial_links(self) -> None:
        """Members with pages get linked; members without don't."""
        ti = analyze_type(_ModelA | _ModelB)
        ctx = LinkContext(
            page_path=PurePosixPath("theme/feature/feature.md"),
            registry={"_ModelA": PurePosixPath("theme/feature/types/model_a.md")},
        )
        result = format_type(_make_union_field(ti), ctx)
        assert "[`_ModelA`](types/model_a.md)" in result
        assert "`_ModelB`" in result
        # _ModelB should NOT be linked
        assert "[`_ModelB`]" not in result


class TestFormatUnderlyingUnionType:
    """Tests for UNION-kind TypeInfo in format_underlying_type."""

    def test_union_renders_all_members(self) -> None:
        ti = analyze_type(_ModelA | _ModelB)
        result = format_underlying_type(ti)
        assert result == "`_ModelA` | `_ModelB`"

    def test_union_with_link_context(self) -> None:
        ti = analyze_type(_ModelA | _ModelB)
        ctx = LinkContext(
            page_path=PurePosixPath("types/my_union.md"),
            registry={
                "_ModelA": PurePosixPath("theme/feature/types/model_a.md"),
                "_ModelB": PurePosixPath("theme/feature/types/model_b.md"),
            },
        )
        result = format_underlying_type(ti, ctx)
        assert "[`_ModelA`](../theme/feature/types/model_a.md)" in result
        assert "[`_ModelB`](../theme/feature/types/model_b.md)" in result
