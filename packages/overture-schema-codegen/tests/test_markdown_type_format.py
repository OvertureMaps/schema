"""Tests for markdown type formatting."""

from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Literal, NewType

import pytest
from overture.schema.codegen.extraction.field import (
    AnyScalar,
    ArrayOf,
    FieldShape,
    LiteralScalar,
    NewTypeShape,
    Primitive,
    Scalar,
    UnionRef,
)
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.extraction.specs import FieldSpec, TypeIdentity, UnionSpec
from overture.schema.codegen.extraction.type_analyzer import analyze_type
from overture.schema.codegen.markdown.link_computation import LinkContext
from overture.schema.codegen.markdown.type_format import (
    _bare_map_side_name,
    _registry_name,
    format_type,
    format_underlying_type,
)
from overture.schema.system.geometric import BBox, Geometry
from overture.schema.system.numeric import int32
from pydantic import BaseModel, HttpUrl


class _ModelA(BaseModel):
    x: int


class _ModelB(BaseModel):
    y: str


class _OuterWithModelMap(BaseModel):
    m: dict[str, _ModelB]


class _OuterWithModelListMap(BaseModel):
    m: dict[str, list[_ModelB]]


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

    def test_geometry_links_to_aggregate_page(self) -> None:
        field = _make_field(Geometry)
        ctx = LinkContext(
            page_path=PurePosixPath("buildings/building/building.md"),
            registry={
                TypeIdentity(Geometry, "Geometry"): PurePosixPath("system/geometric.md")
            },
        )
        assert format_type(field, ctx) == "[`geometry`](../../system/geometric.md)"

    def test_bbox_links_to_aggregate_page(self) -> None:
        field = _make_field(BBox)
        ctx = LinkContext(
            page_path=PurePosixPath("base/feature/feature.md"),
            registry={TypeIdentity(BBox, "BBox"): PurePosixPath("system/geometric.md")},
        )
        assert format_type(field, ctx) == "[`bbox`](../../system/geometric.md)"

    def test_geometry_without_context_renders_plain_code(self) -> None:
        assert format_type(_make_field(Geometry)) == "`geometry`"


def _make_field(
    annotation: object,
    *,
    name: str = "x",
    is_required: bool = True,
    is_optional: bool = False,
) -> FieldSpec:
    """Build a FieldSpec from an annotation for test convenience."""
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
        """int32 links to the numeric types aggregate page when in registry."""
        ctx = LinkContext(
            page_path=PurePosixPath("places/place/place.md"),
            registry={TypeIdentity(int32, "int32"): PurePosixPath("system/numeric.md")},
        )
        result = format_type(_make_field(int32), ctx)
        assert "[`int32`]" in result
        assert "system/numeric.md" in result


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


def _link_ctx(*entries: tuple[object, str, str]) -> LinkContext:
    """Build a LinkContext registering each (newtype, name, page_path)."""
    return LinkContext(
        page_path=PurePosixPath("base/names/names.md"),
        registry={
            TypeIdentity(newtype, name): PurePosixPath(path)
            for newtype, name, path in entries
        },
    )


