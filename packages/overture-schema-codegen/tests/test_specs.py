"""Tests for spec data structures and predicates."""

from typing import Annotated

import pytest
from codegen_test_support import (
    STR_TYPE,
    InstrumentFamily,
    SimpleModel,
    make_union_spec,
)
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.extraction.specs import (
    AnnotatedField,
    EnumSpec,
    FeatureSpec,
    FieldSpec,
    ModelSpec,
    NewTypeSpec,
    TypeIdentity,
    is_union_alias,
)
from overture.schema.codegen.extraction.type_analyzer import TypeInfo, TypeKind
from pydantic import BaseModel, Field


class TestFeatureSpecProtocol:
    """Tests for FeatureSpec protocol compliance."""

    def test_model_spec_satisfies_feature_spec(self) -> None:
        """ModelSpec satisfies the FeatureSpec protocol."""

        class Simple(BaseModel):
            name: str

        spec = extract_model(Simple)
        # Protocol compliance check
        assert isinstance(spec, FeatureSpec)
        # Verify protocol attributes
        assert spec.name == "Simple"
        assert isinstance(spec.fields, list)
        assert spec.source_type is Simple


class TestFieldSpec:
    """Tests for FieldSpec dataclass."""

    def test_fieldspec_stores_basic_attributes(self) -> None:
        """FieldSpec should store name, type_info, description, is_required."""
        field_spec = FieldSpec(
            name="test_field",
            type_info=STR_TYPE,
            description="A test field",
            is_required=True,
        )

        assert field_spec.name == "test_field"
        assert field_spec.type_info == STR_TYPE
        assert field_spec.description == "A test field"
        assert field_spec.is_required is True

    def test_fieldspec_optional_field(self) -> None:
        """FieldSpec should handle optional fields."""
        optional_str = TypeInfo(
            base_type="str", kind=TypeKind.PRIMITIVE, is_optional=True
        )

        field_spec = FieldSpec(
            name="optional_field",
            type_info=optional_str,
            description=None,
            is_required=False,
        )

        assert field_spec.is_required is False
        assert field_spec.description is None


class TestModelSpec:
    """Tests for ModelSpec dataclass."""

    def test_modelspec_stores_basic_attributes(self) -> None:
        """ModelSpec should store name, description, fields."""
        field = FieldSpec(
            name="id",
            type_info=STR_TYPE,
            description="Unique identifier",
            is_required=True,
        )

        model_spec = ModelSpec(
            name="TestModel",
            description="A test model",
            fields=[field],
        )

        assert model_spec.name == "TestModel"
        assert model_spec.description == "A test model"
        assert len(model_spec.fields) == 1
        assert model_spec.fields[0].name == "id"

    def test_entry_point_defaults_to_none(self) -> None:
        spec = ModelSpec(name="M", description=None)
        assert spec.entry_point is None


class TestAnnotatedField:
    """Tests for AnnotatedField wrapper."""

    def test_stores_field_and_variant_sources(self) -> None:
        """AnnotatedField pairs a FieldSpec with variant provenance."""
        fs = FieldSpec(name="x", type_info=STR_TYPE, description=None, is_required=True)
        af = AnnotatedField(field_spec=fs, variant_sources=("RoadSegment",))
        assert af.field_spec is fs
        assert af.variant_sources == ("RoadSegment",)

    def test_none_variant_sources_means_shared(self) -> None:
        """variant_sources=None indicates a shared field."""
        fs = FieldSpec(name="x", type_info=STR_TYPE, description=None, is_required=True)
        af = AnnotatedField(field_spec=fs, variant_sources=None)
        assert af.variant_sources is None


class TestFieldSpecModelTree:
    """Tests for FieldSpec model and starts_cycle fields."""

    def test_model_defaults_to_none(self) -> None:
        field_spec = FieldSpec(
            name="test", type_info=STR_TYPE, description=None, is_required=True
        )
        assert field_spec.model is None

    def test_starts_cycle_defaults_to_false(self) -> None:
        field_spec = FieldSpec(
            name="test", type_info=STR_TYPE, description=None, is_required=True
        )
        assert field_spec.starts_cycle is False

    def test_model_can_hold_model_spec(self) -> None:
        type_info = TypeInfo(base_type="Address", kind=TypeKind.MODEL)
        sub = ModelSpec(name="Address", description=None)
        field_spec = FieldSpec(
            name="address",
            type_info=type_info,
            description=None,
            is_required=True,
            model=sub,
        )
        assert field_spec.model is sub

    def test_starts_cycle_can_be_set(self) -> None:
        type_info = TypeInfo(base_type="Node", kind=TypeKind.MODEL)
        sub = ModelSpec(name="Node", description=None)
        field_spec = FieldSpec(
            name="parent",
            type_info=type_info,
            description=None,
            is_required=False,
            model=sub,
            starts_cycle=True,
        )
        assert field_spec.starts_cycle is True
        assert field_spec.model is sub

    def test_starts_cycle_without_model_is_nonsensical(self) -> None:
        """starts_cycle=True with model=None is expressible but invalid.

        expand_model_tree never produces this combination -- starts_cycle
        is only set when model points to the cycle-causing ModelSpec.
        Document the invariant so violations stand out.
        """
        type_info = TypeInfo(base_type="Node", kind=TypeKind.MODEL)
        field_spec = FieldSpec(
            name="parent",
            type_info=type_info,
            description=None,
            is_required=False,
            starts_cycle=True,
        )
        # Expressible but meaningless: cycle to nowhere
        assert field_spec.starts_cycle is True
        assert field_spec.model is None


