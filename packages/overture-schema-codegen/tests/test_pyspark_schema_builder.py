"""Tests for schema_builder."""

from enum import Enum

import pytest
from codegen_test_support import spec_for_model
from overture.schema.codegen.extraction.field import Primitive
from overture.schema.codegen.extraction.specs import (
    AnnotatedField,
    FieldSpec,
    UnionSpec,
)
from overture.schema.codegen.pyspark.schema_builder import SchemaField, build_schema
from overture.schema.divisions import DivisionArea
from pydantic import BaseModel, Field


class SimpleModel(BaseModel):
    name: str
    count: int = Field(ge=0)


class TestPrimitiveFields:
    @pytest.fixture
    def fields(self) -> list[SchemaField]:
        return build_schema(spec_for_model(SimpleModel))

    def test_string_field_maps_to_string_type(self, fields: list[SchemaField]) -> None:
        name_field = next(f for f in fields if f.name == "name")
        assert name_field.type_expr == "StringType()"

    def test_int_field_maps_to_long_type(self, fields: list[SchemaField]) -> None:
        count_field = next(f for f in fields if f.name == "count")
        assert count_field.type_expr == "LongType()"


class NestedModel(BaseModel):
    value: str
    count: int


class ContainerModel(BaseModel):
    item: NestedModel | None = None


class TestNestedModel:
    @pytest.fixture
    def fields(self) -> list[SchemaField]:
        return build_schema(spec_for_model(ContainerModel))

    def test_nested_model_emits_struct_type(self, fields: list[SchemaField]) -> None:
        item_field = next(f for f in fields if f.name == "item")
        assert item_field.type_expr.startswith("StructType([")

    def test_nested_struct_contains_subfields(self, fields: list[SchemaField]) -> None:
        item_field = next(f for f in fields if f.name == "item")
        assert 'StructField("value"' in item_field.type_expr
        assert 'StructField("count"' in item_field.type_expr


class ListModel(BaseModel):
    tags: list[str]
    counts: list[int] | None = None


class TestListFields:
    @pytest.fixture
    def fields(self) -> list[SchemaField]:
        return build_schema(spec_for_model(ListModel))

    def test_list_str_maps_to_array_string(self, fields: list[SchemaField]) -> None:
        tags_field = next(f for f in fields if f.name == "tags")
        assert tags_field.type_expr == "ArrayType(StringType(), True)"

    def test_optional_list_int_maps_to_array_long(
        self, fields: list[SchemaField]
    ) -> None:
        counts_field = next(f for f in fields if f.name == "counts")
        assert counts_field.type_expr == "ArrayType(LongType(), True)"


class DictModel(BaseModel):
    labels: dict[str, str] | None = None


class TestDictFields:
    @pytest.fixture
    def fields(self) -> list[SchemaField]:
        return build_schema(spec_for_model(DictModel))

    def test_dict_str_str_maps_to_map_type(self, fields: list[SchemaField]) -> None:
        labels_field = next(f for f in fields if f.name == "labels")
        assert labels_field.type_expr == "MapType(StringType(), StringType(), True)"


class TestDivisionAreaSchema:
    @pytest.fixture(scope="class")
    def fields(self) -> list[SchemaField]:
        return build_schema(spec_for_model(DivisionArea))

    def test_id_field_is_string_type(self, fields: list[SchemaField]) -> None:
        id_field = next(f for f in fields if f.name == "id")
        assert id_field.type_expr == "StringType()"

    def test_geometry_field_is_binary_type(self, fields: list[SchemaField]) -> None:
        geom_field = next(f for f in fields if f.name == "geometry")
        assert geom_field.type_expr == "BinaryType()"

    def test_bbox_emits_shared_struct_ref(self, fields: list[SchemaField]) -> None:
        bbox_field = next(f for f in fields if f.name == "bbox")
        assert bbox_field.type_expr == "BBOX_STRUCT"

    def test_version_is_integer_type(self, fields: list[SchemaField]) -> None:
        ver_field = next(f for f in fields if f.name == "version")
        assert ver_field.type_expr == "IntegerType()"

    def test_is_land_is_boolean_type(self, fields: list[SchemaField]) -> None:
        field = next(f for f in fields if f.name == "is_land")
        assert field.type_expr == "BooleanType()"

    def test_country_is_string_type(self, fields: list[SchemaField]) -> None:
        field = next(f for f in fields if f.name == "country")
        assert field.type_expr == "StringType()"

    def test_admin_level_is_integer_type(self, fields: list[SchemaField]) -> None:
        field = next(f for f in fields if f.name == "admin_level")
        assert field.type_expr == "IntegerType()"

    def test_subtype_enum_is_string_type(self, fields: list[SchemaField]) -> None:
        field = next(f for f in fields if f.name == "subtype")
        assert field.type_expr == "StringType()"

    def test_theme_appears_once_at_model_position(
        self, fields: list[SchemaField]
    ) -> None:
        theme_fields = [f for f in fields if f.name == "theme"]
        assert len(theme_fields) == 1

    def test_theme_and_type_present(self, fields: list[SchemaField]) -> None:
        names = [f.name for f in fields]
        assert "theme" in names
        assert "type" in names


class _ColorA(Enum):
    RED = "red"
    GREEN = "green"


class _ColorB(Enum):
    BLUE = "blue"
    YELLOW = "yellow"


class _VariantA(BaseModel):
    pass


class _VariantB(BaseModel):
    pass


class TestUnionSchemaDeduplicate:
    """build_schema deduplicates same-name fields from different union variants."""

    @pytest.fixture
    def fields(self) -> list[SchemaField]:
        af_shared = AnnotatedField(
            field_spec=FieldSpec(
                name="id",
                shape=Primitive(base_type="str"),
                description=None,
                is_required=True,
            ),
            variant_sources=None,
        )
        af_color_a = AnnotatedField(
            field_spec=FieldSpec(
                name="color",
                shape=Primitive(base_type="ColorA", source_type=_ColorA),
                description=None,
                is_required=True,
            ),
            variant_sources=(_VariantA,),
        )
        af_color_b = AnnotatedField(
            field_spec=FieldSpec(
                name="color",
                shape=Primitive(base_type="ColorB", source_type=_ColorB),
                description=None,
                is_required=True,
            ),
            variant_sources=(_VariantB,),
        )
        spec = UnionSpec(
            name="TestUnion",
            description=None,
            annotated_fields=[af_shared, af_color_a, af_color_b],
            members=[],
            discriminator_field=None,
            discriminator_mapping=None,
            source_annotation=object(),
            common_base=BaseModel,
        )
        return build_schema(spec)

    def test_one_schema_field_per_name(self, fields: list[SchemaField]) -> None:
        color_fields = [f for f in fields if f.name == "color"]
        assert len(color_fields) == 1

    def test_color_field_is_string_type(self, fields: list[SchemaField]) -> None:
        color_field = next(f for f in fields if f.name == "color")
        assert color_field.type_expr == "StringType()"