class TestFormatMapType:
    """Tests for MapOf rendering in field cells (format_type).

    Adjacent backtick runs break links: CommonMark reads `` as a
    multi-backtick code-span delimiter, so any side left bare must fold
    into the surrounding `map<...>` span. Every linked case asserts
    `"``" not in result` to guard that.
    """

    def test_map_without_context_renders_bare_names(self) -> None:
        """A map field with no link context renders bare key/value names."""
        assert format_type(_make_field(dict[str, int32])) == "`map<string, int32>`"

    def test_map_value_list_preserves_list_wrapper(self) -> None:
        """A list-valued map keeps its `list<...>` wrapper, not just the element."""
        assert (
            format_type(_make_field(dict[str, list[int]]))
            == "`map<string, list<int64>>`"
        )

    def test_map_value_nested_map_preserves_map_wrapper(self) -> None:
        """A map-valued map keeps its inner `map<...>`, not a bare `?`."""
        assert (
            format_type(_make_field(dict[str, dict[str, int]]))
            == "`map<string, map<string, int64>>`"
        )

    def test_map_value_any_renders_as_any_not_question_mark(self) -> None:
        """An `Any`-valued map names the value `Any`, never a bare `?`."""
        assert format_type(_make_field(dict[str, Any])) == "`map<string, Any>`"

    def test_union_valued_map_side_raises(self) -> None:
        """A union-valued map side fails loudly rather than rendering a guess."""
        with pytest.raises(NotImplementedError):
            _bare_map_side_name(_union_ref([_ModelA, _ModelB]))

    def test_non_semantic_newtype_map_side_uses_registry_name(self) -> None:
        """A pass-through NewType resolves to its registry name, not its raw name.

        A NewType whose name equals its base type (here `int`) is not
        semantic, so it must render as the registry markdown name (`int64`).
        """
        shape = NewTypeShape(
            name="int", ref=object(), inner=Primitive(base_type="int", source_type=int)
        )
        assert _bare_map_side_name(shape) == "int64"

    def test_map_key_newtype_links_in_field_cell(self) -> None:
        """A semantic NewType key links to its page in the field cell."""
        LangTag = NewType("LangTag", str)
        ctx = _link_ctx((LangTag, "LangTag", "system/language_tag.md"))
        result = format_type(_make_field(dict[LangTag, str]), ctx)
        assert "[`LangTag`]" in result
        assert "language_tag.md" in result
        assert "map<" in result
        assert "``" not in result

    def test_map_value_newtype_links_in_field_cell(self) -> None:
        """A semantic NewType value links to its page in the field cell."""
        Stripped = NewType("Stripped", str)
        ctx = _link_ctx((Stripped, "Stripped", "system/stripped_string.md"))
        result = format_type(_make_field(dict[str, Stripped]), ctx)
        assert "[`Stripped`]" in result
        assert "stripped_string.md" in result
        assert "``" not in result

    def test_map_value_model_links_in_field_cell(self) -> None:
        """A model-valued map links the value model to its page (bd-ru4n).

        The real pipeline resolves a `dict[K, Model]` value to a `ModelRef`
        (not a BaseModel-sourced `Primitive`), so the link path must handle
        `ModelRef` map sides, not only `Primitive` ones.
        """
        spec = extract_model(_OuterWithModelMap)
        field = next(f for f in spec.fields if f.name == "m")
        ctx = _link_ctx((_ModelB, "_ModelB", "theme/feature/types/model_b.md"))
        result = format_type(field, ctx)
        assert "[`_ModelB`]" in result
        assert "model_b.md" in result
        assert "map<" in result
        assert "``" not in result

    def test_map_value_model_list_renders_bare_with_wrapper(self) -> None:
        """A `list<Model>`-valued map keeps its `list<...>` wrapper, no link.

        The real pipeline resolves the value to `ArrayOf(element=ModelRef)`.
        Linking would collapse the wrapper to a bare model link, so the
        `depth == 0` guard keeps the model side bare and preserves
        `list<...>`. Registering `_ModelB` makes the absent link meaningful.
        """
        spec = extract_model(_OuterWithModelListMap)
        field = next(f for f in spec.fields if f.name == "m")
        ctx = _link_ctx((_ModelB, "_ModelB", "theme/feature/types/model_b.md"))
        result = format_type(field, ctx)
        assert "[`_ModelB`]" not in result
        assert "list<" in result
        assert "map<string, list<_ModelB>>" in result

    def test_map_key_and_value_newtypes_both_link(self) -> None:
        """When both sides are semantic NewTypes, both link in the field cell."""
        LangTag = NewType("LangTag", str)
        Stripped = NewType("Stripped", str)
        ctx = _link_ctx(
            (LangTag, "LangTag", "system/language_tag.md"),
            (Stripped, "Stripped", "system/stripped_string.md"),
        )
        result = format_type(_make_field(dict[LangTag, Stripped]), ctx)
        assert "[`LangTag`]" in result
        assert "language_tag.md" in result
        assert "[`Stripped`]" in result
        assert "stripped_string.md" in result
        assert "``" not in result

    def test_map_value_geometry_links_in_field_cell(self) -> None:
        """A Geometry-valued map links to the geometry page.

        Geometry is a class-based registered primitive, not Enum/BaseModel.
        The map-side link decision shares `_scalar_identity`'s coverage, so a
        Geometry value links rather than rendering bare.
        """
        ctx = _link_ctx((Geometry, "geometry", "system/geometric.md"))
        result = format_type(_make_field(dict[str, Geometry]), ctx)
        assert "[`geometry`]" in result
        assert "system/geometric.md" in result
        assert "``" not in result

    def test_map_value_pydantic_type_links_in_field_cell(self) -> None:
        """A pydantic-sourced map value links to its page.

        HttpUrl is pydantic-sourced, not Enum/BaseModel; the shared map-side
        decision links it where the narrow Enum/BaseModel-only check left it
        bare.
        """
        ctx = _link_ctx((HttpUrl, "HttpUrl", "pydantic/networks/http_url.md"))
        result = format_type(_make_field(dict[str, HttpUrl]), ctx)
        assert "[`HttpUrl`]" in result
        assert "pydantic/networks/http_url.md" in result
        assert "``" not in result


class TestFormatUnderlyingScalarType:
    """Tests for scalar terminals in format_underlying_type."""

    def test_geometry_underlying_type_links(self) -> None:
        """A NewType whose underlying type is Geometry links to its page."""
        shape, _, _ = analyze_type(NewType("GeomAlias", Geometry))
        ctx = LinkContext(
            page_path=PurePosixPath("system/types/geom_alias.md"),
            registry={
                TypeIdentity(Geometry, "geometry"): PurePosixPath("system/geometric.md")
            },
        )
        result = format_underlying_type(shape, ctx)
        assert "[`geometry`](../geometric.md)" in result

    def test_numeric_underlying_type_stays_bare(self) -> None:
        """A NewType over a numeric primitive renders bare, not over-linked.

        The numeric branch keys on the builtin (`int`), which has no registry
        entry, so the underlying type stays bare and keeps its markdown name.
        """
        shape, _, _ = analyze_type(int32)
        ctx = LinkContext(page_path=PurePosixPath("system/types/x.md"), registry={})
        result = format_underlying_type(shape, ctx)
        assert result == "`int32`"
        assert "[" not in result


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
