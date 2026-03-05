"""Tests for type analysis."""

from enum import Enum
from typing import Annotated, Any, Literal, NewType, Optional

import pytest
from annotated_types import Ge
from overture.schema.codegen.extraction.type_analyzer import (
    TypeInfo,
    TypeKind,
    UnsupportedUnionError,
    analyze_type,
    single_literal_value,
)
from overture.schema.system.primitive import float64, int32
from overture.schema.system.ref import Id
from overture.schema.system.string import (
    HexColor,
    NoWhitespaceConstraint,
    NoWhitespaceString,
    SnakeCaseString,
)
from pydantic import BaseModel, Field, Tag
from typing_extensions import Sentinel


@pytest.fixture()
def id_type_info() -> TypeInfo:
    return analyze_type(Id)


@pytest.fixture()
def hex_color_type_info() -> TypeInfo:
    return analyze_type(HexColor)


class TestAnalyzeTypePrimitives:
    """Tests for primitive type analysis."""

    @pytest.mark.parametrize("annotation", [str, int, float, bool])
    def test_builtin_returns_primitive_type_info(self, annotation: type) -> None:
        """Builtin type annotations return PRIMITIVE TypeInfo with matching base_type."""
        result = analyze_type(annotation)

        assert result.base_type == annotation.__name__
        assert result.kind == TypeKind.PRIMITIVE
        assert result.is_optional is False
        assert result.is_list is False


class TestAnalyzeTypeSentinel:
    """Tests for Sentinel type filtering in unions.

    Pydantic uses ``typing_extensions.Sentinel`` instances (like ``<MISSING>``)
    in union types for optional fields. The type analyzer filters these out
    alongside ``None`` when processing unions.
    """

    @pytest.fixture()
    def missing_sentinel(self) -> object:
        return Sentinel("MISSING")

    def test_sentinel_filtered_from_union(self, missing_sentinel: object) -> None:
        """Sentinel is filtered out, leaving the concrete type."""
        result = analyze_type(str | missing_sentinel)  # type: ignore[arg-type]

        assert result.base_type == "str"
        assert result.kind == TypeKind.PRIMITIVE
        assert result.is_optional is False

    def test_sentinel_with_none_sets_optional(self, missing_sentinel: object) -> None:
        """Sentinel + None both filtered; None triggers is_optional."""
        result = analyze_type(str | missing_sentinel | None)  # type: ignore[arg-type]

        assert result.base_type == "str"
        assert result.kind == TypeKind.PRIMITIVE
        assert result.is_optional is True


class TestAnalyzeTypeOptional:
    """Tests for Optional type analysis."""

    def test_pipe_none_sets_is_optional(self) -> None:
        """str | None returns TypeInfo with is_optional=True."""
        result = analyze_type(str | None)

        assert result.base_type == "str"
        assert result.kind == TypeKind.PRIMITIVE
        assert result.is_optional is True
        assert result.is_list is False

    def test_type_with_literal_and_none(self) -> None:
        """str | Literal[""] | None filters Literal and marks optional."""
        result = analyze_type(str | Literal[""] | None)

        assert result.base_type == "str"
        assert result.kind == TypeKind.PRIMITIVE
        assert result.is_optional is True

    def test_typing_optional_sets_is_optional(self) -> None:
        """Optional[str] from typing module returns TypeInfo with is_optional=True."""
        result = analyze_type(Optional[str])  # noqa: UP045

        assert result.base_type == "str"
        assert result.kind == TypeKind.PRIMITIVE
        assert result.is_optional is True
        assert result.is_list is False


class TestAnalyzeTypeUnionLiteralFiltering:
    """Tests for filtering Literal arms out of unions."""

    def test_type_with_literal_alternative(self) -> None:
        """str | Literal[""] filters out the Literal and analyzes the concrete type."""
        result = analyze_type(str | Literal[""])

        assert result.base_type == "str"
        assert result.kind == TypeKind.PRIMITIVE
        assert result.is_optional is False


