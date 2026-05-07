"""Tests for `analyze_type`: annotation -> `FieldShape` analysis."""

from enum import Enum
from typing import Annotated, Any, Literal, NewType, Optional

import pytest
from annotated_types import Ge, MaxLen, MinLen
from overture.schema.codegen.extraction.field import (
    AnyScalar,
    ArrayOf,
    FieldShape,
    LiteralScalar,
    MapOf,
    NewTypeShape,
    Primitive,
)
from overture.schema.codegen.extraction.field_walk import (
    all_constraints,
    list_depth,
)
from overture.schema.codegen.extraction.length_constraints import (
    ArrayMinLen,
    ScalarMinLen,
)
from overture.schema.codegen.extraction.type_analyzer import (
    UnsupportedUnionError,
    analyze_type,
    single_literal_value,
    unwrap_list,
)
from overture.schema.system.primitive import int32
from overture.schema.system.ref import Id
from overture.schema.system.string import (
    HexColor,
    NoWhitespaceConstraint,
    NoWhitespaceString,
    SnakeCaseString,
)
from pydantic import BaseModel, Field, Tag
from typing_extensions import Sentinel


def _shape(annotation: object) -> FieldShape:
    shape, _, _ = analyze_type(annotation)
    return shape


def _is_optional(annotation: object) -> bool:
    _, is_optional, _ = analyze_type(annotation)
    return is_optional


def _description(annotation: object) -> str | None:
    _, _, description = analyze_type(annotation)
    return description


class TestPrimitives:
    @pytest.mark.parametrize("annotation", [str, int, float, bool])
    def test_builtin_emits_primitive(self, annotation: type) -> None:
        shape = _shape(annotation)
        assert isinstance(shape, Primitive)
        assert shape.base_type == annotation.__name__
        assert shape.source_type is annotation

    def test_any_emits_any_scalar(self) -> None:
        shape = _shape(Any)
        assert isinstance(shape, AnyScalar)


class TestSentinel:
    """`Sentinel` arms in unions are filtered alongside `None`."""

    @pytest.fixture()
    def missing(self) -> object:
        return Sentinel("MISSING")

    def test_filtered_leaves_concrete_type(self, missing: object) -> None:
        shape = _shape(str | missing)  # type: ignore[arg-type]
        assert isinstance(shape, Primitive)
        assert shape.base_type == "str"
        assert _is_optional(str | missing) is False  # type: ignore[arg-type]

    def test_with_none_sets_optional(self, missing: object) -> None:
        assert _is_optional(str | missing | None) is True  # type: ignore[arg-type]


class TestOptional:
    def test_pipe_none(self) -> None:
        assert _is_optional(str | None) is True

    def test_typing_optional(self) -> None:
        assert _is_optional(Optional[str]) is True  # noqa: UP045

    def test_literal_arm_filtered_with_concrete(self) -> None:
        shape, optional, _ = analyze_type(str | Literal[""] | None)
        assert isinstance(shape, Primitive) and shape.base_type == "str"
        assert optional is True


class TestList:
    def test_simple_list(self) -> None:
        shape = _shape(list[str])
        assert isinstance(shape, ArrayOf)
        assert isinstance(shape.element, Primitive)
        assert shape.element.base_type == "str"

    def test_nested_list_records_depth(self) -> None:
        shape = _shape(list[list[str]])
        assert list_depth(shape) == 2

    def test_optional_list(self) -> None:
        shape, optional, _ = analyze_type(list[str] | None)
        assert isinstance(shape, ArrayOf)
        assert optional is True

    def test_list_optional_element(self) -> None:
        shape, optional, _ = analyze_type(list[str | None])
        assert isinstance(shape, ArrayOf)
        # `is_optional` reflects the field accepting None; element-level
        # `| None` propagates the same way.
        assert optional is True


class TestAnnotated:
    def test_ge_collected_on_terminal(self) -> None:
        shape = _shape(Annotated[int, Field(ge=0)])
        assert isinstance(shape, Primitive)
        assert len(shape.constraints) == 1
        cs = shape.constraints[0]
        assert isinstance(cs.constraint, Ge)
        assert cs.source_ref is None

    def test_non_field_metadata_collected(self) -> None:
        shape = _shape(Annotated[str, "just a description"])
        assert isinstance(shape, Primitive)
        assert shape.constraints[0].constraint == "just a description"

    def test_list_level_minlen_lands_on_arrayof(self) -> None:
        shape = _shape(Annotated[list[str], Field(min_length=1)])
        assert isinstance(shape, ArrayOf)
        assert len(shape.constraints) == 1
        assert isinstance(shape.element, Primitive)
        assert shape.element.constraints == ()

    def test_layered_constraints_anchor_separately(self) -> None:
        shape = _shape(Annotated[list[Annotated[str, MinLen(2)]], MinLen(3)])
        assert isinstance(shape, ArrayOf)
        outer = shape.constraints
        assert len(outer) == 1
        assert outer[0].constraint == ArrayMinLen(min_length=3)
        assert isinstance(shape.element, Primitive)
        inner = shape.element.constraints
        assert len(inner) == 1
        assert inner[0].constraint == ScalarMinLen(min_length=2)


