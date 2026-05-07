"""Tests for NewType extraction."""

from typing import Annotated, NewType

from codegen_test_support import STR_TYPE
from overture.schema.codegen.extraction.field import ArrayOf
from overture.schema.codegen.extraction.newtype_extraction import extract_newtype
from overture.schema.codegen.extraction.specs import NewTypeSpec
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.ref import Id
from overture.schema.system.string import HexColor
from pydantic import BaseModel, Field


class TestExtractNewType:
    """Tests for extract_newtype function."""

    def test_extract_hex_color(self) -> None:
        """Should extract HexColor NewType specification."""
        spec = extract_newtype(HexColor)

        assert spec.name == "HexColor"
        # Outermost NewTypeShape stripped; shape is the underlying scalar.
        from overture.schema.codegen.extraction.field_walk import terminal_scalar

        assert terminal_scalar(spec.shape) is not None

    def test_extract_id(self) -> None:
        """Should extract Id NewType with nested chain."""
        spec = extract_newtype(Id)

        assert spec.name == "Id"
        # Id wraps NoWhitespaceString, which is a registered semantic newtype
        # resolving to a Scalar. After stripping "Id", shape is Scalar with
        # base_type "NoWhitespaceString".
        from overture.schema.codegen.extraction.field import Primitive

        assert isinstance(spec.shape, Primitive)
        assert spec.shape.base_type == "NoWhitespaceString"

    def test_extract_newtype_wrapping_list(self) -> None:
        """Should extract a list-wrapping NewType."""

        class Item(BaseModel):
            value: str

        TestSources = NewType(
            "TestSources", Annotated[list[Item], UniqueItemsConstraint()]
        )
        spec = extract_newtype(TestSources)

        assert spec.name == "TestSources"
        # After stripping the outer NewTypeShape("TestSources"), shape is ArrayOf.
        assert isinstance(spec.shape, ArrayOf)

    def test_extract_newtype_without_doc_uses_field_description(self) -> None:
        """NewType with Field(description=...) but no __doc__ uses Field description."""
        TestType = NewType(
            "TestType",
            Annotated[str, Field(description="A test type description")],
        )
        spec = extract_newtype(TestType)
        assert spec.description == "A test type description"

    def test_extract_newtype_with_doc_ignores_field_description(self) -> None:
        """NewType with custom __doc__ uses docstring, not Field description."""
        spec = extract_newtype(HexColor)
        # HexColor has both __doc__ and Field(description=...).
        # __doc__ should win because is_custom_docstring returns True.
        assert spec.description is not None
        assert "example" in spec.description.lower() or "#" in spec.description


class TestNewTypeSpecSourceType:
    """Tests for source_type on NewTypeSpec."""

    def test_newtype_spec_source_type_defaults_to_none(self) -> None:
        spec = NewTypeSpec(name="Test", description=None, shape=STR_TYPE)
        assert spec.source_type is None

    def test_extract_newtype_sets_source_type(self) -> None:
        spec = extract_newtype(HexColor)
        assert spec.source_type is HexColor