class TestAnalyzeTypeList:
    """Tests for list type analysis."""

    def test_list_str_sets_is_list(self) -> None:
        """list[str] returns TypeInfo with is_list=True."""
        result = analyze_type(list[str])

        assert result.base_type == "str"
        assert result.kind == TypeKind.PRIMITIVE
        assert result.is_optional is False
        assert result.is_list is True

    def test_nested_list_sets_depth_2(self) -> None:
        """list[list[str]] records two levels of nesting."""
        result = analyze_type(list[list[str]])

        assert result.list_depth == 2
        assert result.base_type == "str"
        assert result.kind == TypeKind.PRIMITIVE


class TestAnalyzeTypeComposite:
    """Tests for composite/nested type analysis."""

    def test_list_optional_str(self) -> None:
        """list[str | None] sets both is_list and is_optional."""
        result = analyze_type(list[str | None])

        assert result.base_type == "str"
        assert result.is_list is True
        assert result.is_optional is True

    def test_optional_list_str(self) -> None:
        """list[str] | None sets both is_list and is_optional."""
        result = analyze_type(list[str] | None)

        assert result.base_type == "str"
        assert result.is_list is True
        assert result.is_optional is True

    def test_annotated_optional_str(self) -> None:
        """Annotated[str | None, ...] extracts constraints and sets is_optional."""
        result = analyze_type(Annotated[str | None, "description"])

        assert result.base_type == "str"
        assert result.is_optional is True
        assert len(result.constraints) == 1
        assert result.constraints[0].source_ref is None
        assert result.constraints[0].constraint == "description"

    def test_annotated_list_str(self) -> None:
        """Annotated[list[str], ...] extracts constraints and sets is_list."""
        result = analyze_type(Annotated[list[str], Field(min_length=1)])

        assert result.base_type == "str"
        assert result.is_list is True
        assert len(result.constraints) == 1
        assert result.constraints[0].source_ref is None


class TestAnalyzeTypeAnnotated:
    """Tests for Annotated type analysis."""

    def test_annotated_int_with_ge_extracts_constraint(self) -> None:
        """Annotated[int, Field(ge=0)] unpacks FieldInfo to extract Ge constraint."""
        result = analyze_type(Annotated[int, Field(ge=0)])

        assert result.base_type == "int"
        assert result.kind == TypeKind.PRIMITIVE
        assert len(result.constraints) == 1
        cs = result.constraints[0]
        assert cs.source_ref is None
        assert isinstance(cs.constraint, Ge)
        assert cs.constraint.ge == 0

    def test_annotated_without_constraints(self) -> None:
        """Annotated[str, 'description'] extracts non-Field metadata."""
        result = analyze_type(Annotated[str, "just a description"])

        assert result.base_type == "str"
        assert len(result.constraints) == 1
        assert result.constraints[0].source_ref is None
        assert result.constraints[0].constraint == "just a description"


class TestAnalyzeTypeLiteral:
    """Tests for Literal type analysis."""

    def test_literal_string_extracts_values(self) -> None:
        """Literal["active"] stores the value in literal_values tuple."""
        result = analyze_type(Literal["active"])

        assert result.kind == TypeKind.LITERAL
        assert result.literal_values == ("active",)

    def test_literal_int_extracts_values(self) -> None:
        """Literal[42] stores the value in literal_values tuple."""
        result = analyze_type(Literal[42])

        assert result.kind == TypeKind.LITERAL
        assert result.literal_values == (42,)

    def test_multi_value_literal_stores_all_args(self) -> None:
        """Literal["a", "b"] stores all args in literal_values tuple."""
        result = analyze_type(Literal["a", "b"])

        assert result.kind == TypeKind.LITERAL
        assert result.literal_values == ("a", "b")

    def test_optional_literal_extracts_values(self) -> None:
        """Optional[Literal["x"]] unwraps to Literal with is_optional set."""
        result = analyze_type(Literal["x"] | None)

        assert result.kind == TypeKind.LITERAL
        assert result.literal_values == ("x",)
        assert result.is_optional is True


