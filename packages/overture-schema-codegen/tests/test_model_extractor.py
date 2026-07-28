"""Tests for model extraction."""

from typing import Annotated, Literal

from codegen_test_support import (
    FeatureBase,
    FeatureWithAddress,
    Instrument,
    SourceItem,
    TreeNode,
    Venue,
    assert_literal_field,
    find_field,
)
from overture.schema.codegen.extraction.field import ModelRef, Primitive
from overture.schema.codegen.extraction.field_walk import (
    all_constraints,
    has_array_layer,
    terminal_of,
)
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.geometric import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.model_constraint import (
    FieldEqCondition,
    FieldGroupConstraint,
    require_any_of,
    require_if,
)
from overture.schema.system.string import HexColor
from pydantic import BaseModel, Field


class TestModelConstraints:
    """Model-level constraint extraction."""

    def test_unconstrained_model_has_empty_constraints(self) -> None:
        """Models without decorators produce an empty constraints tuple."""

        class Plain(BaseModel):
            name: str

        spec = extract_model(Plain)

        assert spec.constraints == ()

    def test_extracts_require_any_of(self) -> None:
        """Should extract @require_any_of from a decorated model."""
        spec = extract_model(Venue)

        assert len(spec.constraints) == 1
        (constraint,) = spec.constraints
        assert constraint.name == "@require_any_of"
        assert isinstance(constraint, FieldGroupConstraint)
        assert constraint.field_names == ("name", "description")

    def test_stacked_constraints_preserve_order(self) -> None:
        """Multiple decorators extracted in stacking order (inner-first)."""

        @require_if(["bar"], FieldEqCondition("baz", "x"))
        @require_any_of("foo", "bar")
        class Stacked(BaseModel):
            foo: str | None = None
            bar: str | None = None
            baz: str | None = None

        spec = extract_model(Stacked)

        assert len(spec.constraints) == 2
        assert spec.constraints[0].name == "@require_any_of"
        assert spec.constraints[1].name == "@require_if"


class TestExtractModelSimple:
    """Tests for extract_model with simple Pydantic models."""

    def test_extract_simple_model(self) -> None:
        """Should extract basic model information."""

        class SimpleModel(BaseModel):
            """A simple test model."""

            name: str

        result = extract_model(SimpleModel)

        assert result.name == "SimpleModel"
        assert result.description == "A simple test model."
        assert len(result.fields) == 1
        assert result.fields[0].name == "name"
        scalar = terminal_of(result.fields[0].shape)
        assert isinstance(scalar, Primitive)
        assert scalar.base_type == "str"
        assert result.fields[0].is_required is True

    def test_extract_model_does_not_set_entry_point(self) -> None:
        class M(BaseModel):
            x: int

        result = extract_model(M)
        assert result.entry_point is None

    def test_extract_model_with_optional_field(self) -> None:
        """Should handle optional fields correctly."""

        class ModelWithOptional(BaseModel):
            """Model with optional field."""

            name: str
            nickname: str | None = None

        result = extract_model(ModelWithOptional)

        assert len(result.fields) == 2

        name_field = find_field(result, "name")
        assert name_field.is_required is True

        nickname_field = find_field(result, "nickname")
        assert nickname_field.is_required is False
        assert nickname_field.is_optional is True

    def test_extract_model_with_field_description(self) -> None:
        """Should extract field descriptions from Field()."""

        class ModelWithDescription(BaseModel):
            """Model with field descriptions."""

            name: str = Field(description="The name of the entity")

        result = extract_model(ModelWithDescription)

        assert result.fields[0].description == "The name of the entity"

    def test_extract_model_with_list_field(self) -> None:
        """Should handle list fields correctly."""

        class ModelWithList(BaseModel):
            """Model with list field."""

            tags: list[str]

        result = extract_model(ModelWithList)

        tags_field = result.fields[0]
        assert tags_field.name == "tags"
        assert has_array_layer(tags_field.shape)
        scalar = terminal_of(tags_field.shape)
        assert isinstance(scalar, Primitive)
        assert scalar.base_type == "str"


