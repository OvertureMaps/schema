"""Tests for Arrow schema renderer."""

from enum import Enum as StdEnum
from typing import Annotated, Literal

import pyarrow as pa  # type: ignore[import-untyped]
import pytest
from overture.schema.codegen.arrow_renderer import (
    field_spec_to_arrow,
    merge_model_variants,
    model_spec_to_arrow_schema,
    type_info_to_arrow,
    union_spec_to_arrow_schema,
)
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.extraction.specs import (
    ModelSpec,
    UnionSpec,
    filter_model_classes,
    is_union_alias,
)
from overture.schema.codegen.extraction.type_analyzer import UnsupportedUnionError
from overture.schema.codegen.extraction.union_extraction import extract_union
from overture.schema.system.primitive import (
    BBox,
    Geometry,
    float32,
    float64,
    int8,
    int16,
    int32,
    int64,
    uint8,
)
from pydantic import BaseModel, Field


def _arrow_type_for(annotation: object) -> pa.DataType:
    """Build a single-field model with the given annotation, return its Arrow type."""
    model = type("_M", (BaseModel,), {"__annotations__": {"f": annotation}})
    spec = extract_model(model)
    return type_info_to_arrow(spec.fields[0].type_info)


def _arrow_field_for(
    annotation: object,
    *,
    default: object = ...,
    description: str | None = None,
) -> pa.Field:
    """Build a single-field model with the given annotation, return its Arrow field."""
    attrs: dict[str, object] = {"__annotations__": {"f": annotation}}
    if description is not None or default is not ...:
        attrs["f"] = Field(default=default, description=description)
    model = type("_M", (BaseModel,), attrs)
    spec = extract_model(model)
    return field_spec_to_arrow(spec.fields[0])


class _UnionBase(BaseModel):
    type: str
    shared: str


class _VariantA(_UnionBase):
    type: Literal["a"] = "a"
    a_only: int32


class _VariantB(_UnionBase):
    type: Literal["b"] = "b"
    b_only: float64


_UNION_ANNOTATION = Annotated[_VariantA | _VariantB, Field(discriminator="type")]


@pytest.fixture
def union_spec() -> UnionSpec:
    return extract_union("TestUnion", _UNION_ANNOTATION)


class TestTypeInfoToArrowPrimitives:
    """Primitive scalar types map to Arrow types."""

    @pytest.mark.parametrize(
        ("annotation", "expected"),
        [
            (str, pa.utf8()),
            (bool, pa.bool_()),
            (int8, pa.int8()),
            (int16, pa.int16()),
            (int32, pa.int32()),
            (int64, pa.int64()),
            (float32, pa.float32()),
            (float64, pa.float64()),
            (Geometry, pa.binary()),
        ],
        ids=lambda x: getattr(x, "__name__", str(x)),
    )
    def test_primitive_mapping(self, annotation: object, expected: pa.DataType) -> None:
        assert _arrow_type_for(annotation) == expected

    def test_bbox_maps_to_struct(self) -> None:
        result = _arrow_type_for(BBox)
        assert isinstance(result, pa.StructType)
        assert result.num_fields == 4
        for name in ("xmin", "ymin", "xmax", "ymax"):
            idx = result.get_field_index(name)
            assert idx >= 0, f"missing field {name}"
            assert result.field(idx).type == pa.float64()


class TestTypeInfoToArrowFallbacks:
    """Enums and Literals fall back to utf8."""

    def test_enum_maps_to_utf8(self) -> None:
        class Color(str, StdEnum):
            RED = "red"
            BLUE = "blue"

        assert _arrow_type_for(Color) == pa.utf8()

    def test_literal_maps_to_utf8(self) -> None:
        assert _arrow_type_for(Literal["building"]) == pa.utf8()