class TestAnalyzeTypeEnum:
    """Tests for Enum type analysis."""

    def test_enum_subclass_returns_kind_enum(self) -> None:
        """Enum subclass returns TypeInfo with kind=ENUM."""

        class Color(Enum):
            RED = "red"
            GREEN = "green"

        result = analyze_type(Color)

        assert result.base_type == "Color"
        assert result.kind == TypeKind.ENUM


class TestAnalyzeTypeModel:
    """Tests for BaseModel type analysis."""

    def test_basemodel_subclass_returns_kind_model(self) -> None:
        """BaseModel subclass returns TypeInfo with kind=MODEL."""

        class Person(BaseModel):
            name: str

        result = analyze_type(Person)

        assert result.base_type == "Person"
        assert result.kind == TypeKind.MODEL


class TestAnalyzeTypeNewType:
    """Tests for NewType primitive analysis."""

    def test_int32_returns_newtype_name(self) -> None:
        """int32 NewType returns TypeInfo with base_type='int32'."""
        result = analyze_type(int32)

        assert result.base_type == "int32"
        assert result.kind == TypeKind.PRIMITIVE

    def test_float64_returns_newtype_name(self) -> None:
        """float64 NewType returns TypeInfo with base_type='float64'."""
        result = analyze_type(float64)

        assert result.base_type == "float64"
        assert result.kind == TypeKind.PRIMITIVE

    def test_optional_int32(self) -> None:
        """int32 | None sets is_optional and preserves base_type."""
        result = analyze_type(int32 | None)

        assert result.base_type == "int32"
        assert result.is_optional is True


class TestNewtypeName:
    """Tests for outermost NewType name tracking."""

    def test_single_layer_newtype(self) -> None:
        """Single NewType like int32 sets newtype_name to its name."""
        result = analyze_type(int32)

        assert result.newtype_name == "int32"
        assert result.base_type == "int32"

    def test_nested_newtype_preserves_outermost(self, id_type_info: TypeInfo) -> None:
        """Nested NewType chain uses outermost name for newtype_name."""
        assert id_type_info.newtype_name == "Id"
        assert id_type_info.base_type == "NoWhitespaceString"

    def test_plain_type_has_no_newtype_name(self) -> None:
        """Plain types without NewType wrapping have newtype_name=None."""
        result = analyze_type(str)

        assert result.newtype_name is None

    def test_newtype_ref_set_for_newtype(self, id_type_info: TypeInfo) -> None:
        """newtype_ref points to the outermost NewType callable."""
        assert id_type_info.newtype_ref is Id

    def test_newtype_ref_none_for_plain_type(self) -> None:
        """Plain types have newtype_ref=None."""
        result = analyze_type(str)

        assert result.newtype_ref is None


class TestNewtypeWrappingList:
    """Tests for NewType wrapping a list type."""

    def test_newtype_wrapping_list(self) -> None:
        """NewType wrapping a list sets is_list and preserves newtype_name."""
        TestSources = NewType("TestSources", Annotated[list[str], Field(min_length=1)])
        result = analyze_type(TestSources)

        assert result.is_list is True
        assert result.newtype_name == "TestSources"

    def test_scalar_newtype_is_not_list(self) -> None:
        """Scalar NewType like int32 has is_list=False."""
        result = analyze_type(int32)

        assert result.is_list is False

    def test_plain_list_has_no_newtype_name(self) -> None:
        """Plain list[str] without NewType has newtype_name=None."""
        result = analyze_type(list[str])

        assert result.newtype_name is None
        assert result.is_list is True

    def test_newtype_wrapping_list_of_models(self) -> None:
        """list[NewType wrapping list[Model]] records depth 2, outer depth 1."""

        class _Item(BaseModel):
            name: str

        Inner = NewType("Inner", Annotated[list[_Item], Field(min_length=1)])
        result = analyze_type(list[Inner])

        assert result.list_depth == 2
        assert result.newtype_outer_list_depth == 1
        assert result.base_type == "Inner"
        assert result.kind == TypeKind.MODEL
        assert result.source_type is _Item


