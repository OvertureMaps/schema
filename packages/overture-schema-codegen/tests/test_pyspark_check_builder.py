"""Tests for check_builder -- scalar fields, struct recursion, and model constraints."""

from dataclasses import replace
from enum import Enum
from typing import Annotated, Literal, NewType, Union

import pytest
from annotated_types import Ge, Le, MinLen
from codegen_test_support import (
    FeatureWithDict,
    LiteralSubtypeModel,
    RadioModel,
    RequireAnyModel,
    TripleNestedArrayModel,
    discover_feature,
    spec_for_model,
    union_spec_for,
)
from overture.schema.codegen.extraction.field import (
    ConstraintSource,
    Primitive,
    UnionRef,
)
from overture.schema.codegen.extraction.specs import (
    FieldSpec,
    ModelSpec,
    RecordSpec,
)
from overture.schema.codegen.extraction.union_extraction import extract_union
from overture.schema.codegen.pyspark._render_common import column_level_suffix
from overture.schema.codegen.pyspark.check_builder import (
    build_checks,
)
from overture.schema.codegen.pyspark.check_ir import (
    Check,
    ColumnGuard,
    ElementGuard,
    ModelCheck,
)
from overture.schema.codegen.pyspark.constraint_dispatch import (
    ExpressionDescriptor,
    ForbidIf,
    RequireIf,
    model_constraint_function,
)
from overture.schema.common.scoping.lr import LinearlyReferencedRange
from overture.schema.system.field_constraint.collection import UniqueItemsConstraint
from overture.schema.system.field_path import (
    ArrayPath,
    ArraySegment,
    FieldPath,
    MapPath,
    MapProjection,
    ScalarPath,
    parse,
)
from overture.schema.system.model_constraint import (
    FieldEqCondition,
    Not,
    forbid_if,
    require_any_of,
)
from overture.schema.system.string import CountryCodeAlpha2
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
from pydantic.networks import HttpUrl

_path = parse


def _column_guard(check: Check) -> ColumnGuard | None:
    """Return the first ColumnGuard, or None."""
    for g in check.guards:
        if isinstance(g, ColumnGuard):
            return g
    return None


def _element_guard(check: Check) -> ElementGuard | None:
    """Return the first ElementGuard, or None."""
    for g in check.guards:
        if isinstance(g, ElementGuard):
            return g
    return None


def _checks_for(
    model_cls: type[BaseModel],
) -> tuple[list[Check], list[ModelCheck]]:
    return build_checks(spec_for_model(model_cls))


def _condition_of(check: ModelCheck) -> object:
    """Return the condition of a RequireIf or ForbidIf descriptor."""
    desc = check.descriptor
    assert isinstance(desc, (RequireIf, ForbidIf)), (
        f"Expected RequireIf or ForbidIf, got {type(desc).__name__}"
    )
    return desc.condition


def _filter_nodes(
    nodes: list[ModelCheck],
    function: str | tuple[str, ...],
    field_names: tuple[str, ...] | None = None,
) -> list[ModelCheck]:
    functions = (function,) if isinstance(function, str) else function
    return [
        n
        for n in nodes
        if model_constraint_function(n.descriptor) in functions
        and (field_names is None or n.descriptor.field_names == field_names)
    ]


def _union_checks(
    name: str, union_type: object
) -> tuple[list[Check], list[ModelCheck]]:
    return build_checks(union_spec_for(name, union_type))


def _union_model_nodes(name: str, union_type: object) -> list[ModelCheck]:
    _, model_nodes = _union_checks(name, union_type)
    return model_nodes


class TestScalarChecks:
    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(LiteralSubtypeModel)
        return nodes

    def test_literal_produces_enum_check(self, nodes: list[Check]) -> None:
        enum_nodes = [n for n in nodes if n.target == _path("subtype")]
        assert len(enum_nodes) == 1
        node = enum_nodes[0]
        descriptors = node.descriptors
        funcs = [d.function for d in descriptors]
        assert "check_required" in funcs
        assert "check_enum" in funcs

    def test_optional_field_no_required_check(self, nodes: list[Check]) -> None:
        name_nodes = [n for n in nodes if n.target == _path("name")]
        for node in name_nodes:
            funcs = [d.function for d in node.descriptors]
            assert "check_required" not in funcs

    def test_required_comes_first_in_coalesce(self, nodes: list[Check]) -> None:
        enum_nodes = [n for n in nodes if n.target == _path("subtype")]
        node = enum_nodes[0]
        funcs = [d.function for d in node.descriptors]
        req_idx = funcs.index("check_required")
        enum_idx = funcs.index("check_enum")
        assert req_idx < enum_idx

    def test_enum_args_contain_literal_values(self, nodes: list[Check]) -> None:
        enum_nodes = [n for n in nodes if n.target == _path("subtype")]
        node = enum_nodes[0]
        enum_desc = next(d for d in node.descriptors if d.function == "check_enum")
        assert enum_desc.args == (("a", "b", "c"),)

    def test_optional_str_field_no_checks(self, nodes: list[Check]) -> None:
        # name: str | None = None has no constraints, so no check node
        name_nodes = [n for n in nodes if n.target == _path("name")]
        assert len(name_nodes) == 0


class _RequiredNewtypeModel(BaseModel):
    country: CountryCodeAlpha2


class TestRequiredNewtypeChecks:
    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(_RequiredNewtypeModel)
        return nodes

    def test_required_newtype_includes_check_required(self, nodes: list[Check]) -> None:
        country_nodes = [n for n in nodes if n.target == _path("country")]
        assert len(country_nodes) == 1
        funcs = [d.function for d in country_nodes[0].descriptors]
        assert "check_required" in funcs

    def test_required_newtype_includes_newtype_function(
        self, nodes: list[Check]
    ) -> None:
        country_nodes = [n for n in nodes if n.target == _path("country")]
        funcs = [d.function for d in country_nodes[0].descriptors]
        assert "check_pattern" in funcs

    def test_required_precedes_newtype_function(self, nodes: list[Check]) -> None:
        country_nodes = [n for n in nodes if n.target == _path("country")]
        funcs = [d.function for d in country_nodes[0].descriptors]
        assert funcs.index("check_required") < funcs.index("check_pattern")


