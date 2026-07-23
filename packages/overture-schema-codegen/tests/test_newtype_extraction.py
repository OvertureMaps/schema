"""Tests for NewType extraction."""

from typing import Annotated, NewType

from annotated_types import MaxLen
from codegen_test_support import STR_TYPE, TollChargesByVehicleType
from overture.schema.codegen.extraction.field import ArrayOf, MapOf, Primitive
from overture.schema.codegen.extraction.field_walk import (
    all_constraints,
    terminal_scalar,
)
from overture.schema.codegen.extraction.length_constraints import ArrayMaxLen
from overture.schema.codegen.extraction.newtype_extraction import (
    extract_newtype,
    extract_rootmodel_alias,
)
from overture.schema.codegen.extraction.specs import NewTypeSpec
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.ref import Id
from overture.schema.system.string import HexColor
from pydantic import BaseModel, Field, RootModel


class TestExtractNewType:
    """Tests for extract_newtype function."""

    def test_extract_hex_color(self) -> None:
        """Should extract HexColor NewType specification."""
        spec = extract_newtype(HexColor)

        assert spec.name == "HexColor"
        # Outermost NewTypeShape stripped; shape is the underlying scalar.
        assert terminal_scalar(spec.shape) is not None

    def test_extract_id(self) -> None:
        """Should extract Id NewType with nested chain."""
        spec = extract_newtype(Id)

        assert spec.name == "Id"
        # Id wraps NoWhitespaceString, which is a registered semantic newtype
        # resolving to a Scalar. After stripping "Id", shape is Scalar with
        # base_type "NoWhitespaceString".
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


class TestExtractRootModelAlias:
    """A `RootModel` documents as a named alias over its bare root type.

    A RootModel serializes as its bare root value, so for documentation it
    is a named alias -- like a NewType -- and extracts into the same
    `NewTypeSpec`. `analyze_type` already returns the bare root shape, so no
    wrapper is stripped.
    """

    def test_map_root_extracts_to_mapof_shape(self) -> None:
        spec = extract_rootmodel_alias(TollChargesByVehicleType)

        assert isinstance(spec, NewTypeSpec)
        assert spec.name == "TollChargesByVehicleType"
        assert isinstance(spec.shape, MapOf)
        assert spec.source_type is TollChargesByVehicleType

    def test_docstring_becomes_description(self) -> None:
        spec = extract_rootmodel_alias(TollChargesByVehicleType)
        assert spec.description is not None
        assert "map-rooted" in spec.description

    def test_root_field_description_used_without_docstring(self) -> None:
        class Slug(RootModel[Annotated[str, Field(description="A URL slug")]]):
            pass

        spec = extract_rootmodel_alias(Slug)
        assert spec.description == "A URL slug"

    def test_constrained_root_keeps_constraints_on_shape(self) -> None:
        class Tags(RootModel[Annotated[list[str], MaxLen(3)]]):
            pass

        spec = extract_rootmodel_alias(Tags)
        assert isinstance(spec.shape, ArrayOf)
        assert ArrayMaxLen in {
            type(cs.constraint) for cs in all_constraints(spec.shape)
        }


class TestNewTypeSpecSourceType:
    """Tests for source_type on NewTypeSpec."""

    def test_newtype_spec_source_type_defaults_to_none(self) -> None:
        spec = NewTypeSpec(name="Test", description=None, shape=STR_TYPE)
        assert spec.source_type is None

    def test_extract_newtype_sets_source_type(self) -> None:
        spec = extract_newtype(HexColor)
        assert spec.source_type is HexColor