class TestNewtypeOuterListDepth:
    """Tests for newtype_outer_list_depth tracking."""

    def test_list_of_scalar_newtype_has_outer_depth(self) -> None:
        """list[ScalarNewType] records the list layer as outside the NewType."""
        ScalarNT = NewType("ScalarNT", str)
        result = analyze_type(list[ScalarNT])

        assert result.newtype_outer_list_depth == 1
        assert result.list_depth == 1

    def test_newtype_wrapping_list_has_zero_outer_depth(self) -> None:
        """NewType wrapping list[X] records no list layers outside the NewType."""
        ListNT = NewType("ListNT", Annotated[list[str], Field(min_length=1)])
        result = analyze_type(ListNT)

        assert result.newtype_outer_list_depth == 0
        assert result.list_depth == 1

    @pytest.mark.parametrize(
        "annotation",
        [
            list[str],  # list without NewType
            int32,  # scalar NewType
            str,  # plain type
        ],
        ids=["plain_list", "scalar_newtype", "plain_type"],
    )
    def test_zero_outer_depth_without_newtype_boundary(
        self, annotation: object
    ) -> None:
        """Types without a NewType inside a list have newtype_outer_list_depth=0."""
        result = analyze_type(annotation)

        assert result.newtype_outer_list_depth == 0

    def test_nested_list_of_scalar_newtype_has_outer_depth_2(self) -> None:
        """list[list[ScalarNewType]] records two outer list layers."""
        ScalarNT = NewType("ScalarNT", str)
        result = analyze_type(list[list[ScalarNT]])

        assert result.newtype_outer_list_depth == 2
        assert result.list_depth == 2


class TestConstraintProvenance:
    """Tests for flattened constraints with provenance tracking."""

    def test_nested_newtype_flattens_constraints(self, id_type_info: TypeInfo) -> None:
        """Id -> NoWhitespaceString -> str flattens all constraints with sources."""
        source_names = {
            cs.source_name for cs in id_type_info.constraints if cs.source_name
        }
        assert "Id" in source_names
        assert "NoWhitespaceString" in source_names

    def test_nested_newtype_includes_inner_constraints(
        self, id_type_info: TypeInfo
    ) -> None:
        """Inner NewType constraints are collected with provenance."""
        nws_constraints = [
            cs for cs in id_type_info.constraints if cs.source_ref is NoWhitespaceString
        ]
        constraint_types = {type(cs.constraint) for cs in nws_constraints}
        assert NoWhitespaceConstraint in constraint_types

    def test_direct_annotation_has_none_source(self) -> None:
        """Constraints from direct Annotated (no NewType) have source_ref=None."""
        result = analyze_type(Annotated[str, "direct"])

        assert len(result.constraints) == 1
        assert result.constraints[0].source_ref is None
        assert result.constraints[0].constraint == "direct"

    def test_single_newtype_constraints_attributed(
        self, hex_color_type_info: TypeInfo
    ) -> None:
        """HexColor constraints are attributed to the HexColor callable."""
        assert all(cs.source_ref is HexColor for cs in hex_color_type_info.constraints)
        assert len(hex_color_type_info.constraints) > 0

    def test_source_ref_is_newtype_callable(
        self, hex_color_type_info: TypeInfo
    ) -> None:
        """source_ref is the actual NewType callable, not a string."""
        cs = hex_color_type_info.constraints[0]
        assert cs.source_ref is HexColor

    def test_constraint_preserves_original_object(
        self, hex_color_type_info: TypeInfo
    ) -> None:
        """ConstraintSource.constraint holds the original constraint object."""
        hcc = next(
            cs
            for cs in hex_color_type_info.constraints
            if type(cs.constraint).__name__ == "HexColorConstraint"
        )
        assert hcc.constraint.__class__.__name__ == "HexColorConstraint"