class TestTypeInfoToArrowLists:
    """List types wrap element types with pa.list_()."""

    @pytest.mark.parametrize(
        ("annotation", "expected"),
        [
            (list[str], pa.list_(pa.utf8())),
            (list[int32], pa.list_(pa.int32())),
            (list[list[str]], pa.list_(pa.list_(pa.utf8()))),
            (list[dict[str, int32]], pa.list_(pa.map_(pa.utf8(), pa.int32()))),
        ],
        ids=["str", "int32", "nested_list", "list_of_dict"],
    )
    def test_list_mapping(self, annotation: object, expected: pa.DataType) -> None:
        assert _arrow_type_for(annotation) == expected


class TestTypeInfoToArrowDicts:
    """Dict types map to Arrow map types."""

    @pytest.mark.parametrize(
        ("annotation", "expected"),
        [
            (dict[str, str], pa.map_(pa.utf8(), pa.utf8())),
            (dict[str, int32], pa.map_(pa.utf8(), pa.int32())),
        ],
        ids=["str_str", "str_int32"],
    )
    def test_dict_mapping(self, annotation: object, expected: pa.DataType) -> None:
        assert _arrow_type_for(annotation) == expected

    def test_optional_dict_nullable(self) -> None:
        result = _arrow_field_for(dict[str, str] | None, default=None)
        assert result.nullable is True
        assert result.type == pa.map_(pa.utf8(), pa.utf8())


class TestTypeInfoToArrowUnions:
    """Inline union fields produce merged structs."""

    def test_union_field_becomes_struct(self) -> None:
        result = _arrow_type_for(_UNION_ANNOTATION)
        assert isinstance(result, pa.StructType)
        assert result.get_field_index("type") >= 0
        assert result.get_field_index("shared") >= 0
        assert result.get_field_index("a_only") >= 0
        assert result.get_field_index("b_only") >= 0

    def test_list_of_union_becomes_list_of_struct(self) -> None:
        result = _arrow_type_for(list[_UNION_ANNOTATION])
        assert isinstance(result, pa.ListType)
        assert isinstance(result.value_type, pa.StructType)


class TestFieldSpecToArrow:
    """FieldSpec converts to pa.Field with nullability."""

    def test_required_field_not_nullable(self) -> None:
        result = _arrow_field_for(str)
        assert result == pa.field("f", pa.utf8(), nullable=False)

    def test_optional_field_nullable(self) -> None:
        result = _arrow_field_for(str | None, default=None)
        assert result == pa.field("f", pa.utf8(), nullable=True)

    def test_field_name_from_alias(self) -> None:
        class M(BaseModel):
            class_: str | None = Field(default=None, alias="class")

        spec = extract_model(M)
        result = field_spec_to_arrow(spec.fields[0])
        assert result.name == "class"


class TestModelSpecToArrowSchema:
    """ModelSpec converts to pa.Schema."""

    def test_simple_model(self) -> None:
        class M(BaseModel):
            id: str
            count: int32
            label: str | None = None

        spec = extract_model(M)
        result = model_spec_to_arrow_schema(spec)
        assert isinstance(result, pa.Schema)
        assert result.field("id").type == pa.utf8()
        assert result.field("id").nullable is False
        assert result.field("count").type == pa.int32()
        assert result.field("count").nullable is False
        assert result.field("label").type == pa.utf8()
        assert result.field("label").nullable is True

    def test_schema_field_count(self) -> None:
        class M(BaseModel):
            a: str
            b: int32

        spec = extract_model(M)
        result = model_spec_to_arrow_schema(spec)
        assert len(result) == 2

    def test_schema_metadata_with_version_and_model(self) -> None:
        class M(BaseModel):
            id: str

        spec = extract_model(M)
        spec.entry_point = "overture.schema.buildings:Building"
        result = model_spec_to_arrow_schema(spec, version="1.2.3")
        assert result.metadata == {
            b"overture-schema.version": b"1.2.3",
            b"model": b"overture.schema.buildings:Building",
        }

    def test_schema_metadata_version_only(self) -> None:
        class M(BaseModel):
            id: str

        spec = extract_model(M)
        result = model_spec_to_arrow_schema(spec, version="1.0.0")
        assert result.metadata == {b"overture-schema.version": b"1.0.0"}

    def test_schema_metadata_model_only(self) -> None:
        class M(BaseModel):
            id: str

        spec = extract_model(M)
        spec.entry_point = "overture.schema.places:Place"
        result = model_spec_to_arrow_schema(spec)
        assert result.metadata == {b"model": b"overture.schema.places:Place"}

    def test_schema_metadata_absent_by_default(self) -> None:
        class M(BaseModel):
            id: str

        spec = extract_model(M)
        result = model_spec_to_arrow_schema(spec)
        assert result.metadata is None


