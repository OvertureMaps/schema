"""Tests for markdown type formatting."""

from enum import Enum
from pathlib import PurePosixPath
from typing import Literal, NewType

from overture.schema.codegen.extraction.specs import FieldSpec, TypeIdentity
from overture.schema.codegen.extraction.type_analyzer import (
    TypeInfo,
    TypeKind,
    analyze_type,
)
from overture.schema.codegen.markdown.link_computation import LinkContext
from overture.schema.codegen.markdown.type_format import (
    format_dict_type,
    format_type,
    format_underlying_type,
)
from overture.schema.system.primitive import int32
from pydantic import BaseModel, HttpUrl


class _ModelA(BaseModel):
    x: int


class _ModelB(BaseModel):
    y: str


class TestFormatType:
    """Tests for format_type."""

    def test_plain_str_renders_as_string(self) -> None:
        ti = analyze_type(str)
        assert format_type(_make_field(ti)) == "`string`"

    def test_optional_adds_qualifier(self) -> None:
        ti = analyze_type(str | None)
        assert format_type(_make_field(ti, is_required=False)) == "`string` (optional)"

    def test_literal_renders_as_quoted_value(self) -> None:
        ti = analyze_type(Literal["places"])
        assert format_type(_make_field(ti)) == '`"places"`'

    def test_multi_value_literal_renders_comma_separated(self) -> None:
        ti = analyze_type(Literal["a", "b", "c"])
        assert format_type(_make_field(ti)) == '`"a"` \\| `"b"` \\| `"c"`'

    def test_enum_without_context_renders_as_code(self) -> None:
        class Color(str, Enum):
            RED = "red"

        ti = analyze_type(Color)
        assert format_type(_make_field(ti)) == "`Color`"

    def test_enum_with_link_context(self) -> None:
        class Color(str, Enum):
            RED = "red"

        ti = analyze_type(Color)
        field = _make_field(ti)
        ctx = LinkContext(
            page_path=PurePosixPath("buildings/building/building.md"),
            registry={
                TypeIdentity(Color, "Color"): PurePosixPath("types/enums/color.md")
            },
        )
        assert format_type(field, ctx) == "[`Color`](../../types/enums/color.md)"

    def test_list_of_primitives(self) -> None:
        ti = analyze_type(list[str])
        assert format_type(_make_field(ti)) == "`list<string>`"

    def test_nested_list_of_primitives(self) -> None:
        ti = analyze_type(list[list[str]])
        assert format_type(_make_field(ti)) == "`list<list<string>>`"

    def test_registered_primitive_not_linked(self) -> None:
        ti = analyze_type(int32)
        result = format_type(_make_field(ti))
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


def _make_field(
    ti: TypeInfo, *, name: str = "x", is_required: bool = True
) -> FieldSpec:
    """Build a FieldSpec for test convenience."""
    return FieldSpec(name=name, type_info=ti, description=None, is_required=is_required)


class TestFormatUnionType:
    """Tests for UNION-kind TypeInfo in format_type."""

    def test_union_renders_all_members(self) -> None:
        ti = analyze_type(_ModelA | _ModelB)
        result = format_type(_make_field(ti))
        assert "`_ModelA`" in result
        assert "`_ModelB`" in result
        # Pipe separator escaped for table cells
        assert r"\|" in result

    def test_union_with_link_context_links_each_member(self) -> None:
        ti = analyze_type(_ModelA | _ModelB)
        ctx = LinkContext(
            page_path=PurePosixPath("theme/feature/feature.md"),
            registry={
                TypeIdentity(_ModelA, "_ModelA"): PurePosixPath(
                    "theme/feature/types/model_a.md"
                ),
                TypeIdentity(_ModelB, "_ModelB"): PurePosixPath(
                    "theme/feature/types/model_b.md"
                ),
            },
        )
        result = format_type(_make_field(ti), ctx)
        assert "[`_ModelA`](types/model_a.md)" in result
        assert "[`_ModelB`](types/model_b.md)" in result

    def test_optional_union_adds_qualifier(self) -> None:
        ti = analyze_type(_ModelA | _ModelB | None)
        result = format_type(_make_field(ti, is_required=False))
        assert "(optional)" in result
        assert "`_ModelA`" in result
        assert "`_ModelB`" in result

    def test_list_of_union_adds_qualifier(self) -> None:
        ti = TypeInfo(
            base_type="_ModelA",
            kind=TypeKind.UNION,
            list_depth=1,
            union_members=(_ModelA, _ModelB),
        )
        result = format_type(_make_field(ti))
        assert "(list)" in result
        assert "`_ModelA`" in result
        assert "`_ModelB`" in result

    def test_union_members_unlinked_without_context(self) -> None:
        ti = analyze_type(_ModelA | _ModelB)
        result = format_type(_make_field(ti))
        # No markdown links without context
        assert "]()" not in result
        assert "[`" not in result

    def test_union_partial_links(self) -> None:
        """Members with pages get linked; members without don't."""
        ti = analyze_type(_ModelA | _ModelB)
        ctx = LinkContext(
            page_path=PurePosixPath("theme/feature/feature.md"),
            registry={
                TypeIdentity(_ModelA, "_ModelA"): PurePosixPath(
                    "theme/feature/types/model_a.md"
                )
            },
        )
        result = format_type(_make_field(ti), ctx)
        assert "[`_ModelA`](types/model_a.md)" in result
        assert "`_ModelB`" in result
        # _ModelB should NOT be linked
        assert "[`_ModelB`]" not in result