class TestTypeInfoDescription:
    """Tests for TypeInfo.description from Field(description=...) metadata."""

    def test_newtype_with_field_description(
        self, hex_color_type_info: TypeInfo
    ) -> None:
        """Should extract Field description from HexColor."""
        assert hex_color_type_info.description is not None
        assert "color" in hex_color_type_info.description.lower()

    def test_newtype_without_field_description(self) -> None:
        """Should have None description for types without Field(description=...)."""
        result = analyze_type(int)
        assert result.description is None

    def test_plain_annotated_with_field_description(self) -> None:
        """Should extract description from Annotated with Field(description=...)."""
        MyType = Annotated[str, Field(description="A test description")]
        result = analyze_type(MyType)
        assert result.description == "A test description"

    def test_outermost_description_wins(self, id_type_info: TypeInfo) -> None:
        """Outermost FieldInfo.description takes precedence in nested NewTypes."""
        assert id_type_info.description is not None
        assert "unique identifier" in id_type_info.description.lower()

    def test_newtype_without_field_has_none_description(self) -> None:
        """NewType with constraints but no Field(description=...) has None."""
        result = analyze_type(SnakeCaseString)
        assert result.description is None


class TestAnalyzeTypeAny:
    """Tests for typing.Any analysis."""

    def test_any_returns_primitive(self) -> None:
        """Any annotation returns TypeInfo with base_type='Any' and kind=PRIMITIVE."""
        result = analyze_type(Any)

        assert result.base_type == "Any"
        assert result.kind == TypeKind.PRIMITIVE

    def test_dict_with_any_value(self) -> None:
        """dict[str, Any] analyzes without error."""
        result = analyze_type(dict[str, Any])

        assert result.is_dict is True
        assert result.dict_value_type is not None
        assert result.dict_value_type.base_type == "Any"


class TestAnalyzeTypeDict:
    """Tests for dict type analysis."""

    @pytest.fixture()
    def dict_str_int(self) -> TypeInfo:
        return analyze_type(dict[str, int])

    def test_dict_str_int_sets_is_dict(self, dict_str_int: TypeInfo) -> None:
        """dict[str, int] returns TypeInfo with is_dict=True."""
        assert dict_str_int.is_dict is True
        assert dict_str_int.is_optional is False
        assert dict_str_int.is_list is False

    def test_dict_key_type_analyzed(self, dict_str_int: TypeInfo) -> None:
        """dict[str, int] has dict_key_type describing the key."""
        assert dict_str_int.dict_key_type is not None
        assert dict_str_int.dict_key_type.base_type == "str"
        assert dict_str_int.dict_key_type.kind == TypeKind.PRIMITIVE

    def test_dict_value_type_analyzed(self, dict_str_int: TypeInfo) -> None:
        """dict[str, int] has dict_value_type describing the value."""
        assert dict_str_int.dict_value_type is not None
        assert dict_str_int.dict_value_type.base_type == "int"
        assert dict_str_int.dict_value_type.kind == TypeKind.PRIMITIVE

    def test_optional_dict(self) -> None:
        """dict[str, str] | None sets is_dict and is_optional."""
        result = analyze_type(dict[str, str] | None)

        assert result.is_dict is True
        assert result.is_optional is True

    def test_newtype_wrapping_dict(self) -> None:
        """NewType wrapping dict preserves newtype_name and sets is_dict."""
        TestMapping = NewType("TestMapping", dict[str, str])
        result = analyze_type(TestMapping)

        assert result.is_dict is True
        assert result.newtype_name == "TestMapping"

    def test_bare_dict_raises_type_error(self) -> None:
        """Bare dict without type arguments raises TypeError."""
        with pytest.raises(TypeError, match="Bare dict"):
            analyze_type(dict)