class TestArrowNestedModels:
    """MODEL-kind fields expand to Arrow struct types."""

    def test_nested_model_becomes_struct(self) -> None:
        class Inner(BaseModel):
            x: int32
            y: int32

        class Outer(BaseModel):
            point: Inner

        spec = extract_model(Outer)
        result = type_info_to_arrow(spec.fields[0].type_info)
        assert isinstance(result, pa.StructType)
        assert result.get_field_index("x") >= 0
        assert result.field("x").type == pa.int32()

    def test_optional_nested_model(self) -> None:
        class Inner(BaseModel):
            val: str

        class Outer(BaseModel):
            nested: Inner | None = None

        spec = extract_model(Outer)
        result = field_spec_to_arrow(spec.fields[0])
        assert result.nullable is True
        assert isinstance(result.type, pa.StructType)

    def test_list_of_models(self) -> None:
        class Item(BaseModel):
            name: str

        class Container(BaseModel):
            items: list[Item]

        spec = extract_model(Container)
        result = type_info_to_arrow(spec.fields[0].type_info)
        assert isinstance(result, pa.ListType)
        assert isinstance(result.value_type, pa.StructType)


class TestArrowUnionMerging:
    """Discriminated union variants merge into a single struct."""

    def test_merges_shared_and_variant_fields(self) -> None:
        class A(BaseModel):
            type: Literal["a"] = "a"
            shared: str
            a_only: int32

        class B(BaseModel):
            type: Literal["b"] = "b"
            shared: str
            b_only: float64

        result = merge_model_variants([A, B])
        assert isinstance(result, pa.StructType)

        assert result.field("type").type == pa.utf8()
        assert result.field("shared").type == pa.utf8()

        a_idx = result.get_field_index("a_only")
        b_idx = result.get_field_index("b_only")
        assert a_idx >= 0
        assert b_idx >= 0
        assert result.field(a_idx).nullable is True
        assert result.field(b_idx).nullable is True

    @pytest.mark.parametrize(
        ("type_a", "type_b", "expected"),
        [
            (int32, int64, pa.int64()),
            (int64, uint8, pa.int64()),
            (int32, float64, pa.float64()),
        ],
        ids=["wider_int", "signed_unsigned", "int_float"],
    )
    def test_type_promotion(
        self, type_a: type, type_b: type, expected: pa.DataType
    ) -> None:
        A = type("A", (BaseModel,), {"__annotations__": {"val": type_a}})
        B = type("B", (BaseModel,), {"__annotations__": {"val": type_b}})
        result = merge_model_variants([A, B])
        assert result.field("val").type == expected


class TestFieldMetadata:
    """Field descriptions embed as Arrow field metadata."""

    def test_description_becomes_metadata(self) -> None:
        result = _arrow_field_for(str, description="The display name")
        assert result.metadata == {b"description": b"The display name"}

    def test_no_description_means_no_metadata(self) -> None:
        result = _arrow_field_for(str)
        assert result.metadata is None

    def test_nested_struct_fields_carry_metadata(self) -> None:
        class Inner(BaseModel):
            val: str = Field(description="Inner value")

        class Outer(BaseModel):
            nested: Inner

        spec = extract_model(Outer)
        result = field_spec_to_arrow(spec.fields[0])
        inner_field = result.type.field("val")
        assert inner_field.metadata == {b"description": b"Inner value"}

    def test_description_in_schema_fields(self) -> None:
        class M(BaseModel):
            id: str = Field(description="Unique identifier")
            count: int32

        spec = extract_model(M)
        schema = model_spec_to_arrow_schema(spec)
        assert schema.field("id").metadata == {b"description": b"Unique identifier"}
        assert schema.field("count").metadata is None

    def test_merge_preserves_first_metadata(self) -> None:
        class A(BaseModel):
            name: str = Field(description="The name")

        class B(BaseModel):
            name: str

        result = merge_model_variants([A, B])
        assert result.field("name").metadata == {b"description": b"The name"}


