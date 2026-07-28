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
    FieldSpec,
    ModelSpec,
    NewTypeSpec,
    RecordSpec,
    TypeIdentity,
    is_union_alias,
)
from overture.schema.system.numeric import int32
from pydantic import BaseModel, Field


class TestModelSpec:
    def test_record_spec_is_model_spec(self) -> None:
        class Simple(BaseModel):
            name: str

        spec: ModelSpec = extract_model(Simple)
        assert isinstance(spec, RecordSpec)
        assert spec.name == "Simple"
        assert isinstance(spec.fields, list)
        assert spec.source_type is Simple


class TestFieldSpec:
    def test_carries_shape_and_optional_flag(self) -> None:
        fs = FieldSpec(
            name="optional_field",
            shape=STR_TYPE,
            description=None,
            is_required=False,
            is_optional=True,
        )
        assert fs.name == "optional_field"
        assert fs.shape is STR_TYPE
        assert fs.is_required is False
        assert fs.is_optional is True


class TestAnnotatedField:
    def test_stores_field_and_variant_sources(self) -> None:
        class RoadSegment(BaseModel):
            pass

        fs = FieldSpec(name="x", shape=STR_TYPE)
        af = AnnotatedField(field_spec=fs, variant_sources=(RoadSegment,))
        assert af.field_spec is fs
        assert af.variant_sources == (RoadSegment,)

    def test_none_variant_sources_means_shared(self) -> None:
        fs = FieldSpec(name="x", shape=STR_TYPE)
        af = AnnotatedField(field_spec=fs, variant_sources=None)
        assert af.variant_sources is None


class TestIsUnionAlias:
    def test_annotated_union_of_models_returns_true(self) -> None:
        class A(BaseModel):
            x: int

        class B(BaseModel):
            y: str

        assert is_union_alias(Annotated[A | B, Field(description="test")]) is True

    def test_model_class_returns_false(self) -> None:
        class A(BaseModel):
            x: int

        assert is_union_alias(A) is False

    def test_plain_string_returns_false(self) -> None:
        assert is_union_alias("not a type") is False

    def test_non_model_union_returns_false(self) -> None:
        assert is_union_alias(str | int) is False


class TestUnionSpec:
    def test_fields_property_returns_plain_field_specs(self) -> None:
        class X(BaseModel):
            pass

        fs1 = FieldSpec(name="a", shape=STR_TYPE)
        fs2 = FieldSpec(name="b", shape=STR_TYPE, is_required=False)
        spec = make_union_spec(
            annotated_fields=[
                AnnotatedField(field_spec=fs1, variant_sources=None),
                AnnotatedField(field_spec=fs2, variant_sources=(X,)),
            ],
        )
        assert spec.fields == [fs1, fs2]


class TestTypeIdentity:
    def test_frozen(self) -> None:
        ti = TypeIdentity(obj=int, name="int")
        with pytest.raises(AttributeError):
            ti.obj = str  # type: ignore[misc]

    def test_equality_by_obj_identity(self) -> None:
        a = TypeIdentity(obj=int, name="int")
        b = TypeIdentity(obj=int, name="integer")
        c = TypeIdentity(obj=str, name="int")
        assert a == b
        assert hash(a) == hash(b)
        assert a != c

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
    def test_record_spec_identity(self) -> None:
        spec = RecordSpec(name="Foo", description=None, source_type=SimpleModel)
        assert spec.identity.obj is SimpleModel
        assert spec.identity.name == "Foo"

    def test_enum_spec_identity(self) -> None:
        spec = EnumSpec(name="Color", description=None, source_type=InstrumentFamily)
        assert spec.identity.obj is InstrumentFamily

    def test_newtype_spec_identity(self) -> None:
        spec = NewTypeSpec(
            name="int32", description=None, shape=STR_TYPE, source_type=int32
        )
        assert spec.identity.obj is int32

    def test_union_spec_identity(self) -> None:
        sentinel = object()
        spec = make_union_spec("TestUnion", source_annotation=sentinel)
        assert spec.identity.obj is sentinel
        assert spec.identity.name == "TestUnion"
