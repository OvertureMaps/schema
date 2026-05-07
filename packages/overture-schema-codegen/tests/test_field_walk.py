"""Tests for the `FieldShape` walker and structural helpers."""

import pytest
from overture.schema.codegen.extraction.field import (
    AnyScalar,
    ArrayOf,
    LiteralScalar,
    MapOf,
    ModelRef,
    NewTypeShape,
    Primitive,
    UnionRef,
)
from overture.schema.codegen.extraction.field_walk import (
    shape_children,
    terminal_model_ref,
    terminal_of,
    terminal_primitive,
    terminal_scalar,
    walk_shape,
)


class TestShapeChildren:
    """Direct child enumeration over `FieldShape`."""

    def test_scalar_has_no_children(self) -> None:
        assert list(shape_children(Primitive(base_type="str"))) == []

    def test_array_yields_element(self) -> None:
        inner = Primitive(base_type="int32")
        assert list(shape_children(ArrayOf(element=inner))) == [inner]

    def test_map_yields_key_then_value(self) -> None:
        k = Primitive(base_type="str")
        v = Primitive(base_type="int32")
        assert list(shape_children(MapOf(key=k, value=v))) == [k, v]

    def test_model_ref_has_no_children(self) -> None:
        sentinel = object()
        assert list(shape_children(ModelRef(model=sentinel))) == []  # type: ignore[arg-type]

    def test_union_ref_has_no_children(self) -> None:
        sentinel = object()
        assert list(shape_children(UnionRef(union=sentinel))) == []  # type: ignore[arg-type]

    def test_newtype_shape_yields_inner(self) -> None:
        inner = Primitive(base_type="int32")
        nt = NewTypeShape(name="N", ref=object(), inner=inner)
        assert list(shape_children(nt)) == [inner]


class TestWalkShape:
    """Pre-order traversal over `FieldShape` trees."""

    @staticmethod
    def _collect(root: object) -> list[object]:
        seen: list[object] = []
        walk_shape(root, seen.append)  # type: ignore[arg-type]
        return seen

    def test_scalar_visits_once(self) -> None:
        root = Primitive(base_type="str")
        assert self._collect(root) == [root]

    def test_nested_arrays(self) -> None:
        leaf = Primitive(base_type="int32")
        middle = ArrayOf(element=leaf)
        root = ArrayOf(element=middle)
        assert self._collect(root) == [root, middle, leaf]

    def test_map_visits_self_key_value(self) -> None:
        k = Primitive(base_type="str")
        v = Primitive(base_type="int32")
        root = MapOf(key=k, value=v)
        assert self._collect(root) == [root, k, v]

    def test_model_ref_is_boundary(self) -> None:
        sentinel = object()
        root = ModelRef(model=sentinel)  # type: ignore[arg-type]
        assert self._collect(root) == [root]

    def test_union_ref_is_boundary(self) -> None:
        sentinel = object()
        root = UnionRef(union=sentinel)  # type: ignore[arg-type]
        assert self._collect(root) == [root]

    def test_array_of_newtype_walks_through(self) -> None:
        leaf = Primitive(base_type="str")
        nt = NewTypeShape(name="N", ref=object(), inner=leaf)
        root = ArrayOf(element=nt)
        assert self._collect(root) == [root, nt, leaf]


_STR = Primitive(base_type="str")
_INT = Primitive(base_type="int32")
_LITERAL = LiteralScalar(values=("a",))
_ANY = AnyScalar()
_MODEL = ModelRef(model=object())  # type: ignore[arg-type]
_MAP = MapOf(key=_STR, value=_INT)
_NEWTYPE_STR = NewTypeShape(name="N", ref=object(), inner=_STR)
_ARRAY_NEWTYPE_STR = ArrayOf(element=_NEWTYPE_STR)


class TestTerminalFilters:
    """`terminal_of` and the three typed `terminal_*` narrowing helpers."""

    @pytest.mark.parametrize(
        ("shape", "expected"),
        [
            (_STR, _STR),
            (ArrayOf(element=ArrayOf(element=_INT)), _INT),
            (_NEWTYPE_STR, _STR),
            (_ARRAY_NEWTYPE_STR, _STR),
            (ArrayOf(element=_MODEL), _MODEL),
            (_MAP, _MAP),
        ],
    )
    def test_terminal_of_unwraps_to_innermost(
        self, shape: object, expected: object
    ) -> None:
        assert terminal_of(shape) is expected  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("shape", "expected"),
        [
            (_STR, _STR),
            (ArrayOf(element=_INT), _INT),
            (_NEWTYPE_STR, _STR),
            (_LITERAL, None),
            (_ANY, None),
            (_MODEL, None),
        ],
    )
    def test_terminal_primitive(self, shape: object, expected: object) -> None:
        assert terminal_primitive(shape) is expected  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("shape", "expected"),
        [
            (_STR, _STR),
            (_LITERAL, _LITERAL),
            (_ANY, _ANY),
            (ArrayOf(element=_LITERAL), _LITERAL),
            (_MODEL, None),
            (_MAP, None),
        ],
    )
    def test_terminal_scalar(self, shape: object, expected: object) -> None:
        assert terminal_scalar(shape) is expected  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("shape", "expected"),
        [
            (_MODEL, _MODEL),
            (ArrayOf(element=_MODEL), _MODEL),
            (NewTypeShape(name="N", ref=object(), inner=_MODEL), _MODEL),
            (_STR, None),
            (_LITERAL, None),
            (_ANY, None),
        ],
    )
    def test_terminal_model_ref(self, shape: object, expected: object) -> None:
        assert terminal_model_ref(shape) is expected  # type: ignore[arg-type]
