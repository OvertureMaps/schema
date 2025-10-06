"""Test JSON Schema generation for mixin-based constraint validation."""

from enum import Enum
from typing import Any

import pytest
from overture.schema.core.types import LinearReferenceRangeConstraint
from overture.schema.system.constraint import UniqueItemsConstraint
from overture.schema.system.constraint.string import (
    CountryCodeAlpha2Constraint,
    HexColorConstraint,
    JsonPointerConstraint,
    LanguageTagConstraint,
    NoWhitespaceConstraint,
    PatternConstraint,
    RegionCodeConstraint,
    StrippedConstraint,
)
from pydantic import BaseModel, Field

from overture.schema.validation.constraints import (
    ConfidenceScoreConstraint,
)
from overture.schema.validation.mixin import (
    ConstraintValidatedModel,
    any_of,
    exactly_one_of,
    required_if,
)


class SubtypeEnum(str, Enum):
    """Test enum for subtypes."""

    COUNTRY = "country"
    REGION = "region"
    LOCALITY = "locality"


def create_field_constraint_model(
    field_type: type[Any], constraint_instance: object
) -> type[BaseModel]:
    """Create a test model with a single field using the given constraint."""
    from typing import Annotated

    class TestModel(ConstraintValidatedModel, BaseModel):
        test_field: Annotated[Any, constraint_instance]

    return TestModel


def assert_pattern_constraint(
    schema: dict[str, Any],
    field_name: str,
    expected_pattern: str,
    expected_description: str | None = None,
) -> None:
    """Assert that a field has the expected pattern constraint."""
    assert "properties" in schema
    assert field_name in schema["properties"]
    field_schema = schema["properties"][field_name]
    assert "pattern" in field_schema
    assert field_schema["pattern"] == expected_pattern
    if expected_description:
        assert field_schema.get("description") == expected_description


def assert_range_constraint(
    schema: dict[str, Any],
    field_name: str,
    min_val: float | None = None,
    max_val: float | None = None,
    description: str | None = None,
) -> None:
    """Assert that a field has the expected range constraints."""
    assert "properties" in schema
    assert field_name in schema["properties"]
    field_schema = schema["properties"][field_name]
    if min_val is not None:
        assert field_schema.get("minimum") == min_val
    if max_val is not None:
        assert field_schema.get("maximum") == max_val
    if description:
        assert field_schema.get("description") == description


def assert_collection_constraint(
    schema: dict[str, Any],
    field_name: str,
    min_items: int | None = None,
    max_items: int | None = None,
    unique_items: bool | None = None,
) -> None:
    """Assert that a field has the expected collection constraints."""
    assert "properties" in schema
    assert field_name in schema["properties"]
    field_schema = schema["properties"][field_name]
    if min_items is not None:
        assert field_schema.get("minItems") == min_items
    if max_items is not None:
        assert field_schema.get("maxItems") == max_items
    if unique_items is not None:
        assert field_schema.get("uniqueItems") == unique_items


