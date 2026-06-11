"""Tests for markdown type formatting."""

from enum import Enum
from pathlib import PurePosixPath
from typing import Literal, NewType

from overture.schema.codegen.extraction.field import (
    AnyScalar,
    ArrayOf,
    LiteralScalar,
    Scalar,
    UnionRef,
)
from overture.schema.codegen.extraction.specs import FieldSpec, TypeIdentity
from overture.schema.codegen.extraction.type_analyzer import analyze_type
from overture.schema.codegen.markdown.link_computation import LinkContext
from overture.schema.codegen.markdown.type_format import (
    _registry_name,
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
        assert format_type(_make_field(str)) == "`string`"

    def test_optional_adds_qualifier(self) -> None:
        assert (
            format_type(_make_field(str | None, is_required=False))
            == "`string` (optional)"
        )

    def test_literal_renders_as_quoted_value(self) -> None:
        assert format_type(_make_field(Literal["places"])) == '`"places"`'

    def test_multi_value_literal_renders_comma_separated(self) -> None:
        assert (
            format_type(_make_field(Literal["a", "b", "c"]))
            == '`"a"` \\| `"b"` \\| `"c"`'
        )

    def test_enum_without_context_renders_as_code(self) -> None:
        class Color(str, Enum):
            RED = "red"

        assert format_type(_make_field(Color)) == "`Color`"

    def test_enum_with_link_context(self) -> None:
        class Color(str, Enum):
            RED = "red"

        field = _make_field(Color)
        ctx = LinkContext(
            page_path=PurePosixPath("buildings/building/building.md"),
            registry={
                TypeIdentity(Color, "Color"): PurePosixPath("types/enums/color.md")
            },
        )
        assert format_type(field, ctx) == "[`Color`](../../types/enums/color.md)"

    def test_list_of_primitives(self) -> None:
        assert format_type(_make_field(list[str])) == "`list<string>`"

    def test_nested_list_of_primitives(self) -> None:
        assert format_type(_make_field(list[list[str]])) == "`list<list<string>>`"

    def test_registered_primitive_not_linked(self) -> None:
        result = format_type(_make_field(int32))
        assert result == "`int32`"
        assert "](int32.md)" not in result


def _make_field(
    annotation: object,
    *,
    name: str = "x",
    is_required: bool = True,
    is_optional: bool = False,
) -> FieldSpec:
    """Build a FieldSpec from an annotation for test convenience."""
    from overture.schema.codegen.extraction.field import FieldShape

    if isinstance(annotation, (Scalar, ArrayOf, UnionRef)):
        shape: FieldShape = annotation  # type: ignore[assignment]
    else:
        shape, resolved_optional, _ = analyze_type(annotation)
        is_optional = is_optional or resolved_optional
    return FieldSpec(
        name=name,
        shape=shape,
        description=None,
        is_required=is_required,
        is_optional=is_optional,
    )


def _union_ref(members: list[type]) -> UnionRef:
    """Build a UnionRef for tests without running through extract_union."""
    from overture.schema.codegen.extraction.specs import UnionSpec
    from pydantic import BaseModel

    union_spec = UnionSpec(
        name=members[0].__name__,
        description=None,
        annotated_fields=[],
        members=members,  # type: ignore[arg-type]
        discriminator_field=None,
        discriminator_mapping=None,
        source_annotation=object(),
        common_base=BaseModel,
    )
    return UnionRef(union=union_spec)


class TestFormatUnionType:
    """Tests for union FieldShape in format_type."""

    def test_union_renders_all_members(self) -> None:
        result = format_type(_make_field(_union_ref([_ModelA, _ModelB])))
        assert "`_ModelA`" in result
        assert "`_ModelB`" in result
        # Pipe separator escaped for table cells
        assert r"\|" in result

    def test_union_with_link_context_links_each_member(self) -> None:
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
        result = format_type(_make_field(_union_ref([_ModelA, _ModelB])), ctx)
        assert "[`_ModelA`](types/model_a.md)" in result
        assert "[`_ModelB`](types/model_b.md)" in result

    def test_optional_union_adds_qualifier(self) -> None:
        result = format_type(
            _make_field(
                _union_ref([_ModelA, _ModelB]), is_required=False, is_optional=True
            )
        )
        assert "(optional)" in result
        assert "`_ModelA`" in result
        assert "`_ModelB`" in result

    def test_list_of_union_adds_qualifier(self) -> None:
        """list[union] renders with (list) qualifier."""
        shape = ArrayOf(element=_union_ref([_ModelA, _ModelB]))
        result = format_type(_make_field(shape))
        assert "(list)" in result
        assert "`_ModelA`" in result
        assert "`_ModelB`" in result

    def test_union_members_unlinked_without_context(self) -> None:
        result = format_type(_make_field(_union_ref([_ModelA, _ModelB])))
        # No markdown links without context
        assert "]()" not in result
        assert "[`" not in result

    def test_union_partial_links(self) -> None:
        """Members with pages get linked; members without don't."""
        ctx = LinkContext(
            page_path=PurePosixPath("theme/feature/feature.md"),
            registry={
                TypeIdentity(_ModelA, "_ModelA"): PurePosixPath(
                    "theme/feature/types/model_a.md"
                )
            },
        )
        result = format_type(_make_field(_union_ref([_ModelA, _ModelB])), ctx)
        assert "[`_ModelA`](types/model_a.md)" in result
        assert "`_ModelB`" in result
        # _ModelB should NOT be linked
        assert "[`_ModelB`]" not in result


class TestScalarVariantRendering:
    """format_type and _registry_name handle all three Scalar variants correctly."""

    def test_registry_name_any_scalar(self) -> None:
        assert _registry_name(AnyScalar()) == "Any"

    def test_registry_name_literal_scalar(self) -> None:
        assert _registry_name(LiteralScalar(values=("road",))) == "Literal"

    def test_any_scalar_renders_as_Any(self) -> None:
        assert format_type(_make_field(AnyScalar())) == "`Any`"

    def test_literal_scalar_renders_first_value_quoted(self) -> None:
        # LiteralScalar goes through the Literal path in format_type, not _registry_name
        assert format_type(_make_field(LiteralScalar(values=("road",)))) == '`"road"`'

    def test_literal_scalar_multi_value(self) -> None:
        result = format_type(_make_field(LiteralScalar(values=("a", "b"))))
        assert '`"a"`' in result
        assert '`"b"`' in result

    def test_list_of_literal_single_value(self) -> None:
        assert format_type(_make_field(list[Literal["road"]])) == '`list<"road">`'

    def test_list_of_literal_multi_value(self) -> None:
        assert format_type(_make_field(list[Literal["a", "b"]])) == '`list<"a" | "b">`'


class TestPydanticTypeLinking:
    """Tests for PRIMITIVE types with pages getting linked."""

    def test_pydantic_type_linked_when_in_registry(self) -> None:
        ctx = LinkContext(
            page_path=PurePosixPath("places/place/place.md"),
            registry={
                TypeIdentity(HttpUrl, "HttpUrl"): PurePosixPath(
                    "pydantic/networks/http_url.md"
                )
            },
        )
        result = format_type(_make_field(HttpUrl), ctx)
        assert "[`HttpUrl`]" in result
        assert "pydantic/networks/http_url.md" in result

    def test_pydantic_type_unlinked_without_registry_entry(self) -> None:
        ctx = LinkContext(
            page_path=PurePosixPath("places/place/place.md"),
            registry={},
        )
        result = format_type(_make_field(HttpUrl), ctx)
        assert result == "`HttpUrl`"
        assert "[" not in result

    def test_list_of_pydantic_type_linked(self) -> None:
        ctx = LinkContext(
            page_path=PurePosixPath("places/place/place.md"),
            registry={
                TypeIdentity(HttpUrl, "HttpUrl"): PurePosixPath(
                    "pydantic/networks/http_url.md"
                )
            },
        )
        result = format_type(_make_field(list[HttpUrl]), ctx)
        assert "HttpUrl" in result
        assert "pydantic/networks/http_url.md" in result

    def test_registered_primitive_links_to_aggregate_page(self) -> None:
        """int32 links to the primitives aggregate page when in registry."""
        ctx = LinkContext(
            page_path=PurePosixPath("places/place/place.md"),
            registry={
                TypeIdentity(int32, "int32"): PurePosixPath(
                    "system/primitive/primitives.md"
                )
            },
        )
        result = format_type(_make_field(int32), ctx)
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
        result = format_type(_make_field(list[ScalarNT]))
        assert "list<" in result
        assert "ScalarNT" in result
        assert "(list)" not in result

    def test_newtype_wrapping_list_renders_qualifier(self) -> None:
        """NewType wrapping list[X] renders as Name (list)."""
        ListNT = NewType("ListNT", list[str])
        result = format_type(_make_field(ListNT))
        assert "(list)" in result
        assert "ListNT" in result

    def test_list_of_scalar_newtype_with_link(self) -> None:
        """list[ScalarNewType] with link context renders linked list<Name>."""
        ScalarNT = NewType("ScalarNT", str)
        ctx = LinkContext(
            page_path=PurePosixPath("places/place/place.md"),
            registry={
                TypeIdentity(ScalarNT, "ScalarNT"): PurePosixPath("system/scalar_nt.md")
            },
        )
        result = format_type(_make_field(list[ScalarNT]), ctx)
        assert "list<" in result
        assert "ScalarNT" in result
        assert "system/scalar_nt.md" in result
        assert "(list)" not in result

    def test_nested_list_of_scalar_newtype_renders_nested_list_syntax(self) -> None:
        """list[list[ScalarNewType]] renders as list<list<Name>>."""
        ScalarNT = NewType("ScalarNT", str)
        result = format_type(_make_field(list[list[ScalarNT]]))
        assert "list<" in result
        assert "list<`" in result or "`list<list<" in result
        assert "ScalarNT" in result
        assert "(list)" not in result


class TestFormatUnderlyingUnionType:
    """Tests for union FieldShape in format_underlying_type."""

    def test_union_renders_all_members(self) -> None:
        shape = _union_ref([_ModelA, _ModelB])
        result = format_underlying_type(shape)
        assert result == "`_ModelA` | `_ModelB`"

    def test_union_with_link_context(self) -> None:
        shape = _union_ref([_ModelA, _ModelB])
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
        result = format_underlying_type(shape, ctx)
        assert "[`_ModelA`](../theme/feature/types/model_a.md)" in result
        assert "[`_ModelB`](../theme/feature/types/model_b.md)" in result