class TestLiteral:
    def test_single_value(self) -> None:
        shape = _shape(Literal["active"])
        assert isinstance(shape, LiteralScalar)
        assert shape.values == ("active",)

    def test_multi_value(self) -> None:
        shape = _shape(Literal["a", "b"])
        assert isinstance(shape, LiteralScalar)
        assert shape.values == ("a", "b")

    def test_optional_literal(self) -> None:
        shape, optional, _ = analyze_type(Literal["x"] | None)
        assert isinstance(shape, LiteralScalar)
        assert shape.values == ("x",)
        assert optional is True


class TestEnumAndModel:
    def test_enum_emits_primitive_with_source(self) -> None:
        class Color(Enum):
            RED = "red"

        shape = _shape(Color)
        assert isinstance(shape, Primitive)
        assert shape.source_type is Color

    def test_model_without_resolver_falls_back_to_primitive(self) -> None:
        class Person(BaseModel):
            name: str

        shape = _shape(Person)
        assert isinstance(shape, Primitive)
        assert shape.source_type is Person
        assert shape.base_type == "Person"


class TestNewType:
    def test_simple_newtype(self) -> None:
        shape = _shape(int32)
        assert isinstance(shape, NewTypeShape)
        assert shape.name == "int32"
        assert isinstance(shape.inner, Primitive)
        assert shape.inner.base_type == "int32"

    def test_outermost_newtype_is_outer_wrapper(self) -> None:
        shape = _shape(Id)
        assert isinstance(shape, NewTypeShape)
        assert shape.name == "Id"

    def test_optional_newtype(self) -> None:
        assert _is_optional(int32 | None) is True


class TestNewTypeWrappingList:
    def test_newtype_around_list(self) -> None:
        TestSources = NewType("TestSources", Annotated[list[str], Field(min_length=1)])
        shape = _shape(TestSources)
        assert isinstance(shape, NewTypeShape) and shape.name == "TestSources"
        assert isinstance(shape.inner, ArrayOf)

    def test_list_around_scalar_newtype(self) -> None:
        ScalarNT = NewType("ScalarNT", str)
        shape = _shape(list[ScalarNT])
        assert isinstance(shape, ArrayOf)
        assert isinstance(shape.element, NewTypeShape)


class TestConstraintProvenance:
    """Constraints carry the NewType that contributed them."""

    @pytest.fixture()
    def id_shape(self) -> FieldShape:
        return _shape(Id)

    @pytest.fixture()
    def hex_shape(self) -> FieldShape:
        return _shape(HexColor)

    def test_nested_newtype_flattens_with_sources(self, id_shape: FieldShape) -> None:
        sources = {cs.source_name for cs in all_constraints(id_shape)}
        assert "Id" in sources
        assert "NoWhitespaceString" in sources

    def test_inner_newtype_constraints_preserved(self, id_shape: FieldShape) -> None:
        nws = [
            cs
            for cs in all_constraints(id_shape)
            if cs.source_ref is NoWhitespaceString
        ]
        assert NoWhitespaceConstraint in {type(cs.constraint) for cs in nws}

    def test_direct_annotation_has_none_source(self) -> None:
        shape = _shape(Annotated[str, "direct"])
        cs = all_constraints(shape)
        assert len(cs) == 1
        assert cs[0].source_ref is None

    def test_single_newtype_attributed_to_itself(self, hex_shape: FieldShape) -> None:
        cs = all_constraints(hex_shape)
        assert cs and all(c.source_ref is HexColor for c in cs)


class TestDescription:
    def test_newtype_field_description(self) -> None:
        desc = _description(HexColor)
        assert desc is not None and "color" in desc.lower()

    def test_plain_type_has_no_description(self) -> None:
        assert _description(int) is None

    def test_annotated_field_description(self) -> None:
        MyType = Annotated[str, Field(description="A test description")]
        assert _description(MyType) == "A test description"

    def test_outermost_description_wins(self) -> None:
        desc = _description(Id)
        assert desc is not None and "unique identifier" in desc.lower()

    def test_newtype_without_field_description(self) -> None:
        assert _description(SnakeCaseString) is None