class TestIsUnionAlias:
    """Tests for is_union_alias predicate."""

    def test_annotated_union_of_models_returns_true(self) -> None:
        """Annotated[Union of BaseModels] is a union alias."""

        class A(BaseModel):
            x: int

        class B(BaseModel):
            y: str

        union_type = Annotated[A | B, Field(description="test")]
        assert is_union_alias(union_type) is True

    def test_model_class_returns_false(self) -> None:
        """A concrete BaseModel class is not a union alias."""

        class A(BaseModel):
            x: int

        assert is_union_alias(A) is False

    def test_plain_string_returns_false(self) -> None:
        """A plain string is not a union alias."""
        assert is_union_alias("not a type") is False

    def test_non_model_union_returns_false(self) -> None:
        """A union of non-model types is not a union alias."""
        assert is_union_alias(str | int) is False


class TestUnionSpec:
    """Tests for UnionSpec data structure."""

    def test_fields_property_returns_plain_field_specs(self) -> None:
        """UnionSpec.fields property returns list[FieldSpec] from annotated_fields."""
        fs1 = FieldSpec(
            name="a", type_info=STR_TYPE, description=None, is_required=True
        )
        fs2 = FieldSpec(
            name="b", type_info=STR_TYPE, description=None, is_required=False
        )
        spec = make_union_spec(
            annotated_fields=[
                AnnotatedField(field_spec=fs1, variant_sources=None),
                AnnotatedField(field_spec=fs2, variant_sources=("X",)),
            ],
        )
        assert spec.fields == [fs1, fs2]


class TestTypeIdentity:
    def test_frozen(self) -> None:
        ti = TypeIdentity(obj=int, name="int")
        with pytest.raises(AttributeError):
            ti.obj = str  # type: ignore[misc]

    def test_same_obj_equal(self) -> None:
        a = TypeIdentity(obj=int, name="int")
        b = TypeIdentity(obj=int, name="integer")
        assert a == b

    def test_same_obj_same_hash(self) -> None:
        a = TypeIdentity(obj=int, name="int")
        b = TypeIdentity(obj=int, name="integer")
        assert hash(a) == hash(b)

    def test_different_obj_not_equal(self) -> None:
        a = TypeIdentity(obj=int, name="int")
        b = TypeIdentity(obj=str, name="int")
        assert a != b

    def test_works_as_dict_key(self) -> None:
        ti = TypeIdentity(obj=int, name="int")
        d = {ti: "value"}
        assert d[TypeIdentity(obj=int, name="different")] == "value"

    def test_not_equal_to_non_identity(self) -> None:
        ti = TypeIdentity(obj=int, name="int")
        non_identity_type: object = int
        non_identity_str: object = "int"
        assert ti != non_identity_type
        assert ti != non_identity_str


class TestSpecIdentity:
    def test_model_spec_identity(self) -> None:
        spec = ModelSpec(name="Foo", description=None, source_type=SimpleModel)
        ident = spec.identity
        assert isinstance(ident, TypeIdentity)
        assert ident.obj is SimpleModel
        assert ident.name == "Foo"

    def test_enum_spec_identity(self) -> None:
        spec = EnumSpec(name="Color", description=None, source_type=InstrumentFamily)
        ident = spec.identity
        assert ident.obj is InstrumentFamily
        assert ident.name == "Color"

    def test_newtype_spec_identity(self) -> None:
        from overture.schema.system.primitive import int32

        spec = NewTypeSpec(
            name="int32", description=None, type_info=STR_TYPE, source_type=int32
        )
        ident = spec.identity
        assert ident.obj is int32
        assert ident.name == "int32"

    def test_union_spec_identity(self) -> None:
        sentinel = object()
        spec = make_union_spec("TestUnion", source_annotation=sentinel)
        ident = spec.identity
        assert ident.obj is sentinel
        assert ident.name == "TestUnion"

    def test_model_spec_satisfies_feature_protocol_with_identity(self) -> None:
        spec = ModelSpec(name="Foo", description=None, source_type=SimpleModel)
        feature: FeatureSpec = spec
        assert feature.identity.obj is SimpleModel
