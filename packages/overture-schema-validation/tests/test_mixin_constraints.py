"""Comprehensive tests for mixin-based constraint validation."""

from enum import Enum
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from overture.schema.validation import (
    ConstraintValidatedModel,
    exactly_one_of,
    min_properties,
)
from overture.schema.validation.mixin import (
    BaseConstraintValidator,
    ExactlyOneOfValidator,
    MinPropertiesValidator,
)


class PlaceType(str, Enum):
    """Test enum for place types."""

    COUNTRY = "country"
    REGION = "region"
    LOCALITY = "locality"


class TestBaseConstraintValidator:
    """Test the base constraint validator functionality."""

    def test_base_constraint_validator_abstract(self) -> None:
        """Test that BaseConstraintValidator is properly abstract."""
        with pytest.raises(TypeError):
            BaseConstraintValidator()  # type: ignore[abstract]

    def test_custom_constraint_validator(self) -> None:
        """Test creating a custom constraint validator."""

        class CustomValidator(BaseConstraintValidator):
            def __init__(self, required_value: str) -> None:
                super().__init__()
                self.required_value = required_value

            def validate(self, model_instance: BaseModel) -> None:
                if hasattr(model_instance, "custom_field"):
                    if model_instance.custom_field != self.required_value:
                        raise ValueError(f"custom_field must be {self.required_value}")

            def get_metadata(
                self, model_class: type[BaseModel] | None = None, by_alias: bool = True
            ) -> dict[str, Any]:
                return {
                    "type": "custom_constraint",
                    "required_value": self.required_value,
                }

            def apply_json_schema_metadata(
                self,
                target_schema: dict[str, Any],
                model_class: type[BaseModel] | None = None,
                by_alias: bool = True,
            ) -> None:
                """Apply custom constraint metadata to the schema."""
                # This is just a test constraint, so we'll add a simple property
                metadata = self.get_metadata(model_class, by_alias)
                target_schema["custom_constraint"] = metadata

        # Test the custom validator
        validator = CustomValidator("expected")

        class TestModel(BaseModel):
            custom_field: str

        # Valid case
        model = TestModel(custom_field="expected")
        validator.validate(model)  # Should not raise

        # Invalid case
        model = TestModel(custom_field="wrong")
        with pytest.raises(ValueError, match="custom_field must be expected"):
            validator.validate(model)

        # Test metadata
        metadata = validator.get_metadata()
        assert metadata["type"] == "custom_constraint"
        assert metadata["required_value"] == "expected"


class TestConstraintValidatedModel:
    """Test the ConstraintValidatedModel base class."""

    def test_constraint_validated_model_inheritance(self) -> None:
        """Test that ConstraintValidatedModel can be inherited."""

        class TestModel(ConstraintValidatedModel, BaseModel):
            name: str

        # Should create without issues
        model = TestModel(name="test")
        assert model.name == "test"

    def test_constraint_validated_model_with_no_constraints(self) -> None:
        """Test that models without constraints work normally."""

        class TestModel(ConstraintValidatedModel, BaseModel):
            name: str
            value: int = 42

        model = TestModel(name="test", value=100)
        assert model.name == "test"
        assert model.value == 100

    def test_json_schema_generation_no_constraints(self) -> None:
        """Test JSON schema generation for models without constraints."""

        class TestModel(ConstraintValidatedModel, BaseModel):
            name: str
            value: int = 42

        schema = TestModel.model_json_schema()

        # Should have standard properties
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "value" in schema["properties"]

        # Should not have constraint-specific fields
        assert "allOf" not in schema