class TestJSONSchemaGeneration:
    """Test JSON Schema generation for constraint-validated models."""

    def test_exactly_one_of_constraint_json_schema(self) -> None:
        """Test JSON Schema generation for mutually exclusive constraint."""

        @exactly_one_of("field_a", "field_b")
        class TestModel(ConstraintValidatedModel, BaseModel):
            field_a: bool | None = None
            field_b: bool | None = None

        schema = TestModel.model_json_schema()

        # Should have oneOf constraint at top level (parallel to allOf)
        assert "oneOf" in schema
        assert len(schema["oneOf"]) == 2

        # Check that each field appears in oneOf with const: True
        field_a_condition = schema["oneOf"][0]
        field_b_condition = schema["oneOf"][1]

        assert field_a_condition["properties"]["field_a"]["const"] is True
        assert field_b_condition["properties"]["field_b"]["const"] is True

    def test_conditional_required_constraint_json_schema(self) -> None:
        """Test JSON Schema generation for conditional required constraint."""

        @required_if("type_field", "special", ["required_field"])
        class TestModel(ConstraintValidatedModel, BaseModel):
            type_field: str
            required_field: str | None = None

        schema = TestModel.model_json_schema()

        # Should have conditional in allOf
        assert "allOf" in schema
        assert len(schema["allOf"]) == 1

        condition = schema["allOf"][0]
        assert "if" in condition
        assert "then" in condition

    def test_at_least_one_of_constraint_json_schema(self) -> None:
        """Test JSON Schema generation for at-least-one-of constraint."""

        @any_of("field_a", "field_b")
        class TestModel(ConstraintValidatedModel, BaseModel):
            field_a: str | None = None
            field_b: str | None = None

        schema = TestModel.model_json_schema()

        # Should have anyOf constraint
        assert "anyOf" in schema
        assert len(schema["anyOf"]) == 2

        # Check anyOf structure
        required_fields = []
        for condition in schema["anyOf"]:
            assert "required" in condition
            required_fields.extend(condition["required"])

        assert set(required_fields) == {"field_a", "field_b"}

    def test_multiple_constraints_json_schema(self) -> None:
        """Test JSON Schema generation with multiple constraints."""

        @exactly_one_of("flag_a", "flag_b")
        @any_of("required_a", "required_b")
        class TestModel(ConstraintValidatedModel, BaseModel):
            flag_a: bool | None = None
            flag_b: bool | None = None
            required_a: str | None = None
            required_b: str | None = None

        schema = TestModel.model_json_schema()

        # Should have oneOf for exactly_one_of constraint (parallel to anyOf)
        assert "oneOf" in schema
        assert len(schema["oneOf"]) == 2  # For flag_a and flag_b

        # Should have anyOf for at_least_one_of constraint
        assert "anyOf" in schema
        assert len(schema["anyOf"]) == 2  # For required_a and required_b

    def test_no_constraints_json_schema(self) -> None:
        """Test JSON Schema generation for models without constraints."""

        class TestModel(ConstraintValidatedModel, BaseModel):
            name: str
            value: int = 42

        schema = TestModel.model_json_schema()

        # Should have standard properties but no constraint extensions
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "value" in schema["properties"]

        # Should not have constraint-specific fields
        assert "allOf" not in schema or len(schema.get("allOf", [])) == 0
        assert "anyOf" not in schema or len(schema.get("anyOf", [])) == 0
        assert "oneOf" not in schema or len(schema.get("oneOf", [])) == 0

    def test_nested_constraint_json_schema(self) -> None:
        """Test JSON Schema generation for models with nested properties."""

        class NestedProperties(BaseModel):
            subtype: SubtypeEnum
            parent_division_id: str | None = None

        @exactly_one_of("flag_a", "flag_b")
        class TestModel(ConstraintValidatedModel, BaseModel):
            id: str
            properties: NestedProperties
            flag_a: bool | None = None
            flag_b: bool | None = None

        schema = TestModel.model_json_schema()

        # With the new approach, constraints are applied at the root level
        # where the constraint decorator was applied
        assert "oneOf" in schema
        assert len(schema["oneOf"]) == 2

        # Verify the constraint is correctly structured
        one_of_options = schema["oneOf"]
        assert {"properties": {"flag_a": {"const": True}}} in one_of_options
        assert {"properties": {"flag_b": {"const": True}}} in one_of_options

    def test_json_schema_structure_validity(self) -> None:
        """Test that generated JSON Schema has valid structure."""

        @exactly_one_of("is_active", "is_inactive")
        class TestModel(ConstraintValidatedModel, BaseModel):
            subtype: SubtypeEnum
            is_active: bool | None = None
            is_inactive: bool | None = None
            name: str = Field(..., description="Model name")

        schema = TestModel.model_json_schema()

        # Should have standard JSON Schema structure
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "title" in schema

        # Should have required fields
        assert "required" in schema
        assert "subtype" in schema["required"]
        assert "name" in schema["required"]

        # Property definitions should be valid
        properties = schema["properties"]
        assert "subtype" in properties
        assert "name" in properties

        # Enum should be properly defined
        if "$defs" in schema:
            assert "SubtypeEnum" in schema["$defs"]
            enum_def = schema["$defs"]["SubtypeEnum"]
            assert enum_def["type"] == "string"
            assert "enum" in enum_def

        # Conditional fields should be properly structured
        if "allOf" in schema:
            for condition in schema["allOf"]:
                # Each condition should have proper JSON Schema structure
                assert isinstance(condition, dict)

    def test_pattern_constraint_json_schema(self) -> None:
        """Test PatternConstraint JSON schema generation."""
        constraint = PatternConstraint(
            pattern=r"^[A-Z]{2,4}$", error_message="Must be 2-4 uppercase letters"
        )
        TestModel = create_field_constraint_model(str, constraint)
        schema = TestModel.model_json_schema()

        assert_pattern_constraint(schema, "test_field", r"^[A-Z]{2,4}$")

    def test_language_tag_constraint_json_schema(self) -> None:
        """Test LanguageTagConstraint JSON schema generation."""
        constraint = LanguageTagConstraint()
        TestModel = create_field_constraint_model(str, constraint)
        schema = TestModel.model_json_schema()

        assert_pattern_constraint(
            schema,
            "test_field",
            r"^(?:(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}?)|(?:[A-Za-z]{4,8}))(?:-[A-Za-z]{4})?(?:-[A-Za-z]{2}|[0-9]{3})?(?:-(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*(?:-[A-WY-Za-wy-z0-9](?:-[A-Za-z0-9]{2,8})+)*$",
            "IETF BCP-47 language tag",
        )

    def test_country_code_constraint_json_schema(self) -> None:
        """Test CountryCodeAlpha2Constraint JSON schema generation."""
        constraint = CountryCodeAlpha2Constraint()
        TestModel = create_field_constraint_model(str, constraint)
        schema = TestModel.model_json_schema()

        assert_pattern_constraint(
            schema, "test_field", r"^[A-Z]{2}$", "ISO 3166-1 alpha-2 country code"
        )

    def test_region_code_constraint_json_schema(self) -> None:
        """Test RegionCodeConstraint JSON schema generation."""
        constraint = RegionCodeConstraint()
        TestModel = create_field_constraint_model(str, constraint)
        schema = TestModel.model_json_schema()

        assert_pattern_constraint(
            schema,
            "test_field",
            r"^[A-Z]{2}-[A-Z0-9]{1,3}$",
            "ISO 3166-2 subdivision code",
        )

    def test_hex_color_constraint_json_schema(self) -> None:
        """Test HexColorConstraint JSON schema generation."""
        constraint = HexColorConstraint()
        TestModel = create_field_constraint_model(str, constraint)
        schema = TestModel.model_json_schema()

        assert_pattern_constraint(
            schema,
            "test_field",
            r"^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$",
            "Hexadecimal color code in format #RGB or #RRGGBB",
        )

    def test_no_whitespace_constraint_json_schema(self) -> None:
        """Test NoWhitespaceConstraint JSON schema generation."""
        constraint = NoWhitespaceConstraint()
        TestModel = create_field_constraint_model(str, constraint)
        schema = TestModel.model_json_schema()

        assert_pattern_constraint(
            schema, "test_field", r"^\S+$", "String without whitespace characters"
        )

    def test_json_pointer_constraint_json_schema(self) -> None:
        """Test JsonPointerConstraint JSON schema generation."""
        constraint = JsonPointerConstraint()
        TestModel = create_field_constraint_model(str, constraint)
        schema = TestModel.model_json_schema()

        assert "properties" in schema
        assert "test_field" in schema["properties"]
        field_schema = schema["properties"]["test_field"]
        assert field_schema.get("description") == "JSON Pointer (RFC 6901)"

    def test_whitespace_constraint_json_schema(self) -> None:
        """Test WhitespaceConstraint JSON schema generation."""
        constraint = StrippedConstraint()
        TestModel = create_field_constraint_model(str, constraint)
        schema = TestModel.model_json_schema()

        assert_pattern_constraint(
            schema,
            "test_field",
            r"^(\S.*)?\S$",
            "String with no leading/trailing whitespace",
        )

    def test_unique_items_constraint_json_schema(self) -> None:
        """Test UniqueItemsConstraint JSON schema generation."""
        constraint = UniqueItemsConstraint()
        TestModel = create_field_constraint_model(list[str], constraint)
        schema = TestModel.model_json_schema()

        assert_collection_constraint(schema, "test_field", unique_items=True)

    def test_confidence_score_constraint_json_schema(self) -> None:
        """Test ConfidenceScoreConstraint JSON schema generation."""
        constraint = ConfidenceScoreConstraint()
        TestModel = create_field_constraint_model(float, constraint)
        schema = TestModel.model_json_schema()

        assert_range_constraint(
            schema,
            "test_field",
            min_val=0.0,
            max_val=1.0,
            description="Confidence score between 0.0 and 1.0",
        )

    def test_linear_reference_range_constraint_json_schema(self) -> None:
        """Test LinearReferenceRangeConstraint JSON schema generation."""
        constraint = LinearReferenceRangeConstraint()
        TestModel = create_field_constraint_model(list[float], constraint)
        schema = TestModel.model_json_schema()

        assert "properties" in schema
        assert "test_field" in schema["properties"]
        field_schema = schema["properties"]["test_field"]
        assert field_schema.get("type") == "array"
        assert field_schema.get("minItems") == 2
        assert field_schema.get("maxItems") == 2
        assert field_schema.get("items") == {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        }
        assert (
            field_schema.get("description")
            == "Linear reference range [start, end] where 0.0 <= start < end <= 1.0"
        )


if __name__ == "__main__":
    pytest.main([__file__])