class TestDict:
    def test_simple_dict(self) -> None:
        shape = _shape(dict[str, int])
        assert isinstance(shape, MapOf)
        assert isinstance(shape.key, Primitive) and shape.key.base_type == "str"
        assert isinstance(shape.value, Primitive) and shape.value.base_type == "int"

    def test_optional_dict(self) -> None:
        shape, optional, _ = analyze_type(dict[str, str] | None)
        assert isinstance(shape, MapOf)
        assert optional is True

    def test_newtype_around_dict(self) -> None:
        TestMapping = NewType("TestMapping", dict[str, str])
        shape = _shape(TestMapping)
        assert isinstance(shape, NewTypeShape) and shape.name == "TestMapping"
        assert isinstance(shape.inner, MapOf)

    def test_dict_with_any_value(self) -> None:
        shape = _shape(dict[str, Any])
        assert isinstance(shape, MapOf)
        assert isinstance(shape.value, AnyScalar)

    def test_bare_dict_raises(self) -> None:
        with pytest.raises(TypeError, match="Bare dict"):
            analyze_type(dict)

    def test_minlen_on_map_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="MinLen on a Map"):
            _shape(Annotated[dict[str, int], MinLen(1)])

    def test_maxlen_on_map_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="MaxLen on a Map"):
            _shape(Annotated[dict[str, int], MaxLen(10)])


class TestErrors:
    def test_unsupported_annotation(self) -> None:
        with pytest.raises(TypeError, match="Unsupported annotation type"):
            analyze_type("not a type")

    def test_multi_type_union_without_resolver(self) -> None:
        with pytest.raises(UnsupportedUnionError):
            analyze_type(str | int)

    def test_bare_list(self) -> None:
        with pytest.raises(TypeError, match="Bare list without type argument"):
            analyze_type(list)


class UnionModelA(BaseModel):
    x: int


class UnionModelB(BaseModel):
    y: str


class TestUnionResolver:
    """Multi-arm unions of models go through the resolver callback."""

    def test_resolver_receives_annotation_members_and_description(self) -> None:
        captured: list[tuple[object, tuple[type[BaseModel], ...], str | None]] = []

        def resolver(
            annotation: object,
            members: tuple[type[BaseModel], ...],
            description: str | None,
        ) -> Primitive:
            captured.append((annotation, members, description))
            return Primitive(base_type="__captured__")

        union_type = Annotated[UnionModelA | UnionModelB, Field(description="x")]
        shape, _, _ = analyze_type(union_type, union_resolver=resolver)

        assert isinstance(shape, Primitive)
        assert shape.base_type == "__captured__"
        _ann, members, description = captured[0]
        expected: set[type[BaseModel]] = {UnionModelA, UnionModelB}
        assert set(members) == expected
        assert description == "x"

    def test_no_resolver_raises_on_multi_arm(self) -> None:
        union_type = Annotated[UnionModelA | UnionModelB, Field(description="x")]
        with pytest.raises(UnsupportedUnionError):
            analyze_type(union_type)

    def test_annotated_wrapped_members_unwrapped(self) -> None:
        from overture.schema.codegen.extraction.type_analyzer import analyze_type as at

        captured_members: list[tuple[type[BaseModel], ...]] = []

        def resolver(
            _ann: object,
            members: tuple[type[BaseModel], ...],
            _description: str | None,
        ) -> Primitive:
            captured_members.append(members)
            return Primitive(base_type="x")

        union_type = Annotated[
            Annotated[UnionModelA, Tag("a")] | Annotated[UnionModelB, Tag("b")],
            Field(description="disc"),
        ]
        at(union_type, union_resolver=resolver)
        expected: set[type[BaseModel]] = {UnionModelA, UnionModelB}
        assert set(captured_members[0]) == expected

    def test_mixed_model_nonmodel_raises(self) -> None:
        with pytest.raises(UnsupportedUnionError):
            analyze_type(UnionModelA | str)


class TestSingleLiteralValue:
    def test_single_string(self) -> None:
        assert single_literal_value(Literal["x"]) == "x"

    def test_single_int(self) -> None:
        assert single_literal_value(Literal[42]) == 42

    def test_multi_value_returns_none(self) -> None:
        assert single_literal_value(Literal["a", "b"]) is None

    def test_non_literal_returns_none(self) -> None:
        assert single_literal_value(str) is None

    def test_unsupported_returns_none(self) -> None:
        assert single_literal_value("not a type") is None