class TestExtractModelWithThemeType:
    """Tests for extracting theme/type from Feature-like models."""

    def test_extract_theme_and_type_from_generic(self) -> None:
        """Should extract theme and type as Literal fields."""

        class Place(FeatureBase[Literal["places"], Literal["place"]]):
            """A place feature."""

            name: str

        result = extract_model(Place)
        assert_literal_field(result, "theme", "places")
        assert_literal_field(result, "type", "place")

    def test_extract_different_theme_type(self) -> None:
        """Should handle different theme/type values as Literal fields."""

        class Building(FeatureBase[Literal["buildings"], Literal["building"]]):
            """A building feature."""

            height: float | None = None

        result = extract_model(Building)
        assert_literal_field(result, "theme", "buildings")
        assert_literal_field(result, "type", "building")

    def test_non_feature_model_has_no_theme_type(self) -> None:
        """Regular models without Generic base should have no theme/type fields."""

        class RegularModel(BaseModel):
            """A regular model."""

            value: int

        result = extract_model(RegularModel)

        field_names = [f.name for f in result.fields]
        assert "theme" not in field_names
        assert "type" not in field_names


class TestExtractModelFieldAlias:
    """Tests for field alias handling in extract_model."""

    def test_field_with_alias_uses_alias_name(self) -> None:
        """Fields with alias should use alias as the field name, not Python attr name."""

        class ModelWithAlias(BaseModel):
            """Model with aliased field."""

            class_: str | None = Field(default=None, alias="class")

        result = extract_model(ModelWithAlias)

        # Should use alias 'class', not Python name 'class_'
        class_field = result.fields[0]
        assert class_field.name == "class"

    def test_field_without_alias_uses_python_name(self) -> None:
        """Fields without alias should use Python attribute name."""

        class ModelWithoutAlias(BaseModel):
            """Model without alias."""

            name: str

        result = extract_model(ModelWithoutAlias)

        assert result.fields[0].name == "name"


class TestExtractModelDocstring:
    """Tests for docstring extraction and cleaning."""

    def test_multiline_docstring_has_indentation_stripped(self) -> None:
        """Multi-line docstrings should have leading whitespace stripped.

        Docstrings defined in classes have leading whitespace on continuation
        lines. This should be stripped so they render as normal paragraphs
        in Markdown, not as code blocks.
        """

        class ModelWithMultilineDoc(BaseModel):
            """A model with multi-line docstring.

            This is a second paragraph that would have leading
            whitespace in the raw __doc__ attribute.
            """

            name: str

        result = extract_model(ModelWithMultilineDoc)

        # Description should NOT have leading whitespace on continuation lines
        assert result.description is not None
        assert "\n            " not in result.description
        # Should still have the content
        assert "second paragraph" in result.description