class TestAnalyzeTypeErrors:
    """Tests for error handling."""

    def test_unsupported_annotation_raises_type_error(self) -> None:
        """Unsupported annotation type raises TypeError."""
        with pytest.raises(TypeError, match="Unsupported annotation type"):
            analyze_type("not a type")

    def test_multi_type_union_raises_clear_error(self) -> None:
        """Multi-type unions like str | int raise UnsupportedUnionError."""
        with pytest.raises(
            UnsupportedUnionError, match="Multi-type unions not supported"
        ):
            analyze_type(str | int)

    def test_multi_type_union_with_none_raises_clear_error(self) -> None:
        """Multi-type optional unions like str | int | None raise UnsupportedUnionError."""
        with pytest.raises(
            UnsupportedUnionError, match="Multi-type unions not supported"
        ):
            analyze_type(str | int | None)

    def test_bare_list_raises_type_error(self) -> None:
        """Bare list without type argument raises TypeError."""
        with pytest.raises(TypeError, match="Bare list without type argument"):
            analyze_type(list)


class UnionModelA(BaseModel):
    x: int


class UnionModelB(BaseModel):
    y: str


class TestAnalyzeTypeUnion:
    """Tests for discriminated union analysis."""

    def test_all_model_union_returns_union_kind(self) -> None:
        """Annotated[Union of BaseModel subclasses] returns TypeKind.UNION."""
        union_type = Annotated[UnionModelA | UnionModelB, Field(description="test")]
        result = analyze_type(union_type)

        assert result.kind == TypeKind.UNION
        assert result.union_members is not None
        assert len(result.union_members) == 2
        assert UnionModelA in result.union_members
        assert UnionModelB in result.union_members

    def test_annotated_wrapped_members_unwrapped(self) -> None:
        """Union members wrapped in Annotated[X, Tag(...)] are unwrapped."""
        union_type = Annotated[
            Annotated[UnionModelA, Tag("a")] | Annotated[UnionModelB, Tag("b")],
            Field(description="disc"),
        ]
        result = analyze_type(union_type)

        assert result.kind == TypeKind.UNION
        assert result.union_members is not None
        assert len(result.union_members) == 2
        assert UnionModelA in result.union_members
        assert UnionModelB in result.union_members

    def test_mixed_model_nonmodel_union_still_raises(self) -> None:
        """Union of model + non-model types still raises UnsupportedUnionError."""
        with pytest.raises(UnsupportedUnionError):
            analyze_type(UnionModelA | str)

    def test_non_model_multi_union_still_raises(self) -> None:
        """Multi-type union of non-models still raises UnsupportedUnionError."""
        with pytest.raises(UnsupportedUnionError):
            analyze_type(str | int)

    def test_union_base_type_is_first_member_name(self) -> None:
        """UNION TypeInfo base_type is the first member's class name."""
        result = analyze_type(
            Annotated[UnionModelA | UnionModelB, Field(description="test")]
        )
        assert result.base_type == "UnionModelA"

    def test_optional_union_sets_is_optional(self) -> None:
        """Union with None among model members sets is_optional."""
        result = analyze_type(
            Annotated[UnionModelA | UnionModelB, Field(description="test")] | None
        )
        assert result.kind == TypeKind.UNION
        assert result.is_optional is True


class TestSingleLiteralValue:
    """Tests for single_literal_value convenience accessor."""

    def test_single_value_literal(self) -> None:
        """Literal["x"] returns the literal value."""
        assert single_literal_value(Literal["x"]) == "x"

    def test_single_int_literal(self) -> None:
        """Literal[42] returns the integer value."""
        assert single_literal_value(Literal[42]) == 42

    def test_multi_value_literal_returns_none(self) -> None:
        """Multi-value Literal returns None (no single default)."""
        assert single_literal_value(Literal["a", "b"]) is None

    def test_non_literal_returns_none(self) -> None:
        """Non-Literal types return None."""
        assert single_literal_value(str) is None

    def test_unsupported_type_returns_none(self) -> None:
        """Types that raise during analysis return None."""
        assert single_literal_value("not a type") is None