class TestUnwrapList:
    def test_plain_list(self) -> None:
        assert unwrap_list(list[int]) is int

    def test_nested_list(self) -> None:
        assert unwrap_list(list[list[str]]) is str

    def test_non_list_passthrough(self) -> None:
        assert unwrap_list(int) is int

    def test_optional_list(self) -> None:
        assert unwrap_list(list[int] | None) is int

    def test_optional_list_preserves_annotated(self) -> None:
        from overture.schema.common.scoping.vehicle import VehicleSelector

        assert unwrap_list(list[VehicleSelector] | None) is VehicleSelector


class TestNestedArrayCharacterization:
    """Pin analyze_type behavior on consecutive-list and NewType-chain shapes.

    The schema has no genuine `list[list[X]]` field, so these are the only
    coverage of the path the recursive _unwrap rewrite must preserve.
    """

    def test_list_of_list_nests_two_arrayofs(self) -> None:
        shape = _shape(list[list[str]])
        assert isinstance(shape, ArrayOf)
        assert isinstance(shape.element, ArrayOf)
        assert isinstance(shape.element.element, Primitive)
        assert shape.element.element.base_type == "str"

    def test_list_of_list_constraints_anchor_to_their_layer(self) -> None:
        # Each MinLen lands on the ArrayOf layer it annotates, not flattened.
        # Outer Annotated[..., Field(min_length=3)] targets the outer list.
        # Inner Annotated[list[str], Field(min_length=2)] targets the inner list.
        shape = _shape(
            Annotated[
                list[Annotated[list[str], Field(min_length=2)]], Field(min_length=3)
            ]
        )
        assert isinstance(shape, ArrayOf)
        inner = shape.element
        assert isinstance(inner, ArrayOf)
        outer_min_lens = [
            cs.constraint.min_length
            for cs in shape.constraints
            if isinstance(cs.constraint, ArrayMinLen)
        ]
        inner_min_lens = [
            cs.constraint.min_length
            for cs in inner.constraints
            if isinstance(cs.constraint, ArrayMinLen)
        ]
        assert outer_min_lens == [3]
        assert inner_min_lens == [2]

    def test_nested_newtype_chain_flattens_to_one_wrapper(self) -> None:
        # Id = NewType("Id", Annotated[NoWhitespaceString, Field(min_length=1)])
        shape = _shape(Id)
        assert isinstance(shape, NewTypeShape)
        assert shape.name == "Id"
        # exactly one NewTypeShape -- the inner NoWhitespaceString does not nest
        assert not isinstance(shape.inner, NewTypeShape)
        assert isinstance(shape.inner, Primitive)
        assert shape.inner.base_type == "NoWhitespaceString"

    def test_nested_newtype_constraint_order_outer_first(self) -> None:
        shape = _shape(Id)
        names = [cs.source_name for cs in all_constraints(shape)]
        # Id's own constraint precedes NoWhitespaceString's
        assert names == ["Id", "NoWhitespaceString"]

    def test_newtype_nested_as_list_element_flattens_under_outer_newtype(self) -> None:
        # A NewType chain collapses to one NewTypeShape (the outermost) even
        # when an inner NewType is nested across a list boundary -- the inner
        # name survives only as the terminal `base_type`.
        InnerElem = NewType("InnerElem", str)
        OuterList = NewType("OuterList", list[InnerElem])
        shape = _shape(OuterList)
        assert isinstance(shape, NewTypeShape)
        assert shape.name == "OuterList"
        assert isinstance(shape.inner, ArrayOf)
        # the InnerElem NewType does NOT produce its own NewTypeShape
        assert isinstance(shape.inner.element, Primitive)
        assert shape.inner.element.base_type == "InnerElem"

    def test_sole_list_element_newtype_keeps_its_wrapper(self) -> None:
        # With no outer NewType, a list-element NewType IS the outermost --
        # it keeps its NewTypeShape (guards against over-erasing).
        ElemOnly = NewType("ElemOnly", str)
        shape = _shape(list[ElemOnly])
        assert isinstance(shape, ArrayOf)
        assert isinstance(shape.element, NewTypeShape)
        assert shape.element.name == "ElemOnly"

    def test_newtype_inside_dict_value_is_an_independent_spine(self) -> None:
        # `dict` key/value are independent spines: a NewType in the value
        # keeps its wrapper even under an outer NewType, because erasure
        # stops at MapOf.
        DictValue = NewType("DictValue", str)
        DictWrap = NewType("DictWrap", dict[str, DictValue])
        shape = _shape(DictWrap)
        assert isinstance(shape, NewTypeShape)
        assert shape.name == "DictWrap"
        assert isinstance(shape.inner, MapOf)
        assert isinstance(shape.inner.value, NewTypeShape)
        assert shape.inner.value.name == "DictValue"