class _Color(str, Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class EnumFieldModel(BaseModel):
    color: _Color


class TestEnumKindChecks:
    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(EnumFieldModel)
        return nodes

    def test_enum_field_produces_check_enum(self, nodes: list[Check]) -> None:
        enum_descs = [
            d for n in nodes for d in n.descriptors if d.function == "check_enum"
        ]
        assert len(enum_descs) == 1

    def test_enum_field_uses_member_values(self, nodes: list[Check]) -> None:
        enum_descs = [
            d for n in nodes for d in n.descriptors if d.function == "check_enum"
        ]
        assert enum_descs[0].args == (("red", "green", "blue"),)


class InnerModel(BaseModel):
    value: str
    count: int = Field(ge=0)


class OuterModel(BaseModel):
    inner: InnerModel | None = None


class _ArrayElement(BaseModel):
    tag: str


class _NullableWithArray(BaseModel):
    items: list[_ArrayElement] | None = None


class _NullableArrayGrandparent(BaseModel):
    parent: _NullableWithArray | None = None


class TestNullableParentGating:
    """Required fields within optional struct parents get gated check_required."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(OuterModel)
        return nodes

    def test_required_field_has_gated_check_required(self, nodes: list[Check]) -> None:
        value_nodes = [n for n in nodes if n.target == _path("inner.value")]
        req_descs = [
            d
            for n in value_nodes
            for d in n.descriptors
            if d.function == "check_required"
        ]
        assert len(req_descs) == 1
        assert req_descs[0].gate == _path("inner")

    def test_non_check_required_descriptors_have_no_gate(
        self, nodes: list[Check]
    ) -> None:
        count_nodes = [n for n in nodes if n.target == _path("inner.count")]
        for node in count_nodes:
            for desc in node.descriptors:
                if desc.function != "check_required":
                    assert desc.gate is None

    def test_other_checks_still_present(self, nodes: list[Check]) -> None:
        count_nodes = [n for n in nodes if n.target == _path("inner.count")]
        assert len(count_nodes) >= 1
        funcs = [d.function for d in count_nodes[0].descriptors]
        assert "check_bounds" in funcs


class TestArrayBoundaryResetsNullable:
    """nullable_gate resets at array boundaries."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(_NullableArrayGrandparent)
        return nodes

    def test_required_field_in_array_element_has_check_required(
        self, nodes: list[Check]
    ) -> None:
        tag_nodes = [n for n in nodes if n.target == _path("parent.items[].tag")]
        assert len(tag_nodes) >= 1
        funcs = [d.function for n in tag_nodes for d in n.descriptors]
        assert "check_required" in funcs

    def test_array_element_required_has_no_gate(self, nodes: list[Check]) -> None:
        tag_nodes = [n for n in nodes if n.target == _path("parent.items[].tag")]
        req_descs = [
            d
            for n in tag_nodes
            for d in n.descriptors
            if d.function == "check_required"
        ]
        assert len(req_descs) == 1
        assert req_descs[0].gate is None


class _OptionalNested(BaseModel):
    mode: str


class _ElementWithOptional(BaseModel):
    nested: _OptionalNested | None = None


class _ArrayWithOptionalNested(BaseModel):
    items: list[_ElementWithOptional]


class TestArrayElementConditionalGate:
    """Optional structs within array elements get gated check_required."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(_ArrayWithOptionalNested)
        return nodes

    def test_required_in_optional_element_struct_has_gate(
        self, nodes: list[Check]
    ) -> None:
        mode_nodes = [n for n in nodes if n.target == _path("items[].nested.mode")]
        req_descs = [
            d
            for n in mode_nodes
            for d in n.descriptors
            if d.function == "check_required"
        ]
        assert len(req_descs) == 1
        assert req_descs[0].gate == _path("items[].nested")


class TestStructRecursion:
    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(OuterModel)
        return nodes

    def test_recurses_into_model_fields(self, nodes: list[Check]) -> None:
        paths = {n.target for n in nodes}
        assert _path("inner.count") in paths

    def test_nested_field_uses_dot_path(self, nodes: list[Check]) -> None:
        count_nodes = [n for n in nodes if n.target == _path("inner.count")]
        assert len(count_nodes) == 1


class ItemModel(BaseModel):
    value: str


class ArrayModel(BaseModel):
    items: Annotated[list[ItemModel], MinLen(1)]


class TestArrayChecks:
    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(ArrayModel)
        return nodes

    def test_array_min_length_is_scalar_shape(self, nodes: list[Check]) -> None:
        length_nodes = [
            n
            for n in nodes
            if any(d.function == "check_array_min_length" for d in n.descriptors)
        ]
        assert len(length_nodes) == 1
        assert isinstance(length_nodes[0].target, ScalarPath)

    def test_array_element_field_uses_bracket_notation(
        self, nodes: list[Check]
    ) -> None:
        paths = {n.target for n in nodes}
        assert any(isinstance(p, ArrayPath) for p in paths)

    def test_array_element_subfield_path(self, nodes: list[Check]) -> None:
        # ItemModel.value is required, so a check node for items[].value must exist
        paths = {n.target for n in nodes}
        assert _path("items[].value") in paths

    def test_array_level_check_has_no_inner_levels(self, nodes: list[Check]) -> None:
        length_nodes = [
            n
            for n in nodes
            if any(d.function == "check_array_min_length" for d in n.descriptors)
        ]
        assert length_nodes[0].target == _path("items")

    def test_required_array_field_has_required_check(self, nodes: list[Check]) -> None:
        # check_required on an array field is a column-level null check; its
        # target is the scalar `items` column, not an element path.
        required_nodes = [
            n
            for n in nodes
            if n.target == _path("items")
            and any(d.function == "check_required" for d in n.descriptors)
        ]
        assert len(required_nodes) == 1

    def test_array_element_subfield_has_single_check(self, nodes: list[Check]) -> None:
        value_nodes = [n for n in nodes if n.target == _path("items[].value")]
        assert len(value_nodes) == 1


class _StringListModel(BaseModel):
    tags: Annotated[list[str], MinLen(1)]


class _NestedListModel(BaseModel):
    """list[list[ItemModel]] — both layers contribute MinLen + UniqueItems."""

    items: Annotated[
        list[Annotated[list[InnerModel], MinLen(1), UniqueItemsConstraint()]],
        MinLen(1),
        UniqueItemsConstraint(),
    ]


class _StringInListModel(BaseModel):
    """list[Annotated[str, MinLen]] with outer list MinLen — inner is string MinLen."""

    tags: Annotated[list[Annotated[str, MinLen(1)]], MinLen(1)]


_HierarchyItemList = NewType(
    "_HierarchyItemList",
    Annotated[list[InnerModel], MinLen(1), UniqueItemsConstraint()],
)


class _HierarchyLikeModel(BaseModel):
    """Mirror of Division.hierarchies: inner list lives inside a NewType."""

    hierarchies: Annotated[
        list[_HierarchyItemList],
        MinLen(1),
        UniqueItemsConstraint(),
    ]


class TestListFieldNameSplitting:
    """Column-level and element-level checks for list fields get distinct field names."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(_StringListModel)
        return nodes

    def test_unique_labels_for_different_shapes(self, nodes: list[Check]) -> None:
        labels = [(n.target, column_level_suffix(n)) for n in nodes]
        assert len(labels) == len(set(labels)), f"Duplicate labels: {labels}"

    def test_min_length_check_carries_min_length_suffix(
        self, nodes: list[Check]
    ) -> None:
        min_len_nodes = [
            n
            for n in nodes
            if any(d.function == "check_array_min_length" for d in n.descriptors)
        ]
        assert len(min_len_nodes) == 1
        assert min_len_nodes[0].target == _path("tags")
        assert column_level_suffix(min_len_nodes[0]) == "_min_length"


def _node_for(nodes: list[Check], field: str, function: str) -> Check:
    field_path = _path(field)
    matching = [
        n
        for n in nodes
        if n.target == field_path and any(d.function == function for d in n.descriptors)
    ]
    assert len(matching) == 1, (
        f"expected exactly one node for field={field!r} function={function!r}, "
        f"got {len(matching)}"
    )
    return matching[0]


@pytest.mark.parametrize(
    ("model_cls", "field"),
    [
        (_NestedListModel, "items"),
        (_HierarchyLikeModel, "hierarchies"),
    ],
    ids=["nested_list", "hierarchy_newtype"],
)
class TestPerLevelListConstraints:
    """Each layer of `list[list[X]]` emits its own column-level check.

    Covers both raw nested lists (`_NestedListModel`) and the
    NewType-wrapped variant (`_HierarchyLikeModel`, mirroring
    `Division.hierarchies`).
    """

    def test_no_duplicate_labels(self, model_cls: type[BaseModel], field: str) -> None:
        nodes, _ = _checks_for(model_cls)
        labels = [(n.target, column_level_suffix(n)) for n in nodes]
        assert len(labels) == len(set(labels)), f"Duplicate labels: {labels}"

    def test_outer_min_length_check(
        self, model_cls: type[BaseModel], field: str
    ) -> None:
        nodes, _ = _checks_for(model_cls)
        outer = _node_for(nodes, field, "check_array_min_length")
        assert outer.target == _path(field)

    def test_inner_min_length_check(
        self, model_cls: type[BaseModel], field: str
    ) -> None:
        nodes, _ = _checks_for(model_cls)
        inner = _node_for(nodes, f"{field}[]", "check_array_min_length")
        assert inner.target == _path(f"{field}[]")

    def test_outer_unique_check(self, model_cls: type[BaseModel], field: str) -> None:
        nodes, _ = _checks_for(model_cls)
        outer = _node_for(nodes, field, "check_struct_unique")
        assert outer.target == _path(field)

    def test_inner_unique_check(self, model_cls: type[BaseModel], field: str) -> None:
        nodes, _ = _checks_for(model_cls)
        inner = _node_for(nodes, f"{field}[]", "check_struct_unique")
        assert inner.target == _path(f"{field}[]")


class TestPerLevelScalarMinLen:
    """list[Annotated[str, MinLen]] with outer list MinLen splits cleanly."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(_StringInListModel)
        return nodes

    def test_outer_array_min_length(self, nodes: list[Check]) -> None:
        outer = _node_for(nodes, "tags", "check_array_min_length")
        assert outer.target == _path("tags")

    def test_inner_string_min_length(self, nodes: list[Check]) -> None:
        inner = _node_for(nodes, "tags[]", "check_string_min_length")
        assert inner.target == _path("tags[]")


class TestDescriptorDedupKey:
    """Descriptor equality drives layer-level dedup via `dict.fromkeys`."""

    def test_identical_descriptors_collapse(self) -> None:
        desc = ExpressionDescriptor(function="check_array_min_length", args=(1,))
        assert list(dict.fromkeys([desc, desc])) == [desc]

    def test_distinct_descriptors_preserve_order(self) -> None:
        first = ExpressionDescriptor(function="check_array_min_length", args=(1,))
        second = ExpressionDescriptor(function="check_struct_unique")
        assert list(dict.fromkeys([first, second, first])) == [first, second]

    def test_different_args_are_distinct(self) -> None:
        one = ExpressionDescriptor(function="check_array_min_length", args=(1,))
        two = ExpressionDescriptor(function="check_array_min_length", args=(2,))
        assert list(dict.fromkeys([one, two])) == [one, two]

    def test_different_gates_are_distinct(self) -> None:
        ungated = ExpressionDescriptor(function="check_required")
        gated = ExpressionDescriptor(function="check_required", gate=_path("parent"))
        assert list(dict.fromkeys([ungated, gated])) == [ungated, gated]


class TestListOfNewtypeConstraintDispatch:
    """Element-level MinLen from NewType inside a list dispatches as string check."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        MyId = NewType("MyId", Annotated[str, MinLen(1)])

        class ListOfIdModel(BaseModel):
            ids: list[MyId]

        nodes, _ = _checks_for(ListOfIdModel)
        return nodes

    def test_element_min_length_dispatches_as_string_check(
        self, nodes: list[Check]
    ) -> None:
        """MinLen from the element NewType should produce check_string_min_length, not check_array_min_length."""
        all_funcs = [d.function for n in nodes for d in n.descriptors]
        assert "check_string_min_length" in all_funcs
        # check_array_min_length should NOT appear — there's no list-level MinLen
        assert "check_array_min_length" not in all_funcs


class _InternalListNewtypeModel(BaseModel):
    """Model with a NewType that wraps list[float] (list is inside the NewType)."""

    between: list[CountryCodeAlpha2] | None = None  # outer list wrapping


class TestNewtypeWithInternalList:
    """When a NewType IS a list, the check function handles the whole array."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        class InternalListModel(BaseModel):
            between: LinearlyReferencedRange | None = None

        nodes, _ = _checks_for(InternalListModel)
        return nodes

    def test_internal_list_newtype_has_single_check(self, nodes: list[Check]) -> None:
        between_nodes = [n for n in nodes if n.target == _path("between")]
        assert len(between_nodes) == 1

    def test_internal_list_newtype_has_three_descriptors(
        self, nodes: list[Check]
    ) -> None:
        between_nodes = [n for n in nodes if n.target == _path("between")]
        fns = [d.function for d in between_nodes[0].descriptors]
        assert "check_linear_range_length" in fns
        assert "check_linear_range_bounds" in fns
        assert "check_linear_range_order" in fns


class TestBaseTypeDispatchInCheckBuilder:
    """Base type dispatch generates element-level checks for HttpUrl/EmailStr."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        class HttpUrlListModel(BaseModel):
            websites: list[HttpUrl] | None = None

        nodes, _ = _checks_for(HttpUrlListModel)
        return nodes

    def test_http_url_produces_check_url_format(self, nodes: list[Check]) -> None:
        url_nodes = [
            n
            for n in nodes
            if any(d.function == "check_url_format" for d in n.descriptors)
        ]
        assert len(url_nodes) == 1

    def test_http_url_element_check_is_array_shape(self, nodes: list[Check]) -> None:
        url_nodes = [
            n
            for n in nodes
            if any(d.function == "check_url_format" for d in n.descriptors)
        ]
        assert isinstance(url_nodes[0].target, ArrayPath)


class _DeepInner(BaseModel):
    field: str


class _ArrayElementWithNestedStruct(BaseModel):
    nested: _DeepInner


class _DeepNestedArrayModel(BaseModel):
    items: list[_ArrayElementWithNestedStruct]


class TestArrayElementNestedStructChecks:
    """Struct fields inside array elements produce array-shaped checks."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(_DeepNestedArrayModel)
        return nodes

    def test_nested_struct_field_path(self, nodes: list[Check]) -> None:
        paths = {n.target for n in nodes}
        assert _path("items[].nested.field") in paths


class _ArrayElementWithList(BaseModel):
    tags: list[CountryCodeAlpha2]


class _ListInArrayModel(BaseModel):
    items: list[_ArrayElementWithList]


class TestArrayElementListChecks:
    """List fields inside array elements need nested iteration."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(_ListInArrayModel)
        return nodes

    def test_list_subfield_element_checks_have_inner_levels(
        self, nodes: list[Check]
    ) -> None:
        # Element-level check on a list field inside an outer array: target
        # encodes both iterations explicitly as `items[].tags[]`.
        element_nodes = [n for n in nodes if n.target == _path("items[].tags[]")]
        assert len(element_nodes) >= 1

    def test_list_subfield_column_path_is_enclosing_array(
        self, nodes: list[Check]
    ) -> None:
        tag_nodes = [n for n in nodes if str(n.target).startswith("items[].tags")]
        for node in tag_nodes:
            assert isinstance(node.target, ArrayPath)
            # the outermost iterated column is `items`, not the inner `tags` list
            assert node.target.array_chunks[0] == ((), "items", 1)


class _ArrayElementWithNewtype(BaseModel):
    country: CountryCodeAlpha2


class _NewtypeInArrayModel(BaseModel):
    items: list[_ArrayElementWithNewtype]


class TestArrayElementNewtypeChecks:
    """Newtype fields inside array elements: shape=ARRAY, no inner_levels."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(_NewtypeInArrayModel)
        return nodes

    def test_newtype_subfield_has_single_check(self, nodes: list[Check]) -> None:
        country_nodes = [n for n in nodes if n.target == _path("items[].country")]
        assert len(country_nodes) == 1


class TestModelLevelConstraints:
    @pytest.fixture
    def radio_model_nodes(self) -> list[ModelCheck]:
        _, model_nodes = _checks_for(RadioModel)
        return model_nodes

    @pytest.fixture
    def require_any_model_nodes(self) -> list[ModelCheck]:
        _, model_nodes = _checks_for(RequireAnyModel)
        return model_nodes

    def test_radio_group_produces_model_check(
        self, radio_model_nodes: list[ModelCheck]
    ) -> None:
        assert len(_filter_nodes(radio_model_nodes, "check_radio_group")) == 1

    def test_radio_group_field_names(self, radio_model_nodes: list[ModelCheck]) -> None:
        radio = _filter_nodes(radio_model_nodes, "check_radio_group")[0]
        assert set(radio.descriptor.field_names) == {"a", "b"}

    def test_require_any_of_produces_model_check(
        self, require_any_model_nodes: list[ModelCheck]
    ) -> None:
        assert len(_filter_nodes(require_any_model_nodes, "check_require_any_of")) == 1

    def test_require_any_of_field_names(
        self, require_any_model_nodes: list[ModelCheck]
    ) -> None:
        node = _filter_nodes(require_any_model_nodes, "check_require_any_of")[0]
        assert set(node.descriptor.field_names) == {"x", "y"}

    def test_no_constraints_returns_empty_model_nodes(self) -> None:
        _, model_nodes = _checks_for(LiteralSubtypeModel)
        assert model_nodes == []


class _SpeedStruct(BaseModel):
    value: int
    unit: str


@require_any_of("fast", "slow")
class _RequireAnyOfStructFields(BaseModel):
    fast: _SpeedStruct | None = None
    slow: _SpeedStruct | None = None


class TestRequireAnyOfStructUnwrapping:
    """require_any_of on struct fields must reference the leaf scalar, not the struct."""

    @pytest.fixture
    def node(self) -> ModelCheck:
        _, model_nodes = _checks_for(_RequireAnyOfStructFields)
        nodes = _filter_nodes(model_nodes, "check_require_any_of")
        assert len(nodes) == 1
        return nodes[0]

    def test_field_names_use_leaf_path(self, node: ModelCheck) -> None:
        assert set(node.descriptor.field_names) == {"fast.value", "slow.value"}


class _SyntheticUnionFixtures:
    """Discriminated-union models exercising union check generation."""

    class Base(BaseModel):
        kind: str

    class TypeA(Base):
        kind: Literal["a"] = "a"
        a_field: Literal["x", "y"] | None = None

    class TypeB(Base):
        kind: Literal["b"] = "b"
        b_field: Literal["p", "q"] | None = None

    SyntheticUnion = Annotated[
        Union[TypeA, TypeB],  # noqa: UP007
        FieldInfo(discriminator="kind"),
    ]

    @require_any_of("p", "q")
    class ConstrainedMember(Base):
        kind: Literal["c"] = "c"
        p: str | None = None
        q: str | None = None

    ConstrainedUnion = Annotated[
        Union[TypeA, ConstrainedMember],  # noqa: UP007
        FieldInfo(discriminator="kind"),
    ]

    class MemberX(Base):
        kind: Literal["x"] = "x"
        shared_name: Literal["x1", "x2"]

    class MemberY(Base):
        kind: Literal["y"] = "y"
        shared_name: Literal["y1", "y2"]

    class MemberZ(Base):
        kind: Literal["z"] = "z"

    ThreeWayUnion = Annotated[
        Union[MemberX, MemberY, MemberZ],  # noqa: UP007
        FieldInfo(discriminator="kind"),
    ]

    class MixedRequired(Base):
        kind: Literal["r"] = "r"
        mixed_field: str

    class MixedOptional(Base):
        kind: Literal["o"] = "o"
        mixed_field: str | None = None

    class MixedAbsent(Base):
        kind: Literal["a"] = "a"

    MixedRequirednessUnion = Annotated[
        Union[MixedRequired, MixedOptional, MixedAbsent],  # noqa: UP007
        FieldInfo(discriminator="kind"),
    ]

    class AllVarA(Base):
        kind: Literal["a"] = "a"
        everywhere: str | None = None

    class AllVarB(Base):
        kind: Literal["b"] = "b"
        everywhere: str | None = None

    AllVariantsUnion = Annotated[
        Union[AllVarA, AllVarB],  # noqa: UP007
        FieldInfo(discriminator="kind"),
    ]

    @require_any_of("fast", "slow")
    @forbid_if(["restrictions"], FieldEqCondition("gated", True))
    class MemberWithModelConstraints(Base):
        """Union member carrying model constraints over struct/compound fields."""

        kind: Literal["m"] = "m"
        gated: bool = False
        fast: _SpeedStruct | None = None
        slow: _SpeedStruct | None = None
        restrictions: list[str] | None = None

    MemberConstraintUnion = Annotated[
        Union[TypeA, MemberWithModelConstraints],  # noqa: UP007
        FieldInfo(discriminator="kind"),
    ]

    class PlainMember(Base):
        kind: Literal["p"] = "p"


class TestSyntheticUnionChecks:
    @pytest.fixture
    def field_nodes(self) -> list[Check]:
        nodes, _ = _union_checks("Synthetic", _SyntheticUnionFixtures.SyntheticUnion)
        return nodes

    def test_variant_field_gets_variant_values(self, field_nodes: list[Check]) -> None:
        a_nodes = [n for n in field_nodes if n.target == _path("a_field")]
        assert len(a_nodes) > 0
        for node in a_nodes:
            assert node.guards == (ColumnGuard(discriminator="kind", values=("a",)),)

    def test_shared_field_has_no_variant_values(self, field_nodes: list[Check]) -> None:
        kind_nodes = [n for n in field_nodes if n.target == _path("kind")]
        for node in kind_nodes:
            assert node.guards == ()

    def test_b_field_gets_b_variant_value(self, field_nodes: list[Check]) -> None:
        b_nodes = [n for n in field_nodes if n.target == _path("b_field")]
        assert len(b_nodes) > 0
        for node in b_nodes:
            assert node.guards == (ColumnGuard(discriminator="kind", values=("b",)),)

    def test_variant_nodes_carry_discriminator_field(
        self, field_nodes: list[Check]
    ) -> None:
        variant_nodes = [n for n in field_nodes if n.guards]
        for node in variant_nodes:
            for guard in node.guards:
                assert guard.discriminator == "kind"

    @pytest.fixture
    def model_nodes(self) -> list[ModelCheck]:
        return _union_model_nodes("Synthetic", _SyntheticUnionFixtures.SyntheticUnion)

    @pytest.mark.parametrize(
        ("field_name", "expected_value"),
        [("a_field", "b"), ("b_field", "a")],
    )
    def test_variant_field_gets_forbid_if(
        self,
        model_nodes: list[ModelCheck],
        field_name: str,
        expected_value: str,
    ) -> None:
        forbid_nodes = _filter_nodes(model_nodes, "check_forbid_if", (field_name,))
        assert len(forbid_nodes) == 1
        condition = _condition_of(forbid_nodes[0])
        assert isinstance(condition, FieldEqCondition)
        assert condition.field_name == "kind"
        assert condition.value == expected_value

    def test_forbid_if_nodes_are_top_level(self, model_nodes: list[ModelCheck]) -> None:
        forbid_nodes = _filter_nodes(model_nodes, "check_forbid_if")
        assert len(forbid_nodes) == 2
        for node in forbid_nodes:
            assert node.target == ScalarPath()


class TestUnionMemberModelConstraints:
    @pytest.fixture
    def model_nodes(self) -> list[ModelCheck]:
        return _union_model_nodes(
            "Constrained", _SyntheticUnionFixtures.ConstrainedUnion
        )

    def test_member_model_constraints_collected(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        assert len(_filter_nodes(model_nodes, "check_require_any_of")) == 1

    def test_member_constraint_tagged_with_arm(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        """Constraint from ConstrainedMember carries that member's discriminator value."""
        require_any_of_nodes = _filter_nodes(model_nodes, "check_require_any_of")
        assert len(require_any_of_nodes) == 1
        assert require_any_of_nodes[0].arm == "c"

    def test_exclusivity_checks_have_no_arm(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        """Synthesized forbid_if/require_if checks apply to every arm."""
        exclusivity_nodes = _filter_nodes(
            model_nodes, ("check_forbid_if", "check_require_if")
        )
        assert exclusivity_nodes
        for node in exclusivity_nodes:
            assert node.arm is None


class TestUnionMemberStructAndCompoundConstraints:
    """Member-level constraints on struct/compound fields dispatch with real shapes.

    `@require_any_of` over struct fields must unwrap to the first required
    leaf scalar; `@forbid_if` over a compound field must populate
    `field_shapes`. Both depend on the member being run through real
    extraction rather than stubbed proxies -- a latent gap, since no real
    schema member currently carries a model-level constraint decorator.
    """

    @pytest.fixture
    def model_nodes(self) -> list[ModelCheck]:
        return _union_model_nodes(
            "MemberConstraint", _SyntheticUnionFixtures.MemberConstraintUnion
        )

    def test_require_any_of_unwraps_struct_leaf(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        nodes = _filter_nodes(model_nodes, "check_require_any_of")
        assert len(nodes) == 1
        assert set(nodes[0].descriptor.field_names) == {"fast.value", "slow.value"}

    def test_forbid_if_populates_compound_field_shapes(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        # Exclusivity logic also emits a forbid_if for `restrictions`, but
        # gated on the discriminator; the member-level constraint is the
        # one whose condition references `gated`.
        forbid_nodes = _filter_nodes(model_nodes, "check_forbid_if", ("restrictions",))
        member_level = [
            n
            for n in forbid_nodes
            if isinstance((cond := _condition_of(n)), FieldEqCondition)
            and cond.field_name == "gated"
        ]
        assert len(member_level) == 1
        descriptor = member_level[0].descriptor
        assert isinstance(descriptor, ForbidIf)
        assert "restrictions" in dict(descriptor.field_shapes)


@require_any_of("max_speed", "min_speed")
class _SpeedLimitElement(BaseModel):
    """Element model with its own @require_any_of constraint."""

    max_speed: int | None = None
    min_speed: int | None = None


class _VariantWithConstrainedList(_SyntheticUnionFixtures.Base):
    """Union member with a variant-specific list of constrained sub-models."""

    kind: Literal["v"] = "v"
    speed_limits: list[_SpeedLimitElement] | None = None


_VariantFieldConstraintUnion = Annotated[
    Union[_VariantWithConstrainedList, _SyntheticUnionFixtures.PlainMember],  # noqa: UP007
    FieldInfo(discriminator="kind"),
]


class TestVariantSpecificFieldDiscoveredModelConstraints:
    """Model constraints discovered through a variant-specific field carry the contributing arm.

    A `@require_any_of` declared on an element model of a list field that
    appears only in one union arm must be tagged with that arm, not
    propagated to every arm.
    """

    @pytest.fixture
    def model_nodes(self) -> list[ModelCheck]:
        return _union_model_nodes(
            "VariantFieldConstraint", _VariantFieldConstraintUnion
        )

    def test_field_discovered_constraint_tagged_with_arm(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        nodes = [
            n
            for n in _filter_nodes(model_nodes, "check_require_any_of")
            if n.target == _path("speed_limits[]")
        ]
        assert len(nodes) == 1
        assert nodes[0].arm == "v"


class _VariantWithConstrainedModelRef(_SyntheticUnionFixtures.Base):
    """Variant-specific direct (non-list) model ref with model-level constraint."""

    kind: Literal["d"] = "d"
    speed: _SpeedLimitElement | None = None


_DirectModelRefConstraintUnion = Annotated[
    Union[_VariantWithConstrainedModelRef, _SyntheticUnionFixtures.PlainMember],  # noqa: UP007
    FieldInfo(discriminator="kind"),
]


class TestVariantSpecificDirectModelRefConstraint:
    """Variant-specific non-list `ModelRef` with a constrained sub-model is unsupported.

    The direct-ref path routes through `_recurse_into_model` rather
    than the array branch of `_walk_field_shape`, and pure struct
    nesting can't anchor a real model constraint -- the dispatch
    raises `NotImplementedError`. Distinct from the `list[Model]`
    case in `TestVariantSpecificFieldDiscoveredModelConstraints`,
    which is supported.
    """

    def test_direct_modelref_constraint_raises(self) -> None:
        # Pure struct nesting can't anchor a real model constraint; today
        # the only constraint kind that survives struct nesting raises.
        with pytest.raises(
            NotImplementedError, match="Model constraint on struct-nested"
        ):
            _union_model_nodes(
                "DirectModelRefConstraint", _DirectModelRefConstraintUnion
            )


class _OuterWithStructNestedUnion(BaseModel):
    """Non-list `UnionRef` field reaches a union with a constrained member."""

    nested: _SyntheticUnionFixtures.ConstrainedUnion


class TestStructNestedUnionWithConstraint:
    """Non-list `UnionRef` reaching a union with model checks is unsupported.

    `_recurse_into_union` mirrors `_recurse_into_model`'s guard: when
    the prefix is struct-nested (no `ArrayPath` segment) and the union
    would emit either union-level constraints or synthesized
    exclusivity checks (`check_forbid_if`/`check_require_if`), the
    dispatch raises because `_model_constraint_target` would collapse
    the anchor to the row root with field names that don't exist
    there. This fixture exercises the union-level branch; the
    exclusivity branch isn't covered by a synthetic fixture today
    because the dual-trigger raise body is one statement.
    """

    def test_struct_nested_union_constraint_raises(self) -> None:
        with pytest.raises(
            NotImplementedError, match="Model constraint on struct-nested"
        ):
            build_checks(spec_for_model(_OuterWithStructNestedUnion))


class TestStructNestedUnionWithVariantFields:
    """Struct-nested union producing gated field checks is unsupported.

    A `ColumnGuard` carries a bare discriminator name that renders as
    `F.col("<discriminator>")` -- a top-level column access that is wrong
    when the union is reached through a plain struct field. Raising loudly
    is safer than emitting a mis-gated check.

    Distinct from `TestStructNestedUnionWithConstraint`: that class covers
    model/exclusivity checks; this class covers variant-gated field checks
    (the silent-failure path the previous guard missed).

    The trigger spec is built manually (not via `spec_for_model`) because
    Pydantic strips the `Annotated[Union[...], FieldInfo(discriminator=...)]`
    wrapper from `model_fields`, causing the inline extraction path to lose
    `discriminator_mapping`. Constructing `UnionRef(union=...)` directly
    with a fully-extracted union spec (via `union_spec_for`) replicates the
    state that a future extraction path that preserves discriminator metadata
    would produce.
    """

    @pytest.fixture(scope="class")
    def discriminated_union_ref_spec(self) -> RecordSpec:
        """A `RecordSpec` whose `nested` field holds a `UnionRef` with a full discriminator."""
        union_spec = union_spec_for("Synthetic", _SyntheticUnionFixtures.SyntheticUnion)
        field = FieldSpec(
            name="nested",
            shape=UnionRef(union=union_spec),
            description=None,
            is_required=True,
            is_optional=False,
        )
        return RecordSpec(name="Outer", description=None, fields=[field])

    def test_struct_nested_union_variant_fields_raises(
        self, discriminated_union_ref_spec: RecordSpec
    ) -> None:
        with pytest.raises(NotImplementedError, match="ColumnGuard"):
            build_checks(discriminated_union_ref_spec)

    def test_row_root_union_with_variant_fields_succeeds(self) -> None:
        """Row-root union (empty `ScalarPath`) must still build checks without raising."""
        field_checks, _ = _union_checks(
            "Synthetic", _SyntheticUnionFixtures.SyntheticUnion
        )
        assert any(n.guards for n in field_checks)

    def test_array_reached_union_with_variant_fields_succeeds(self) -> None:
        """Array-reached union (`ArrayPath` prefix) must still build checks without raising."""
        field_checks, _ = _checks_for(_ListUnionContainer)
        assert any(n.guards for n in field_checks)


class _NestedInnerBase(BaseModel):
    inner_kind: str


class _NestedInnerArmA(_NestedInnerBase):
    inner_kind: Literal["i_a"] = "i_a"
    a_only: str | None = None


@require_any_of("first", "second")
class _NestedInnerArmB(_NestedInnerBase):
    """Inner-union arm with its own model-level constraint."""

    inner_kind: Literal["i_b"] = "i_b"
    first: str | None = None
    second: str | None = None


_NestedInnerUnion = Annotated[
    Union[_NestedInnerArmA, _NestedInnerArmB],  # noqa: UP007
    FieldInfo(discriminator="inner_kind"),
]


class _OuterArmWithInnerUnion(_SyntheticUnionFixtures.Base):
    """Outer-union arm that wraps a nested union via a list field."""

    kind: Literal["n"] = "n"
    inners: list[_NestedInnerUnion] | None = None


_NestedUnionViaVariantField = Annotated[
    Union[_OuterArmWithInnerUnion, _SyntheticUnionFixtures.PlainMember],  # noqa: UP007
    FieldInfo(discriminator="kind"),
]


class TestNestedUnionThroughVariantField:
    """Inner-union member constraints inherit the outer-union arm.

    Reached through a variant-specific field carrying a nested union,
    the inner member's `@require_any_of` must be tagged with the outer
    arm ('n'), not the inner discriminator value ('i_b'). The outermost
    union's discriminator is the only one per-arm test filtering keys
    on.
    """

    @pytest.fixture
    def model_nodes(self) -> list[ModelCheck]:
        return _union_model_nodes(
            "NestedUnionViaVariantField", _NestedUnionViaVariantField
        )

    def test_inner_member_constraint_tagged_with_outer_arm(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        require_any_of_nodes = _filter_nodes(model_nodes, "check_require_any_of")
        assert len(require_any_of_nodes) == 1
        assert require_any_of_nodes[0].arm == "n"


class _MultiArmContributorA(_SyntheticUnionFixtures.Base):
    kind: Literal["a"] = "a"
    shared_limits: list[_SpeedLimitElement] | None = None


class _MultiArmContributorB(_SyntheticUnionFixtures.Base):
    kind: Literal["b"] = "b"
    shared_limits: list[_SpeedLimitElement] | None = None


class _MultiArmThirdMember(_SyntheticUnionFixtures.Base):
    """Third arm that does NOT contribute the shared field."""

    kind: Literal["c"] = "c"


_MultiArmVariantSourcesUnion = Annotated[
    Union[  # noqa: UP007
        _MultiArmContributorA, _MultiArmContributorB, _MultiArmThirdMember
    ],
    FieldInfo(discriminator="kind"),
]


class TestMultiArmVariantSourcesPolicy:
    """Tombstone: a 2-of-N variant-specific field collapses to `arm=None`.

    No real schema today declares a variant-specific field on a proper
    subset of arms (2-of-N). When/if that pattern surfaces with a
    sub-model carrying its own model constraint, the current policy
    routes the constraint to every arm rather than the intersection --
    including arms the field doesn't belong to. This pins the
    behaviour explicitly so the gap surfaces if anyone treats it as
    correct or relies on it. See `_singleton_arm` in `check_builder.py`.
    """

    @pytest.fixture
    def model_nodes(self) -> list[ModelCheck]:
        return _union_model_nodes(
            "MultiArmVariantSources", _MultiArmVariantSourcesUnion
        )

    def test_multi_arm_field_discovered_constraint_has_no_arm(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        nodes = [
            n
            for n in _filter_nodes(model_nodes, "check_require_any_of")
            if n.target == _path("shared_limits[]")
        ]
        assert len(nodes) == 1
        # The 2-of-N case can't pick a single arm, so the constraint
        # carries arm=None -- broadcasting to every arm, including the
        # third member that doesn't declare shared_limits at all.
        # Tracked for resolution if/when a real schema surfaces this.
        assert nodes[0].arm is None


class TestGroupedExclusivityChecks:
    """A required field with the same name in 2 of 3 variants (different types) groups correctly."""

    @pytest.fixture
    def model_nodes(self) -> list[ModelCheck]:
        return _union_model_nodes("ThreeWay", _SyntheticUnionFixtures.ThreeWayUnion)

    def test_grouped_field_forbid_if_for_excluded_variant(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        forbid_nodes = _filter_nodes(model_nodes, "check_forbid_if", ("shared_name",))
        assert len(forbid_nodes) == 1
        condition = _condition_of(forbid_nodes[0])
        assert isinstance(condition, FieldEqCondition)
        assert condition.field_name == "kind"
        assert condition.value == "z"

    def test_grouped_field_require_if_per_variant(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        require_nodes = _filter_nodes(model_nodes, "check_require_if", ("shared_name",))
        assert len(require_nodes) == 2
        conditions = set()
        for node in require_nodes:
            cond = _condition_of(node)
            assert isinstance(cond, FieldEqCondition)
            conditions.add(cond.value)
        assert conditions == {"x", "y"}


class TestMixedRequirednessExclusivity:
    """Same-named field required in one variant, optional in another."""

    @pytest.fixture
    def model_nodes(self) -> list[ModelCheck]:
        return _union_model_nodes(
            "Mixed", _SyntheticUnionFixtures.MixedRequirednessUnion
        )

    def test_require_if_only_for_required_variant(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        require_nodes = _filter_nodes(model_nodes, "check_require_if", ("mixed_field",))
        assert len(require_nodes) == 1
        condition = _condition_of(require_nodes[0])
        assert isinstance(condition, FieldEqCondition)
        assert condition.value == "r"

    def test_forbid_if_for_absent_variant(self, model_nodes: list[ModelCheck]) -> None:
        forbid_nodes = _filter_nodes(model_nodes, "check_forbid_if", ("mixed_field",))
        assert len(forbid_nodes) == 1
        condition = _condition_of(forbid_nodes[0])
        assert isinstance(condition, FieldEqCondition)
        assert condition.value == "a"


class TestExclusivityEdgeCases:
    def test_no_discriminator_produces_zero_exclusivity_nodes(self) -> None:
        """Union without discriminator_mapping produces no exclusivity checks."""
        spec = replace(
            extract_union("Synthetic", _SyntheticUnionFixtures.SyntheticUnion),
            discriminator_mapping=None,
            discriminator_field=None,
        )
        _, model_nodes = build_checks(spec)
        forbid = _filter_nodes(model_nodes, "check_forbid_if")
        require = _filter_nodes(model_nodes, "check_require_if")
        assert len(forbid) + len(require) == 0

    def test_field_in_all_variants_no_exclusivity(self) -> None:
        """Field present in every variant via variant_sources produces no exclusivity checks."""
        _, model_nodes = _union_checks(
            "AllVariants", _SyntheticUnionFixtures.AllVariantsUnion
        )
        forbid = _filter_nodes(model_nodes, "check_forbid_if")
        require = _filter_nodes(model_nodes, "check_require_if")
        assert len(forbid) + len(require) == 0


@require_any_of("x", "y")
class _ArrayElementWithConstraint(BaseModel):
    x: str | None = None
    y: str | None = None


class _ArrayOfConstrainedModel(BaseModel):
    items: list[_ArrayElementWithConstraint]


class _OptionalArrayOfConstrainedModel(BaseModel):
    items: list[_ArrayElementWithConstraint] | None = None


@require_any_of("a", "b")
class _NestedConstrainedStruct(BaseModel):
    a: str | None = None
    b: str | None = None


class _ArrayElementWithConstrainedNested(BaseModel):
    nested: _NestedConstrainedStruct


class _ArrayOfNestedConstrained(BaseModel):
    items: list[_ArrayElementWithConstrainedNested]


@require_any_of("a", "b")
class _InnerConstrainedElement(BaseModel):
    a: str | None = None
    b: str | None = None


class _OuterElementWithConstrainedList(BaseModel):
    things: list[_InnerConstrainedElement]


class _DoubleNestedConstrained(BaseModel):
    items: list[_OuterElementWithConstrainedList]


def _require_any_node_for(model_cls: type[BaseModel]) -> ModelCheck:
    _, model_nodes = _checks_for(model_cls)
    nodes = _filter_nodes(model_nodes, "check_require_any_of")
    assert len(nodes) == 1
    return nodes[0]


@pytest.mark.parametrize(
    ("model_cls", "expected_target"),
    [
        pytest.param(_ArrayOfConstrainedModel, _path("items[]"), id="direct_element"),
        pytest.param(
            _ArrayOfNestedConstrained, _path("items[].nested"), id="nested_struct"
        ),
    ],
)
class TestArrayContextModelConstraints:
    """Model constraints on array-element (or nested struct) models produce array-context ModelChecks."""

    def test_produces_model_check_node(
        self, model_cls: type[BaseModel], expected_target: FieldPath
    ) -> None:
        node = _require_any_node_for(model_cls)
        assert model_constraint_function(node.descriptor) == "check_require_any_of"

    def test_target(
        self, model_cls: type[BaseModel], expected_target: FieldPath
    ) -> None:
        node = _require_any_node_for(model_cls)
        assert node.target == expected_target


class TestDoubleNestedArrayModelConstraints:
    """Model constraints on list[] elements nested inside another array use nested geometry."""

    def test_target_is_nested_inner_array(self) -> None:
        # `things` is itself an ArraySegment, so the constraint's target
        # iterates items[] then things[] with no struct nav between.
        node = _require_any_node_for(_DoubleNestedConstrained)
        assert node.target == _path("items[].things[]")


class TestSegmentUnionChecks:
    @pytest.fixture(scope="class")
    def segment_spec(self) -> ModelSpec:
        return discover_feature("Segment")

    @pytest.fixture(scope="class")
    def segment_checks(
        self, segment_spec: ModelSpec
    ) -> tuple[list[Check], list[ModelCheck]]:
        return build_checks(segment_spec)

    @pytest.fixture(scope="class")
    def field_nodes(
        self, segment_checks: tuple[list[Check], list[ModelCheck]]
    ) -> list[Check]:
        return segment_checks[0]

    @pytest.fixture(scope="class")
    def model_nodes(
        self, segment_checks: tuple[list[Check], list[ModelCheck]]
    ) -> list[ModelCheck]:
        return segment_checks[1]

    def test_produces_variant_gated_checks(self, field_nodes: list[Check]) -> None:
        variant_nodes = [n for n in field_nodes if n.guards]
        assert len(variant_nodes) > 0

    def test_shared_fields_have_no_variant_values(
        self, field_nodes: list[Check]
    ) -> None:
        subtype_nodes = [n for n in field_nodes if n.target == _path("subtype")]
        for node in subtype_nodes:
            assert node.guards == ()

    def test_speed_limits_require_any_of_in_model_nodes(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        speed_limit_nodes = [
            n
            for n in _filter_nodes(model_nodes, "check_require_any_of")
            if n.target == _path("speed_limits[]")
        ]
        assert len(speed_limit_nodes) >= 1

    def test_destinations_require_any_of_in_model_nodes(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        dest_nodes = [
            n
            for n in _filter_nodes(model_nodes, "check_require_any_of")
            if n.target == _path("destinations[]")
        ]
        assert len(dest_nodes) >= 1

    def test_speed_limits_when_require_any_of_in_model_nodes(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        when_nodes = [
            n
            for n in _filter_nodes(model_nodes, "check_require_any_of")
            if n.target == _path("speed_limits[].when")
        ]
        assert len(when_nodes) >= 1

    @pytest.mark.parametrize(
        ("field_name", "expected_subtype"),
        [("road_surface", "road"), ("rail_flags", "rail")],
    )
    def test_single_variant_field_forbid_if(
        self,
        model_nodes: list[ModelCheck],
        field_name: str,
        expected_subtype: str,
    ) -> None:
        forbid_nodes = _filter_nodes(model_nodes, "check_forbid_if", (field_name,))
        assert len(forbid_nodes) == 1
        condition = _condition_of(forbid_nodes[0])
        assert isinstance(condition, Not)
        assert isinstance(condition.inner, FieldEqCondition)
        assert condition.inner.field_name == "subtype"
        assert condition.inner.value == expected_subtype

    def test_class_forbid_if_for_water(self, model_nodes: list[ModelCheck]) -> None:
        forbid_nodes = _filter_nodes(model_nodes, "check_forbid_if", ("class",))
        assert len(forbid_nodes) == 1
        condition = _condition_of(forbid_nodes[0])
        assert isinstance(condition, FieldEqCondition)
        assert condition.field_name == "subtype"
        assert condition.value == "water"

    def test_class_require_if_for_road_and_rail(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        require_nodes = _filter_nodes(model_nodes, "check_require_if", ("class",))
        assert len(require_nodes) == 2
        conditions = [_condition_of(n) for n in require_nodes]
        assert all(isinstance(c, FieldEqCondition) for c in conditions)
        values = {c.value for c in conditions if isinstance(c, FieldEqCondition)}
        assert values == {"road", "rail"}

    def test_nested_union_discriminator_preserved(
        self, field_nodes: list[Check]
    ) -> None:
        """Inner VehicleSelector discriminator survives outer Segment annotation.

        Vehicle unit checks inside variant-specific fields (speed_limits,
        prohibited_transitions) need both the outer subtype guard and the
        inner dimension discriminator. The outer annotation must not
        clobber the inner one.
        """
        unit_nodes = [
            n for n in field_nodes if "vehicle[].unit" in str(n.target) and n.guards
        ]
        assert len(unit_nodes) > 0, "Expected variant-gated vehicle unit nodes"

        for node in unit_nodes:
            inner = _element_guard(node)
            assert inner is not None, (
                f"{node.target}: inner discriminator should be element-level, "
                f"got guards {node.guards}"
            )
            assert inner.discriminator == "dimension", (
                f"{node.target}: inner discriminator should be 'dimension', "
                f"got {inner.discriminator!r}"
            )

        # Variant-specific fields (speed_limits, prohibited_transitions)
        # also need the outer subtype guard.
        speed_unit_nodes = [n for n in unit_nodes if "speed_limits" in str(n.target)]
        for node in speed_unit_nodes:
            outer = _column_guard(node)
            assert outer is not None, f"{node.target}: missing outer subtype guard"
            assert outer.discriminator == "subtype", (
                f"{node.target}: outer discriminator should be 'subtype', "
                f"got {outer.discriminator!r}"
            )

    def test_segment_vehicle_selector_field_checks(
        self, field_nodes: list[Check]
    ) -> None:
        """VehicleSelector fields appear with correct nesting."""
        vehicle_nodes = [n for n in field_nodes if "vehicle[]" in str(n.target)]
        assert len(vehicle_nodes) > 0

        dim_nodes = [n for n in vehicle_nodes if "dimension" in str(n.target)]
        assert any("speed_limits" in str(n.target) for n in dim_nodes)
        assert any("access_restrictions" in str(n.target) for n in dim_nodes)

        for node in dim_nodes:
            assert isinstance(node.target, ArrayPath)
            # vehicle[] is nested inside an outer array (speed_limits, etc.),
            # so the struct nav to `dimension` lands in the target's leaf.
            assert len(node.target.leaf) >= 1

    def test_segment_vehicle_selector_exclusivity(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        """VehicleSelector produces forbid_if/require_if for unit field."""
        vehicle_forbid = [
            n
            for n in _filter_nodes(model_nodes, "check_forbid_if")
            if "unit" in n.descriptor.field_names and isinstance(n.target, ArrayPath)
        ]
        assert len(vehicle_forbid) > 0

        vehicle_require = [
            n
            for n in _filter_nodes(model_nodes, "check_require_if")
            if "unit" in n.descriptor.field_names and isinstance(n.target, ArrayPath)
        ]
        assert len(vehicle_require) > 0

    def test_segment_vehicle_selector_exclusivity_has_inner_levels(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        """VehicleSelector exclusivity checks use nested geometry to reach vehicle[]."""
        vehicle_constraint_nodes = [
            n
            for n in _filter_nodes(model_nodes, ("check_forbid_if", "check_require_if"))
            if "unit" in n.descriptor.field_names and isinstance(n.target, ArrayPath)
        ]
        for node in vehicle_constraint_nodes:
            assert isinstance(node.target, ArrayPath)
            # The target reaches the inner vehicle[] via a second iteration:
            # one inner level navigating `when` to the `vehicle` array.
            iter_paths = node.target.iter_struct_paths
            assert len(iter_paths) == 1
            assert "when" in iter_paths[0]
            assert "vehicle" in iter_paths[0]


class _InnerBase(BaseModel):
    kind: str


class _InnerA(_InnerBase):
    kind: Literal["a"] = "a"
    a_field: str


class _InnerB(_InnerBase):
    kind: Literal["b"] = "b"
    b_field: int = Field(ge=0)


_InnerUnion = Annotated[
    _InnerA | _InnerB,
    Field(discriminator="kind"),
]


class _Wrapper(BaseModel):
    items: list[_InnerUnion]


class TestUnionInsideArray:
    """UNION-kind fields nested inside list[] produce variant-gated checks."""

    @pytest.fixture(scope="class")
    def results(self) -> tuple[list[Check], list[ModelCheck]]:
        return build_checks(spec_for_model(_Wrapper))

    @pytest.fixture(scope="class")
    def field_nodes(self, results: tuple[list[Check], list[ModelCheck]]) -> list[Check]:
        return results[0]

    @pytest.fixture(scope="class")
    def model_nodes(
        self, results: tuple[list[Check], list[ModelCheck]]
    ) -> list[ModelCheck]:
        return results[1]

    @pytest.fixture(scope="class")
    def a_nodes(self, field_nodes: list[Check]) -> list[Check]:
        return [n for n in field_nodes if n.target == _path("items[].a_field")]

    @pytest.fixture(scope="class")
    def b_nodes(self, field_nodes: list[Check]) -> list[Check]:
        return [n for n in field_nodes if n.target == _path("items[].b_field")]

    def test_a_field_check_produced(self, a_nodes: list[Check]) -> None:
        assert len(a_nodes) >= 1

    def test_a_field_is_array_shape(self, a_nodes: list[Check]) -> None:
        assert isinstance(a_nodes[0].target, ArrayPath)

    def test_a_field_target_is_items(self, a_nodes: list[Check]) -> None:
        assert a_nodes[0].target == _path("items[].a_field")

    def test_a_field_guard(self, a_nodes: list[Check]) -> None:
        assert a_nodes[0].guards == (ElementGuard(discriminator="kind", values=("a",)),)

    def test_a_nodes_have_array_shape(self, a_nodes: list[Check]) -> None:
        assert all(isinstance(n.target, ArrayPath) for n in a_nodes)

    def test_b_field_check_produced(self, b_nodes: list[Check]) -> None:
        assert len(b_nodes) >= 1

    def test_b_field_guard(self, b_nodes: list[Check]) -> None:
        assert b_nodes[0].guards == (ElementGuard(discriminator="kind", values=("b",)),)

    def test_b_nodes_have_array_shape(self, b_nodes: list[Check]) -> None:
        assert all(isinstance(n.target, ArrayPath) for n in b_nodes)

    def test_forbid_nodes_produced(self, model_nodes: list[ModelCheck]) -> None:
        forbid_nodes = _filter_nodes(model_nodes, "check_forbid_if")
        assert len(forbid_nodes) > 0

    def test_forbid_nodes_have_array_column_path(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        forbid_nodes = _filter_nodes(model_nodes, "check_forbid_if")
        for node in forbid_nodes:
            assert node.target == _path("items[]")

    def test_require_if_model_nodes_have_array_column_path(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        require_nodes = _filter_nodes(model_nodes, "check_require_if")
        for node in require_nodes:
            assert node.target == _path("items[]")


class TestTopLevelUnionColumnPath:
    """Top-level union (not inside array) exclusivity nodes have column_path=None."""

    @pytest.fixture(scope="class")
    def model_nodes(self) -> list[ModelCheck]:
        return _union_model_nodes("Synthetic", _SyntheticUnionFixtures.SyntheticUnion)

    def test_forbid_if_column_path_is_none(self, model_nodes: list[ModelCheck]) -> None:
        forbid_nodes = _filter_nodes(model_nodes, "check_forbid_if")
        assert len(forbid_nodes) > 0
        for node in forbid_nodes:
            assert node.target == ScalarPath()

    def test_require_if_column_path_is_none(
        self, model_nodes: list[ModelCheck]
    ) -> None:
        require_nodes = _filter_nodes(model_nodes, "check_require_if")
        for node in require_nodes:
            assert node.target == ScalarPath()


class _ListUnionContainer(BaseModel):
    """Top-level list of a discriminated union.

    The variant fields live inside each list element, so variant gating
    must reference the element-level discriminator (`el["kind"]`), not a
    top-level column (`F.col("kind")`).
    """

    items: list[_SyntheticUnionFixtures.SyntheticUnion]


class TestTopLevelListUnion:
    """Field-level checks for `list[DiscriminatedUnion]` at the feature root.

    Regression test: the discriminator must be flagged as element-level so
    the renderer accesses `el["kind"]` rather than `F.col("kind")`.
    """

    @pytest.fixture()
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(_ListUnionContainer)
        return nodes

    def test_variant_field_uses_element_level_discriminator(
        self, nodes: list[Check]
    ) -> None:
        for variant_field in ("a_field", "b_field"):
            variant_nodes = [n for n in nodes if variant_field in str(n.target)]
            assert variant_nodes, f"Expected variant-gated {variant_field} nodes"
            for node in variant_nodes:
                guard = _element_guard(node)
                assert guard is not None, (
                    f"{node.target}: list[Union] descendants must use the "
                    "element-level discriminator"
                )
                assert guard.discriminator == "kind", (
                    f"{node.target}: discriminator should be 'kind'"
                )


class _NestedListUnionContainer(BaseModel):
    """Top-level `list[list[DiscriminatedUnion]]` with a constrained member.

    A union nested under multiple list layers would need the union
    target to record `list_depth` iterations, but the rebase in
    `_recurse_into_union` records only one. No real schema exercises
    this path; `build_checks` raises rather than emit a target that
    silently drops iterations.
    """

    nested: list[list[_SyntheticUnionFixtures.ConstrainedUnion]]


class TestNestedListUnionModelConstraints:
    """`list[list[Union]]` raises rather than emit a collapsed target."""

    def test_build_checks_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="multiple list layers"):
            _checks_for(_NestedListUnionContainer)


class _DeepInnerModel(BaseModel):
    value: Annotated[str, Field(min_length=1)]


class _DoubleNestedArrayModel(BaseModel):
    items: list[list[_DeepInnerModel]]


class TestDoubleNestedArrayFieldChecks:
    """Sub-field validation for list[list[Model]] (list_depth=2)."""

    @pytest.fixture()
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(_DoubleNestedArrayModel)
        return nodes

    def test_subfield_target_encodes_both_array_levels(
        self, nodes: list[Check]
    ) -> None:
        # A `list[list[Model]]` sub-field reaches `value` through a single
        # ArraySegment with iter_count=2; the target pins the full geometry.
        assert any(n.target == _path("items[][].value") for n in nodes)


class TestTripleNestedArrayFieldChecks:
    """Verify depth=3 nesting generates correct geometry."""

    @pytest.fixture()
    def nodes(self) -> list[Check]:
        nodes, _ = _checks_for(TripleNestedArrayModel)
        return nodes

    def test_subfield_target_shows_three_brackets(self, nodes: list[Check]) -> None:
        assert any(n.target == _path("deep[][][].tag") for n in nodes)


class _NestedScalarListModel(BaseModel):
    """list[list[scalar]] terminating directly in a constrained scalar.

    Exercises the one nested-array geometry the other tests miss: an
    element-level check whose target's terminal ArraySegment carries
    iter_count > 1 with no struct leaf after it (`grid[][]`, not
    `grid[][].field`).
    """

    grid: list[list[Annotated[str, MinLen(1)]]]


class TestNestedScalarListTarget:
    """Element-level check on list[list[scalar]] targets a bare `field[][]`."""

    def test_terminal_target_carries_iter_count_two(self) -> None:
        nodes, _ = _checks_for(_NestedScalarListModel)
        node = _node_for(nodes, "grid[][]", "check_string_min_length")
        target = node.target
        assert isinstance(target, ArrayPath)
        last = target.segments[-1]
        assert isinstance(last, ArraySegment)
        assert last.name == "grid"
        assert last.iter_count == 2


class TestPrimitiveBoundsFiltered:
    """Constraints inherent to primitive numeric types are filtered out."""

    @pytest.fixture
    def nodes(self) -> list[Check]:
        """Field with int32-inherent and layered bounds."""
        shape = Primitive(
            base_type="int32",
            constraints=(
                # Layered by schema author
                ConstraintSource(
                    source_ref=None, source_name="FeatureVersion", constraint=Ge(ge=0)
                ),
                # Inherent to int32
                ConstraintSource(
                    source_ref=None, source_name="int32", constraint=Ge(ge=-(2**31))
                ),
                ConstraintSource(
                    source_ref=None, source_name="int32", constraint=Le(le=2**31 - 1)
                ),
            ),
        )
        field = FieldSpec(
            name="version", shape=shape, description=None, is_required=True
        )
        spec = RecordSpec(name="Test", description=None, fields=[field])
        nodes, _ = build_checks(spec)
        return nodes

    def test_layered_bound_survives(self, nodes: list[Check]) -> None:
        descs = nodes[0].descriptors
        bounds = [d for d in descs if d.function == "check_bounds"]
        assert len(bounds) == 1
        assert dict(bounds[0].kwargs) == {"ge": 0}

    def test_primitive_bounds_excluded(self, nodes: list[Check]) -> None:
        descs = nodes[0].descriptors
        bounds = [d for d in descs if d.function == "check_bounds"]
        for b in bounds:
            d = dict(b.kwargs)
            assert d.get("ge") != -(2**31)
            assert d.get("le") != 2**31 - 1


@require_any_of("x", "y")
class _OptionalSubModelConstrained(BaseModel):
    """Sub-model with require_any_of on its own fields."""

    x: str | None = None
    y: str | None = None


class _ElementWithOptionalConstrained(BaseModel):
    nested: _OptionalSubModelConstrained | None = None


class _ArrayOfElementWithOptionalConstrained(BaseModel):
    items: list[_ElementWithOptionalConstrained]


class TestOptionalSubModelModelCheckGate:
    """ModelCheck for a constraint on an optional sub-model carries gate set to its path.

    When the constrained model is reached via an optional field (`field: Model | None`),
    the PySpark validator must skip the constraint when the field is NULL. The
    `ModelCheck.gate` carries the path to the optional field so the renderer can emit
    `F.when(<accessor>.isNotNull(), ...)`.
    """

    def test_optional_nested_model_gate_set(self) -> None:
        """items[].nested is optional -- gate == path to nested."""
        _, model_nodes = _checks_for(_ArrayOfElementWithOptionalConstrained)
        nodes = [
            n
            for n in _filter_nodes(model_nodes, "check_require_any_of")
            if n.target == _path("items[].nested")
        ]
        assert len(nodes) == 1
        assert nodes[0].gate == _path("items[].nested")

    def test_non_optional_sub_model_has_no_gate(self) -> None:
        """Direct array element model (not optional) -- gate is None."""
        _, model_nodes = _checks_for(_ArrayOfConstrainedModel)
        nodes = [
            n
            for n in _filter_nodes(model_nodes, "check_require_any_of")
            if n.target == _path("items[]")
        ]
        assert len(nodes) == 1
        assert nodes[0].gate is None

    def test_optional_list_field_element_model_has_no_gate(self) -> None:
        """Optional list field (list[Model] | None) -- element constraint gate is None.

        The field being optional means the list itself may be absent; but the
        constrained model is reached via array iteration, not a nullable struct
        field, so no element-level gate belongs.
        """
        _, model_nodes = _checks_for(_OptionalArrayOfConstrainedModel)
        nodes = [
            n
            for n in _filter_nodes(model_nodes, "check_require_any_of")
            if n.target == _path("items[]")
        ]
        assert len(nodes) == 1
        assert nodes[0].gate is None

    def test_segment_speed_limits_when_has_gate(self) -> None:
        """Segment.speed_limits[].when is optional -- gate == path to when."""
        from codegen_test_support import discover_feature

        spec = discover_feature("Segment")
        _, model_nodes = build_checks(spec)
        when_nodes = [
            n
            for n in _filter_nodes(model_nodes, "check_require_any_of")
            if n.target == _path("speed_limits[].when")
        ]
        assert len(when_nodes) >= 1
        for node in when_nodes:
            assert node.gate == _path("speed_limits[].when")


class TestMapKeyValueConstraints:
    """check_builder descends into MapOf key/value shapes.

    `FeatureWithDict.names` is `dict[LanguageTag, StrippedString]`: the key
    carries `LanguageTagConstraint` (dispatches to check_pattern) and the
    value carries `StrippedConstraint` (dispatches to check_stripped). Both
    constraints are validated when the same NewTypes are reached through a
    struct field -- generated transportation/segment.py emits check_pattern
    for `names.rules[].language` -- so reaching them through a map must not
    silently drop validation.
    """

    def _map_check(self, projection: MapProjection, function: str) -> Check:
        field_checks, _ = _checks_for(FeatureWithDict)
        matches = [
            c
            for c in field_checks
            if isinstance(c.target, MapPath)
            and c.target.projection is projection
            and any(d.function == function for d in c.descriptors)
        ]
        assert len(matches) >= 1, (
            f"no MapPath {projection} check with {function}; "
            f"targets={[str(c.target) for c in field_checks]}"
        )
        return matches[0]

    def test_map_key_pattern_check_targets_names_key(self) -> None:
        check = self._map_check(MapProjection.KEY, "check_pattern")
        assert str(check.target) == "names{key}"

    def test_map_value_stripped_check_targets_names_value(self) -> None:
        check = self._map_check(MapProjection.VALUE, "check_stripped")
        assert str(check.target) == "names{value}"

    def test_map_field_with_unconstrained_value_emits_no_value_check(self) -> None:
        # metadata: dict[str, int] -- neither key nor value carries a
        # constraint, so no MapPath checks are produced for it.
        field_checks, _ = _checks_for(FeatureWithDict)
        metadata_maps = [
            c
            for c in field_checks
            if isinstance(c.target, MapPath) and c.target.map_column == "metadata"
        ]
        assert metadata_maps == []


class _MapWithConstrainedListValueModel(BaseModel):
    """`dict[K, list[constrained-scalar]]` -- a map value carrying an array layer.

    `terminal_scalar` unwraps the `ArrayOf` to the inner scalar, so the
    naive scalar guard lets this through; the value scalar's constraint
    has no `MapPath` + `ArraySegment` geometry to land on.
    """

    items: dict[str, list[Annotated[str, MinLen(1)]]]


class _MapWithUnconstrainedListValueModel(BaseModel):
    """`dict[K, list[scalar]]` with no key/value constraint -- nothing to emit."""

    items: dict[str, list[int]]


class _ListOfConstrainedMapModel(BaseModel):
    """`list[dict[K, constrained-scalar]]` -- a map reached through an array."""

    items: list[dict[str, Annotated[str, MinLen(1)]]]


class _ListOfUnconstrainedMapModel(BaseModel):
    """`list[dict[K, scalar]]` with no key/value constraint -- nothing to emit."""

    items: list[dict[str, str]]


class TestMapProjectionUnsupportedShapes:
    """`_map_projection_checks` is bounded to a scalar terminal reached struct-only.

    Three shapes fall outside that bound -- a map value/key with an array
    layer (`dict[K, list[V]]`), and a map reached through an array
    (`list[dict[K, V]]`). For each, a key/value constraint raises to keep
    the dropped check loud, and an unconstrained one yields no checks (a
    `MapPath` cannot locate the value, but there is nothing to validate).
    """

    def test_constrained_list_value_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="map value"):
            _checks_for(_MapWithConstrainedListValueModel)

    def test_unconstrained_list_value_emits_no_projection_check(self) -> None:
        field_checks, _ = _checks_for(_MapWithUnconstrainedListValueModel)
        assert not any(isinstance(c.target, MapPath) for c in field_checks)

    def test_constrained_map_in_array_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="map value"):
            _checks_for(_ListOfConstrainedMapModel)

    def test_unconstrained_map_in_array_emits_no_projection_check(self) -> None:
        field_checks, _ = _checks_for(_ListOfUnconstrainedMapModel)
        assert not any(isinstance(c.target, MapPath) for c in field_checks)


class _InnerLabel(BaseModel):
    label: Annotated[str, MinLen(1)]


class _MapOfModel(BaseModel):
    """A `dict[K, Model]` value model with a constrained scalar field.

    The value model's `label` field is validated on a `MapPath` leaf
    (`items{value}.label`), the map analogue of a `list[Model]` element.
    """

    items: dict[str, _InnerLabel]


@require_any_of("foo", "bar")
class _AnyOfSub(BaseModel):
    foo: int | None = None
    bar: str | None = None


class _ModelConstraintAsMapValue(BaseModel):
    """A `dict[K, Model]` value model carrying a model-level constraint.

    The `require_any_of` constraint is validated on the map value itself
    (`subs{value}`).
    """

    subs: dict[str, _AnyOfSub]


class TestMapValueModelDescent:
    """check_builder descends into a `dict[K, Model]` value model.

    A `ModelRef`/`UnionRef` map value is walked for its field and
    model-level constraints on a `MapPath` target, the map analogue of a
    `list[Model]` element reached through the `ModelRef` walker arm.
    """

    def test_value_field_constraint_targets_map_value_leaf(self) -> None:
        field_checks, _ = _checks_for(_MapOfModel)
        matches = [
            c
            for c in field_checks
            if isinstance(c.target, MapPath)
            and str(c.target) == "items{value}.label"
            and any(d.function == "check_string_min_length" for d in c.descriptors)
        ]
        assert len(matches) == 1, [str(c.target) for c in field_checks]

    def test_value_required_field_emits_required_descriptor(self) -> None:
        field_checks, _ = _checks_for(_MapOfModel)
        leaf_checks = [
            c
            for c in field_checks
            if isinstance(c.target, MapPath) and str(c.target) == "items{value}.label"
        ]
        assert leaf_checks
        functions = {d.function for c in leaf_checks for d in c.descriptors}
        assert "check_required" in functions

    def test_value_model_constraint_targets_map_value(self) -> None:
        _, model_checks = _checks_for(_ModelConstraintAsMapValue)
        matches = _filter_nodes(model_checks, "check_require_any_of", ("foo", "bar"))
        assert len(matches) == 1
        assert isinstance(matches[0].target, MapPath)
        assert str(matches[0].target) == "subs{value}"


class _MapValueWithList(BaseModel):
    tags: list[Annotated[str, MinLen(1)]]


class _ListInsideMapValueModel(BaseModel):
    """A `dict[K, Model]` value model with a constrained list field.

    A list nested inside a map element has no representable `MapPath`, so
    the descent raises rather than emitting an unanchored target.
    """

    items: dict[str, _MapValueWithList]


class TestMapValueModelDescentBoundary:
    """Descent raises where a `MapPath` cannot represent the shape.

    A map value model is descended into for scalar fields and model
    constraints; a container (list or map) nested inside it has no
    `MapPath` geometry, so the walker raises rather than emitting an
    unvalidated target.
    """

    def test_list_inside_map_value_model_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="list nested inside a map"):
            _checks_for(_ListInsideMapValueModel)