class TestExactlyOneOfValidator:
    """Test exactly one of constraint validation."""

    def test_exactly_one_of_validator_direct(self) -> None:
        """Test ExactlyOneOfValidator directly."""

        class TestModel(BaseModel):
            field_a: bool | None = None
            field_b: bool | None = None

        validator = ExactlyOneOfValidator("field_a", "field_b")

        # Valid: exactly one field is True
        model = TestModel(field_a=True, field_b=False)
        validator.validate(model)  # Should not raise

        model = TestModel(field_a=False, field_b=True)
        validator.validate(model)  # Should not raise

        # Invalid: no fields are True
        model = TestModel(field_a=False, field_b=False)
        with pytest.raises(
            ValueError, match="Exactly one of field_a, field_b must be true"
        ):
            validator.validate(model)

        # Invalid: fields are None (treated as not True)
        model = TestModel(field_a=None, field_b=None)
        with pytest.raises(
            ValueError, match="Exactly one of field_a, field_b must be true"
        ):
            validator.validate(model)

        # Invalid: both fields are True
        model = TestModel(field_a=True, field_b=True)
        with pytest.raises(
            ValueError,
            match="Exactly one field must be true, but found 2: field_a, field_b",
        ):
            validator.validate(model)

    def test_exactly_one_of_constraint_decorator(self) -> None:
        """Test exactly one of constraint using decorator."""

        @exactly_one_of("is_land", "is_territorial")
        class DivisionModel(ConstraintValidatedModel, BaseModel):
            is_land: bool | None = None
            is_territorial: bool | None = None

        # Valid cases: exactly one is True
        model = DivisionModel(is_land=True, is_territorial=False)
        assert model.is_land is True
        assert model.is_territorial is False

        model = DivisionModel(is_land=False, is_territorial=True)
        assert model.is_land is False
        assert model.is_territorial is True

        # Invalid case: neither True
        with pytest.raises(ValidationError) as exc_info:
            DivisionModel(is_land=False, is_territorial=False)
        assert "Exactly one of is_land, is_territorial must be true" in str(
            exc_info.value
        )

        # Invalid case: both True
        with pytest.raises(ValidationError) as exc_info:
            DivisionModel(is_land=True, is_territorial=True)
        assert (
            "Exactly one field must be true, but found 2: is_land, is_territorial"
            in str(exc_info.value)
        )

        # Invalid case: both None
        with pytest.raises(ValidationError) as exc_info:
            DivisionModel(is_land=None, is_territorial=None)
        assert "Exactly one of is_land, is_territorial must be true" in str(
            exc_info.value
        )

    def test_exactly_one_of_multiple_fields(self) -> None:
        """Test exactly one of constraint with more than 2 fields."""

        @exactly_one_of("option_a", "option_b", "option_c")
        class OptionsModel(ConstraintValidatedModel, BaseModel):
            option_a: bool | None = None
            option_b: bool | None = None
            option_c: bool | None = None

        # Valid: exactly one option True
        model = OptionsModel(option_a=True, option_b=False, option_c=False)
        assert model.option_a is True

        model = OptionsModel(option_a=False, option_b=True, option_c=False)
        assert model.option_b is True

        model = OptionsModel(option_a=False, option_b=False, option_c=True)
        assert model.option_c is True

        # Invalid: no options True
        with pytest.raises(ValidationError) as exc_info:
            OptionsModel(option_a=False, option_b=False, option_c=False)
        assert "Exactly one of option_a, option_b, option_c must be true" in str(
            exc_info.value
        )

        # Invalid: multiple options True
        with pytest.raises(ValidationError) as exc_info:
            OptionsModel(option_a=True, option_b=True, option_c=False)
        assert "Exactly one field must be true, but found 2: option_a, option_b" in str(
            exc_info.value
        )

    def test_exactly_one_of_json_schema(self) -> None:
        """Test JSON schema generation for exactly one of constraint."""

        @exactly_one_of("field_a", "field_b")
        class TestModel(ConstraintValidatedModel, BaseModel):
            field_a: bool | None = None
            field_b: bool | None = None

        schema = TestModel.model_json_schema()

        # Should have oneOf constraint (ExactlyOneOfValidator generates oneOf)
        # The constraint metadata is included by the ConstraintValidatedModel at top level
        assert "oneOf" in schema
        assert len(schema["oneOf"]) == 2


