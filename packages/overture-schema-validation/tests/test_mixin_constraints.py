"""Comprehensive tests for mixin-based constraint validation."""

from enum import Enum
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from overture.schema.validation import (
    ConstraintValidatedModel,
    any_of,
    exactly_one_of,
    min_properties,
    not_required_if,
    required_if,
)
from overture.schema.validation.mixin import (
    AnyOfValidator,
    BaseConstraintValidator,
    ExactlyOneOfValidator,
    MinPropertiesValidator,
    NotRequiredIfValidator,
    RequiredIfValidator,
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


class TestConditionalRequiredValidator:
    """Test conditional required constraint validation."""

    def test_conditional_required_validator_direct(self) -> None:
        """Test RequiredIfValidator directly."""

        class TestModel(BaseModel):
            type_field: str
            required_field: str | None = None

        validator = RequiredIfValidator("type_field", "special", ["required_field"])

        # Valid: condition not met, field can be None
        model = TestModel(type_field="normal", required_field=None)
        validator.validate(model)  # Should not raise

        # Valid: condition met, field provided
        model = TestModel(type_field="special", required_field="value")
        validator.validate(model)  # Should not raise

        # Invalid: condition met, field missing
        model = TestModel(type_field="special", required_field=None)
        with pytest.raises(
            ValueError,
            match="Field 'required_field' is required when type_field = special",
        ):
            validator.validate(model)

    def test_conditional_required_constraint_decorator(self) -> None:
        """Test conditional required constraint using decorator."""

        @required_if("subtype", "road", ["class_"])
        @required_if("subtype", "rail", ["class_"])
        class SegmentModel(ConstraintValidatedModel, BaseModel):
            subtype: str
            class_: str | None = None

        # Valid: subtype doesn't require class_
        model = SegmentModel(subtype="water", class_=None)
        assert model.subtype == "water"
        assert model.class_ is None

        # Valid: road subtype with class_
        model = SegmentModel(subtype="road", class_="primary")
        assert model.subtype == "road"
        assert model.class_ == "primary"

        # Valid: rail subtype with class_
        model = SegmentModel(subtype="rail", class_="passenger")
        assert model.subtype == "rail"
        assert model.class_ == "passenger"

        # Invalid: road subtype without class_
        with pytest.raises(ValidationError) as exc_info:
            SegmentModel(subtype="road", class_=None)
        assert "Field 'class_' is required when subtype = road" in str(exc_info.value)

        # Invalid: rail subtype without class_
        with pytest.raises(ValidationError) as exc_info:
            SegmentModel(subtype="rail", class_=None)
        assert "Field 'class_' is required when subtype = rail" in str(exc_info.value)

    def test_conditional_required_multiple_fields(self) -> None:
        """Test conditional required constraint with multiple required fields."""

        @required_if("type", "complex", ["field_a", "field_b"])
        class TestModel(ConstraintValidatedModel, BaseModel):
            type: str
            field_a: str | None = None
            field_b: str | None = None

        # Valid: condition not met
        model = TestModel(type="simple", field_a=None, field_b=None)
        assert model.type == "simple"

        # Valid: condition met, all fields provided
        model = TestModel(type="complex", field_a="value_a", field_b="value_b")
        assert model.type == "complex"
        assert model.field_a == "value_a"
        assert model.field_b == "value_b"

        # Invalid: condition met, field_a missing
        with pytest.raises(ValidationError) as exc_info:
            TestModel(type="complex", field_a=None, field_b="value_b")
        assert "Field 'field_a' is required when type = complex" in str(exc_info.value)


class TestConditionalNotRequiredValidator:
    """Test conditional not required constraint validation."""

    def test_conditional_not_required_validator_direct(self) -> None:
        """Test NotRequiredIfValidator directly."""

        class TestModel(BaseModel):
            subtype: PlaceType
            country: str | None = None

        validator = NotRequiredIfValidator("subtype", PlaceType.COUNTRY, ["country"])

        # Valid: country subtype, country can be None
        model = TestModel(subtype=PlaceType.COUNTRY, country=None)
        validator.validate(model)  # Should not raise

        # Valid: non-country subtype, country provided
        model = TestModel(subtype=PlaceType.REGION, country="US")
        validator.validate(model)  # Should not raise

        # Invalid: non-country subtype, country missing
        model = TestModel(subtype=PlaceType.REGION, country=None)
        with pytest.raises(
            ValueError, match="Field 'country' is required when subtype != country"
        ):
            validator.validate(model)

    def test_conditional_not_required_constraint_decorator(self) -> None:
        """Test conditional not required constraint using decorator."""

        @not_required_if("subtype", PlaceType.COUNTRY, ["country"])
        class BoundaryModel(ConstraintValidatedModel, BaseModel):
            subtype: PlaceType
            country: str | None = None

        # Valid: country subtype, no country field needed
        model = BoundaryModel(subtype=PlaceType.COUNTRY, country=None)
        assert model.subtype == PlaceType.COUNTRY
        assert model.country is None

        # Valid: region subtype, country provided
        model = BoundaryModel(subtype=PlaceType.REGION, country="US")
        assert model.subtype == PlaceType.REGION
        assert model.country == "US"

        # Invalid: region subtype, country missing
        with pytest.raises(ValidationError) as exc_info:
            BoundaryModel(subtype=PlaceType.REGION, country=None)
        assert "Field 'country' is required when subtype != country" in str(
            exc_info.value
        )


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


class TestAnyOfValidator:
    """Test anyOf constraint validation."""

    def test_any_of_validator_direct(self) -> None:
        """Test AtLeastOneOfValidator directly."""

        class TestModel(BaseModel):
            max_speed: str | None = None
            min_speed: str | None = None

        validator = AnyOfValidator("max_speed", "min_speed")

        # Valid: max_speed provided
        model = TestModel(max_speed="50", min_speed=None)
        validator.validate(model)  # Should not raise

        # Valid: min_speed provided
        model = TestModel(max_speed=None, min_speed="30")
        validator.validate(model)  # Should not raise

        # Valid: both provided
        model = TestModel(max_speed="50", min_speed="30")
        validator.validate(model)  # Should not raise

        # Invalid: neither provided
        model = TestModel(max_speed=None, min_speed=None)
        with pytest.raises(
            ValueError, match="At least one of max_speed, min_speed must be present"
        ):
            validator.validate(model)

    def test_any_of_constraint_decorator(self) -> None:
        """Test at-least-one-of constraint using decorator."""

        @any_of("max_speed", "min_speed")
        class SpeedRuleModel(ConstraintValidatedModel, BaseModel):
            max_speed: str | None = None
            min_speed: str | None = None

        # Valid cases
        model = SpeedRuleModel(max_speed="50", min_speed=None)
        assert model.max_speed == "50"
        assert model.min_speed is None

        model = SpeedRuleModel(max_speed=None, min_speed="30")
        assert model.max_speed is None
        assert model.min_speed == "30"

        model = SpeedRuleModel(max_speed="50", min_speed="30")
        assert model.max_speed == "50"
        assert model.min_speed == "30"

        # Invalid case: neither provided
        with pytest.raises(ValidationError) as exc_info:
            SpeedRuleModel(max_speed=None, min_speed=None)
        assert "At least one of max_speed, min_speed must be present" in str(
            exc_info.value
        )

    def test_any_of_multiple_fields(self) -> None:
        """Test anyOf constraint with multiple fields."""

        @any_of("field_a", "field_b", "field_c")
        class TestModel(ConstraintValidatedModel, BaseModel):
            field_a: str | None = None
            field_b: str | None = None
            field_c: str | None = None

        # Valid: one field provided
        model = TestModel(field_a="value", field_b=None, field_c=None)
        assert model.field_a == "value"

        # Valid: multiple fields provided
        model = TestModel(field_a="value_a", field_b="value_b", field_c=None)
        assert model.field_a == "value_a"
        assert model.field_b == "value_b"

        # Invalid: no fields provided
        with pytest.raises(ValidationError) as exc_info:
            TestModel(field_a=None, field_b=None, field_c=None)
        assert "At least one of field_a, field_b, field_c must be present" in str(
            exc_info.value
        )


class TestMultipleConstraints:
    """Test models with multiple constraints applied."""

    def test_multiple_constraint_decorators(self) -> None:
        """Test applying multiple constraint decorators to one model."""

        @exactly_one_of("is_land", "is_territorial")
        @required_if("subtype", PlaceType.REGION, ["region_code"])
        class ComplexModel(ConstraintValidatedModel, BaseModel):
            subtype: PlaceType
            parent_division_id: str | None = None
            is_land: bool | None = None
            is_territorial: bool | None = None
            region_code: str | None = None

        # Valid: country with no parent, land boundary, no region code needed
        model = ComplexModel(
            subtype=PlaceType.COUNTRY,
            parent_division_id=None,
            is_land=True,
            is_territorial=False,
            region_code=None,
        )
        assert model.subtype == PlaceType.COUNTRY
        assert model.is_land is True

        # Valid: region with parent, territorial boundary, region code provided
        model = ComplexModel(
            subtype=PlaceType.REGION,
            parent_division_id="parent",
            is_land=False,
            is_territorial=True,
            region_code="US-CA",
        )
        assert model.subtype == PlaceType.REGION
        assert model.region_code == "US-CA"

        # Invalid: violates mutually exclusive constraint
        with pytest.raises(ValidationError) as exc_info:
            ComplexModel(
                subtype=PlaceType.REGION,
                parent_division_id="parent",
                is_land=True,
                is_territorial=True,  # Both True - invalid
                region_code="US-CA",
            )
        assert "Exactly one field must be true, but found 2" in str(exc_info.value)

        # Invalid: violates conditional required constraint
        with pytest.raises(ValidationError) as exc_info:
            ComplexModel(
                subtype=PlaceType.REGION,
                parent_division_id="parent",
                is_land=True,
                is_territorial=False,
                region_code=None,  # Required when subtype is REGION
            )
        assert "Field 'region_code' is required when subtype = region" in str(
            exc_info.value
        )

    def test_multiple_constraints_json_schema(self) -> None:
        """Test JSON schema generation with multiple constraints."""

        @exactly_one_of("field_a", "field_b")
        @any_of("required_a", "required_b")
        class MultiConstraintModel(ConstraintValidatedModel, BaseModel):
            subtype: PlaceType
            parent_division_id: str | None = None
            field_a: bool | None = None
            field_b: bool | None = None
            required_a: str | None = None
            required_b: str | None = None

        schema = MultiConstraintModel.model_json_schema()

        # Should have oneOf for exactly_one_of constraint (parallel to anyOf)
        assert "oneOf" in schema
        assert len(schema["oneOf"]) == 2  # For field_a and field_b

        # Should have anyOf for at_least_one_of constraint
        assert "anyOf" in schema
        assert len(schema["anyOf"]) == 2  # For required_a and required_b

    def test_multiple_constraints_with_min_properties(self) -> None:
        """Test min_properties constraint combined with other constraints."""

        @min_properties(1)
        @any_of("required_a", "required_b")
        class MultiConstraintModel(ConstraintValidatedModel, BaseModel):
            field_a: str | None = None
            field_b: str | None = None
            required_a: str | None = None
            required_b: str | None = None

        # Valid: satisfies both min_properties and any_of
        model = MultiConstraintModel(
            field_a="value", field_b=None, required_a="value", required_b=None
        )
        assert model.field_a == "value"
        assert model.required_a == "value"

        # Invalid: violates constraints (no properties set)
        # Either constraint could fail first, so check for either error
        with pytest.raises(ValidationError) as exc_info:
            MultiConstraintModel(
                field_a=None, field_b=None, required_a=None, required_b=None
            )
        error_str = str(exc_info.value)
        assert (
            "At least 1 properties must be set, but only 0 are set" in error_str
            or "At least one of required_a, required_b must be present" in error_str
        )

        # Invalid: satisfies min_properties but violates any_of
        with pytest.raises(ValidationError) as exc_info:
            MultiConstraintModel(
                field_a="value", field_b=None, required_a=None, required_b=None
            )
        assert "At least one of required_a, required_b must be present" in str(
            exc_info.value
        )

        # Test JSON schema generation includes both constraints
        schema = MultiConstraintModel.model_json_schema()
        assert "minProperties" in schema
        assert schema["minProperties"] == 1
        assert "anyOf" in schema
        assert len(schema["anyOf"]) == 2


class TestConstraintInheritance:
    """Test constraint inheritance and complex model hierarchies."""

    def test_constraint_inheritance(self) -> None:
        """Test that constraints work with model inheritance."""

        @exactly_one_of("field_a", "field_b")
        class TestBaseModel(ConstraintValidatedModel, BaseModel):
            field_a: bool | None = None
            field_b: bool | None = None

        @any_of("required_c", "required_d")
        class DerivedModel(TestBaseModel):
            required_c: str | None = None
            required_d: str | None = None

        # Valid: satisfies both constraints
        model = DerivedModel(
            field_a=True, field_b=False, required_c="value", required_d=None
        )
        assert model.field_a is True
        assert model.required_c == "value"

        # Invalid: violates base class constraint
        with pytest.raises(ValidationError) as exc_info:
            DerivedModel(
                field_a=True,
                field_b=True,  # Violates mutually exclusive
                required_c="value",
                required_d=None,
            )
        assert "Exactly one field must be true, but found 2" in str(exc_info.value)

        # Invalid: violates derived class constraint
        with pytest.raises(ValidationError) as exc_info:
            DerivedModel(
                field_a=True,
                field_b=False,
                required_c=None,
                required_d=None,  # Violates at_least_one_of
            )
        assert "At least one of required_c, required_d must be present" in str(
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

    def test_constraint_validation_order(self) -> None:
        """Test that constraints are validated in the correct order."""

        # This test ensures that field validation happens before constraint validation
        @required_if("type_field", "special", ["required_field"])
        class OrderTestModel(ConstraintValidatedModel, BaseModel):
            type_field: str
            required_field: str | None = None

        # Field validation should catch invalid type_field before constraint validation
        with pytest.raises(ValidationError) as exc_info:
            # This should fail due to validation of enum field, not constraint
            OrderTestModel(type_field=123, required_field=None)  # Invalid type

        # Constraint validation should catch missing required field
        with pytest.raises(ValidationError) as exc_info:
            OrderTestModel(type_field="special", required_field=None)
        assert "Field 'required_field' is required" in str(exc_info.value)

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

    def test_transportation_rule_model(self) -> None:
        """Test constraint validation on transportation rule models."""

        @any_of("max_speed", "min_speed")
        @required_if("is_variable", True, ["conditions"])
        class SpeedLimitRule(ConstraintValidatedModel, BaseModel):
            max_speed: dict | None = None
            min_speed: dict | None = None
            is_variable: bool = False
            conditions: list[str] | None = None

        # Valid: has max_speed, not variable
        rule = SpeedLimitRule(
            max_speed={"value": 50, "unit": "km/h"},
            min_speed=None,
            is_variable=False,
            conditions=None,
        )
        assert rule.max_speed is not None and rule.max_speed["value"] == 50

        # Valid: variable speed with conditions
        rule = SpeedLimitRule(
            max_speed={"value": 50, "unit": "km/h"},
            min_speed=None,
            is_variable=True,
            conditions=["weather_dependent"],
        )
        assert rule.is_variable is True
        assert rule.conditions == ["weather_dependent"]

        # Invalid: no speeds provided
        with pytest.raises(ValidationError) as exc_info:
            SpeedLimitRule(
                max_speed=None, min_speed=None, is_variable=False, conditions=None
            )
        assert "At least one of max_speed, min_speed must be present" in str(
            exc_info.value
        )

        # Invalid: variable but no conditions
        with pytest.raises(ValidationError) as exc_info:
            SpeedLimitRule(
                max_speed={"value": 50, "unit": "km/h"},
                min_speed=None,
                is_variable=True,
                conditions=None,
            )
        assert "Field 'conditions' is required when is_variable = True" in str(
            exc_info.value
        )


if __name__ == "__main__":
    pytest.main([__file__])