class TestUnionSpecToArrowSchema:
    """UnionSpec converts to pa.Schema by merging member variants."""

    def test_merges_members_into_schema(self, union_spec: UnionSpec) -> None:
        result = union_spec_to_arrow_schema(union_spec)

        assert isinstance(result, pa.Schema)
        assert result.field("type").type == pa.utf8()
        assert result.field("shared").type == pa.utf8()
        assert result.field("a_only").nullable is True
        assert result.field("b_only").nullable is True

    def test_schema_metadata(self, union_spec: UnionSpec) -> None:
        union_spec.entry_point = "overture.schema.test:TestUnion"
        result = union_spec_to_arrow_schema(union_spec, version="2.0.0")

        assert result.metadata == {
            b"overture-schema.version": b"2.0.0",
            b"model": b"overture.schema.test:TestUnion",
        }


class TestArrowRealModels:
    """Integration tests with real Overture models."""

    def test_building_schema(self, building_spec: ModelSpec) -> None:
        result = model_spec_to_arrow_schema(building_spec)
        assert isinstance(result, pa.Schema)

        assert result.field("id").nullable is False
        assert result.field("id").type == pa.utf8()
        assert result.field("geometry").type == pa.binary()
        assert result.field("geometry").nullable is False

        assert result.field("height").nullable is True

        bbox_type = result.field("bbox").type
        assert isinstance(bbox_type, pa.StructType)
        assert bbox_type.field("xmin").type == pa.float64()

    def test_building_schema_metadata(self, building_spec: ModelSpec) -> None:
        building_spec.entry_point = "overture.schema.buildings:Building"
        result = model_spec_to_arrow_schema(building_spec, version="1.0.0")
        assert result.metadata == {
            b"overture-schema.version": b"1.0.0",
            b"model": b"overture.schema.buildings:Building",
        }

    def test_all_models_no_crash(self, all_discovered_models: dict) -> None:
        """All discovered models convert to Arrow schemas without errors."""
        for model_class in filter_model_classes(all_discovered_models):
            try:
                spec = extract_model(model_class)
            except UnsupportedUnionError:
                continue
            result = model_spec_to_arrow_schema(spec)
            assert isinstance(result, pa.Schema)
            assert len(result) > 0

    def test_all_union_aliases_no_crash(self, all_discovered_models: dict) -> None:
        """All discovered union aliases convert to Arrow schemas without errors."""
        from overture.schema.codegen.layout.module_layout import entry_point_class

        for key, entry in all_discovered_models.items():
            if not is_union_alias(entry):
                continue
            spec = extract_union(
                entry_point_class(key.entry_point),
                entry,
                entry_point=key.entry_point,
            )
            result = union_spec_to_arrow_schema(spec)
            assert isinstance(result, pa.Schema)
            assert len(result) > 0

    def test_division_hierarchies_nested_list(self, division_class: type) -> None:
        """Division.hierarchies produces list<list<struct<...>>>."""
        spec = extract_model(division_class)
        schema = model_spec_to_arrow_schema(spec)
        hierarchies_type = schema.field("hierarchies").type

        assert isinstance(hierarchies_type, pa.ListType)
        inner_list = hierarchies_type.value_type
        assert isinstance(inner_list, pa.ListType)
        assert isinstance(inner_list.value_type, pa.StructType)
        assert inner_list.value_type.get_field_index("division_id") >= 0
        assert inner_list.value_type.get_field_index("subtype") >= 0
        assert inner_list.value_type.get_field_index("name") >= 0