class TestMinPropertiesValidator:
    """Test minimum properties constraint validation."""

    def test_min_properties_validator_direct(self) -> None:
        """Test MinPropertiesValidator directly."""

        class TestModel(BaseModel):
            field_a: str | None = None
            field_b: str | None = None
            field_c: str | None = None

        validator = MinPropertiesValidator(min_count=1)

        # Valid: one property is set
        model = TestModel(field_a="value", field_b=None, field_c=None)
        validator.validate(model)  # Should not raise

        # Valid: multiple properties are set
        model = TestModel(field_a="value_a", field_b="value_b", field_c=None)
        validator.validate(model)  # Should not raise

        # Invalid: no properties are set
        model = TestModel(field_a=None, field_b=None, field_c=None)
        with pytest.raises(
            ValueError, match="At least 1 properties must be set, but only 0 are set"
        ):
            validator.validate(model)

    def test_min_properties_constraint_decorator(self) -> None:
        """Test minimum properties constraint using decorator."""

        @min_properties(1)
        class MinOnePropertyModel(ConstraintValidatedModel, BaseModel):
            heading: str | None = None
            during: str | None = None

        # Valid: one property is set
        model = MinOnePropertyModel(heading="north", during=None)
        assert model.heading == "north"
        assert model.during is None

        # Valid: both properties are set
        model = MinOnePropertyModel(heading="north", during="daytime")
        assert model.heading == "north"
        assert model.during == "daytime"

        # Invalid: no properties are set
        with pytest.raises(ValidationError) as exc_info:
            MinOnePropertyModel(heading=None, during=None)
        assert "At least 1 properties must be set, but only 0 are set" in str(
            exc_info.value
        )

    def test_min_properties_higher_count(self) -> None:
        """Test minimum properties constraint with higher minimum count."""

        @min_properties(2)
        class MinTwoPropertiesModel(ConstraintValidatedModel, BaseModel):
            field_a: str | None = None
            field_b: str | None = None
            field_c: str | None = None

        # Valid: exactly 2 properties set
        model = MinTwoPropertiesModel(
            field_a="value_a", field_b="value_b", field_c=None
        )
        assert model.field_a == "value_a"
        assert model.field_b == "value_b"

        # Valid: all 3 properties set
        model = MinTwoPropertiesModel(
            field_a="value_a", field_b="value_b", field_c="value_c"
        )
        assert model.field_a == "value_a"
        assert model.field_c == "value_c"

        # Invalid: only 1 property set
        with pytest.raises(ValidationError) as exc_info:
            MinTwoPropertiesModel(field_a="value_a", field_b=None, field_c=None)
        assert "At least 2 properties must be set, but only 1 are set" in str(
            exc_info.value
        )

        # Invalid: no properties set
        with pytest.raises(ValidationError) as exc_info:
            MinTwoPropertiesModel(field_a=None, field_b=None, field_c=None)
        assert "At least 2 properties must be set, but only 0 are set" in str(
            exc_info.value
        )

    def test_min_properties_json_schema(self) -> None:
        """Test JSON schema generation for minimum properties constraint."""

        @min_properties(1)
        class TestModel(ConstraintValidatedModel, BaseModel):
            field_a: str | None = None
            field_b: str | None = None

        schema = TestModel.model_json_schema()

        # Should have minProperties constraint
        assert "minProperties" in schema
        assert schema["minProperties"] == 1

    def test_min_properties_with_inheritance(self) -> None:
        """Test minimum properties constraint with model inheritance."""

        @min_properties(1)
        class BaseTestModel(ConstraintValidatedModel, BaseModel):
            field_a: str | None = None
            field_b: str | None = None

        class DerivedModel(BaseTestModel):
            field_c: str | None = None

        # Valid: base property set
        model = DerivedModel(field_a="value", field_b=None, field_c=None)
        assert model.field_a == "value"

        # Valid: derived property set
        model = DerivedModel(field_a=None, field_b=None, field_c="value")
        assert model.field_c == "value"

        # Invalid: no properties set
        with pytest.raises(ValidationError) as exc_info:
            DerivedModel(field_a=None, field_b=None, field_c=None)
        assert "At least 1 properties must be set, but only 0 are set" in str(
            exc_info.value
        )


class TestConstraintErrorHandling:
    """Test error handling and edge cases."""

    def test_constraint_with_missing_fields(self) -> None:
        """Test constraints when referenced fields don't exist."""

        @exactly_one_of("field_a", "field_b")
        class IncompleteModel(ConstraintValidatedModel, BaseModel):
            # Missing subtype and parent_division_id fields
            name: str

        # Should not raise validation errors for missing fields
        # (constraint should handle missing fields gracefully)
        model = IncompleteModel(name="test")
        assert model.name == "test"

    def test_constraint_validator_without_mixin(self) -> None:
        """Test that decorators work but validation won't be applied without the
        mixin."""

        # This should not raise - decorators can be applied to any class
        # but validation won't happen without ConstraintValidatedModel
        @exactly_one_of("field_a", "field_b")
        class InvalidModel(BaseModel):  # Missing ConstraintValidatedModel
            field_a: bool | None = None
            field_b: bool | None = None

        # This should NOT fail validation since ConstraintValidatedModel isn't mixed in
        model = InvalidModel(
            field_a=True,
            field_b=True,  # would fail validation if mixin was present
        )
        assert model.field_a is True

    def test_json_schema_with_no_constraints(self) -> None:
        """Test JSON schema generation when no constraints are registered."""

        class PlainModel(ConstraintValidatedModel, BaseModel):
            name: str
            value: int

        schema = PlainModel.model_json_schema()

        # Should generate normal schema without constraint extensions
        assert "properties" in schema
        assert "allOf" not in schema


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_geojson_feature_model(self) -> None:
        """Test constraint validation on a GeoJSON-like feature model."""

        @exactly_one_of("is_land", "is_territorial")
        class PropertiesModel(ConstraintValidatedModel, BaseModel):
            subtype: PlaceType
            parent_division_id: str | None = None
            is_land: bool | None = None
            is_territorial: bool | None = None

        class FeatureModel(BaseModel):
            id: str
            type: str = "Feature"
            properties: PropertiesModel
            geometry: dict

        # Valid feature
        feature_data = {
            "id": "test-feature",
            "properties": {
                "subtype": PlaceType.REGION,
                "parent_division_id": "US",
                "is_land": True,
                "is_territorial": False,
            },
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }

        model = FeatureModel(**feature_data)
        assert model.id == "test-feature"
        assert model.properties.subtype == PlaceType.REGION

        # Invalid feature - violates mutually exclusive constraint
        invalid_feature_data = {
            "id": "invalid-feature",
            "properties": {
                "subtype": PlaceType.COUNTRY,
                "parent_division_id": "parent",
                "is_land": True,
                "is_territorial": True,  # Both True - violates mutually exclusive
            },
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }

        with pytest.raises(ValidationError) as exc_info:
            FeatureModel(**invalid_feature_data)
        assert "Exactly one field must be true, but found 2" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])