class TestPydanticTypeLinking:
    """Tests for PRIMITIVE types with pages getting linked."""

    def test_pydantic_type_linked_when_in_registry(self) -> None:
        ti = analyze_type(HttpUrl)
        field = _make_field(ti)
        ctx = LinkContext(
            page_path=PurePosixPath("places/place/place.md"),
            registry={
                TypeIdentity(HttpUrl, "HttpUrl"): PurePosixPath(
                    "pydantic/networks/http_url.md"
                )
            },
        )
        result = format_type(field, ctx)
        assert "[`HttpUrl`]" in result
        assert "pydantic/networks/http_url.md" in result

    def test_pydantic_type_unlinked_without_registry_entry(self) -> None:
        ti = analyze_type(HttpUrl)
        field = _make_field(ti)
        ctx = LinkContext(
            page_path=PurePosixPath("places/place/place.md"),
            registry={},
        )
        result = format_type(field, ctx)
        assert result == "`HttpUrl`"
        assert "[" not in result

    def test_list_of_pydantic_type_linked(self) -> None:
        ti = analyze_type(list[HttpUrl])
        field = _make_field(ti)
        ctx = LinkContext(
            page_path=PurePosixPath("places/place/place.md"),
            registry={
                TypeIdentity(HttpUrl, "HttpUrl"): PurePosixPath(
                    "pydantic/networks/http_url.md"
                )
            },
        )
        result = format_type(field, ctx)
        assert "HttpUrl" in result
        assert "pydantic/networks/http_url.md" in result

    def test_registered_primitive_links_to_aggregate_page(self) -> None:
        """int32 links to the primitives aggregate page when in registry."""
        ti = analyze_type(int32)
        field = _make_field(ti)
        ctx = LinkContext(
            page_path=PurePosixPath("places/place/place.md"),
            registry={
                TypeIdentity(int32, "int32"): PurePosixPath(
                    "system/primitive/primitives.md"
                )
            },
        )
        result = format_type(field, ctx)
        assert "[`int32`]" in result
        assert "system/primitive/primitives.md" in result


class TestListOfSemanticNewtype:
    """Tests for list[SemanticNewType] rendering.

    When a scalar NewType appears inside list[], the type renders as
    list<NewTypeName> rather than NewTypeName (list). The (list) qualifier
    is reserved for NewTypes that internally wrap a list.
    """

    def test_list_of_scalar_newtype_renders_list_syntax(self) -> None:
        """list[ScalarNewType] renders as list<Name>, not Name (list)."""
        ScalarNT = NewType("ScalarNT", str)
        ti = analyze_type(list[ScalarNT])
        result = format_type(_make_field(ti))
        assert "list<" in result
        assert "ScalarNT" in result
        assert "(list)" not in result

    def test_newtype_wrapping_list_renders_qualifier(self) -> None:
        """NewType wrapping list[X] renders as Name (list)."""
        ListNT = NewType("ListNT", list[str])
        ti = analyze_type(ListNT)
        result = format_type(_make_field(ti))
        assert "(list)" in result
        assert "ListNT" in result

    def test_list_of_scalar_newtype_with_link(self) -> None:
        """list[ScalarNewType] with link context renders linked list<Name>."""
        ScalarNT = NewType("ScalarNT", str)
        ti = analyze_type(list[ScalarNT])
        field = _make_field(ti)
        ctx = LinkContext(
            page_path=PurePosixPath("places/place/place.md"),
            registry={
                TypeIdentity(ScalarNT, "ScalarNT"): PurePosixPath("system/scalar_nt.md")
            },
        )
        result = format_type(field, ctx)
        assert "list<" in result
        assert "ScalarNT" in result
        assert "system/scalar_nt.md" in result
        assert "(list)" not in result

    def test_nested_list_of_scalar_newtype_renders_nested_list_syntax(self) -> None:
        """list[list[ScalarNewType]] renders as list<list<Name>>."""
        ScalarNT = NewType("ScalarNT", str)
        ti = analyze_type(list[list[ScalarNT]])
        result = format_type(_make_field(ti))
        assert "list<" in result
        assert "list<`" in result or "`list<list<" in result
        assert "ScalarNT" in result
        assert "(list)" not in result


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
                TypeIdentity(_ModelA, "_ModelA"): PurePosixPath(
                    "theme/feature/types/model_a.md"
                ),
                TypeIdentity(_ModelB, "_ModelB"): PurePosixPath(
                    "theme/feature/types/model_b.md"
                ),
            },
        )
        result = format_underlying_type(ti, ctx)
        assert "[`_ModelA`](../theme/feature/types/model_a.md)" in result
        assert "[`_ModelB`](../theme/feature/types/model_b.md)" in result