class TestFieldOrderingWithMixins:
    """Tests for field ordering when a model has multiple inheritance."""

    def test_mixin_fields_come_after_primary_chain_and_own(self) -> None:
        """Fields from mixin bases should appear after primary chain and own fields."""

        class PrimaryBase(BaseModel):
            base_field: str

        class MixinA(BaseModel):
            a_field: str

        class MixinB(BaseModel):
            b_field: str

        class Child(PrimaryBase, MixinA, MixinB):
            """A child model with mixins."""

            own_field: str

        result = extract_model(Child)
        field_names = [f.name for f in result.fields]

        assert field_names == ["base_field", "own_field", "a_field", "b_field"]

    def test_single_inheritance_order_unchanged(self) -> None:
        """Single-inheritance models should keep Pydantic's default order."""

        class Parent(BaseModel):
            parent_field: str

        class Child(Parent):
            """A child model."""

            child_field: str

        result = extract_model(Child)
        field_names = [f.name for f in result.fields]

        assert field_names == ["parent_field", "child_field"]

    def test_mixin_fields_in_declaration_order(self) -> None:
        """Mixin fields should appear in class declaration order, not reversed MRO."""

        class Primary(BaseModel):
            p: str

        class MixinFirst(BaseModel):
            first: str

        class MixinSecond(BaseModel):
            second: str

        class MixinThird(BaseModel):
            third: str

        class Model(Primary, MixinFirst, MixinSecond, MixinThird):
            """Model with three mixins."""

            own: str

        result = extract_model(Model)
        field_names = [f.name for f in result.fields]

        # Mixins in declaration order: First, Second, Third
        assert field_names == ["p", "own", "first", "second", "third"]

    def test_deep_primary_chain_before_mixins(self) -> None:
        """Fields from the entire primary chain should precede mixin fields."""

        class GrandParent(BaseModel):
            gp_field: str

        class Parent(GrandParent):
            p_field: str

        class Mixin(BaseModel):
            m_field: str

        class Child(Parent, Mixin):
            """Child with deep primary chain."""

            own_field: str

        result = extract_model(Child)
        field_names = [f.name for f in result.fields]

        assert field_names == ["gp_field", "p_field", "own_field", "m_field"]

    def test_recursive_mixin_reordering(self) -> None:
        """Mixins on primary-chain classes should also be reordered."""

        class CoreBase(BaseModel):
            core: str

        class ParentMixin(BaseModel):
            pm: str

        class Parent(CoreBase, ParentMixin):
            p: str

        class ChildMixin(BaseModel):
            cm: str

        class Child(Parent, ChildMixin):
            """Child where primary-chain parent has its own mixin."""

            own: str

        result = extract_model(Child)
        field_names = [f.name for f in result.fields]

        # CoreBase (Parent's primary) -> Parent own -> ParentMixin -> Child own -> ChildMixin
        assert field_names == ["core", "p", "pm", "own", "cm"]


class TestSubModelExpansion:
    """Sub-model resolution at extract_model time."""

    def test_model_without_sub_models_unchanged(self) -> None:
        """Fields without MODEL kind have no ModelRef in their shape."""

        class Simple(BaseModel):
            name: str
            count: int

        spec = extract_model(Simple)

        for f in spec.fields:
            assert not isinstance(terminal_of(f.shape), ModelRef)

    def test_nested_model_gets_expanded(self) -> None:
        """MODEL-kind fields resolve to a ModelRef in the shape."""
        spec = extract_model(FeatureWithAddress)

        addr_field = find_field(spec, "address")
        terminal = terminal_of(addr_field.shape)
        assert isinstance(terminal, ModelRef)
        assert terminal.model.name == "Address"
        assert terminal.starts_cycle is False

        # Sub-model fields should exist
        sub_names = [f.name for f in terminal.model.fields]
        assert "street" in sub_names
        assert "city" in sub_names

    def test_cycle_detected_and_marked(self) -> None:
        """Self-referential model gets starts_cycle=True on the ModelRef."""
        spec = extract_model(TreeNode)

        parent_field = find_field(spec, "parent")
        terminal = terminal_of(parent_field.shape)
        assert isinstance(terminal, ModelRef)
        assert terminal.model is spec  # Same object -- cycle
        assert terminal.starts_cycle is True

    def test_shared_reference_within_one_extraction(self) -> None:
        """Two fields referencing the same sub-model share the RecordSpec."""

        class Shared(BaseModel):
            value: str

        class Container(BaseModel):
            first: Shared
            second: Shared

        spec = extract_model(Container)
        first = find_field(spec, "first")
        second = find_field(spec, "second")

        first_ref = terminal_of(first.shape)
        second_ref = terminal_of(second.shape)
        assert isinstance(first_ref, ModelRef)
        assert isinstance(second_ref, ModelRef)
        # Within one extract_model call, the cache ensures the same
        # RecordSpec is reused for both references; neither is a cycle.
        assert first_ref.model is second_ref.model
        assert first_ref.starts_cycle is False
        assert second_ref.starts_cycle is False

    def test_list_of_model_gets_expanded(self) -> None:
        """list[Model] fields also get their model populated via ModelRef."""

        class HasList(BaseModel):
            items: list[SourceItem]

        spec = extract_model(HasList)

        items_field = find_field(spec, "items")
        terminal = terminal_of(items_field.shape)
        assert isinstance(terminal, ModelRef)
        assert terminal.model.name == "SourceItem"


class TestFieldInfoMetadataConstraints:
    """Constraints from `field_info.metadata` attach to the field's shape.

    Pydantic strips the Annotated wrapper from some fields and moves the
    metadata to `field_info.metadata`. `extract_model` attaches these
    constraints to the appropriate `FieldShape` layer so they aren't
    silently dropped.
    """

    def test_geometry_type_constraint_extracted(self) -> None:
        """GeometryTypeConstraint on geometry field should appear in constraints."""
        spec = extract_model(Venue)
        geometry_field = find_field(spec, "geometry")

        constraint_types = [
            type(cs.constraint) for cs in all_constraints(geometry_field.shape)
        ]
        assert GeometryTypeConstraint in constraint_types

    def test_geometry_type_constraint_has_null_source(self) -> None:
        """Constraints from field_info.metadata have source_ref=None (not from a NewType)."""
        spec = extract_model(Venue)
        geometry_field = find_field(spec, "geometry")

        geo_constraints = [
            cs
            for cs in all_constraints(geometry_field.shape)
            if isinstance(cs.constraint, GeometryTypeConstraint)
        ]
        assert len(geo_constraints) == 1
        assert geo_constraints[0].source_ref is None

    def test_metadata_constraints_not_duplicated(self) -> None:
        """Fields where Pydantic preserves Annotated don't get duplicate constraints.

        When field_info.metadata is empty (Pydantic kept the Annotated wrapper),
        no extra constraints are added.
        """
        spec = extract_model(Instrument)
        tags_field = find_field(spec, "tags")

        unique_constraints = [
            cs
            for cs in all_constraints(tags_field.shape)
            if isinstance(cs.constraint, UniqueItemsConstraint)
        ]
        assert len(unique_constraints) == 1

    def test_standalone_annotated_field_extracts_metadata(self) -> None:
        """Direct Annotated[Type, constraint] fields (non-optional, non-union)
        get their constraints from field_info.metadata."""

        class Model(BaseModel):
            geo: Annotated[
                Geometry,
                GeometryTypeConstraint(GeometryType.POINT),
            ]

        spec = extract_model(Model)
        geo_field = find_field(spec, "geo")

        constraint_types = [
            type(cs.constraint) for cs in all_constraints(geo_field.shape)
        ]
        assert GeometryTypeConstraint in constraint_types


class TestFieldDescriptionFallback:
    """Tests for field description fallback from NewType Field metadata."""

    def test_field_inherits_newtype_description(self) -> None:
        """Field with no explicit description gets NewType's Field description."""

        class TestModel(BaseModel):
            color: HexColor

        spec = extract_model(TestModel)
        field = find_field(spec, "color")
        assert field.description is not None
        assert "color" in field.description.lower()

    def test_explicit_description_not_overridden(self) -> None:
        """Field with explicit description keeps its own, ignores NewType's."""

        class TestModel(BaseModel):
            color: HexColor = Field(description="Custom color description")

        spec = extract_model(TestModel)
        field = find_field(spec, "color")
        assert field.description == "Custom color description"

    def test_field_without_newtype_description_stays_none(self) -> None:
        """Field typed as plain str (no NewType description) keeps None."""

        class TestModel(BaseModel):
            name: str

        spec = extract_model(TestModel)
        field = find_field(spec, "name")
        assert field.description is None
