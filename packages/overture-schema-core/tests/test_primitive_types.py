"""Tests for primitive data types functionality."""

from typing import Annotated

import pytest
from overture.schema.system.primitive import (
    float32,
    float64,
    int32,
    uint8,
    uint16,
)
from pydantic import BaseModel, Field, ValidationError


class TestValidation:
    """Test validation behavior of primitive types."""

    def test_uint8_validation(self) -> None:
        """Test UInt8 validation constraints."""

        class TestModel(BaseModel):
            value: uint8

        # Valid values
        assert TestModel(value=0).value == 0
        assert TestModel(value=255).value == 255
        assert TestModel(value=128).value == 128

        # Invalid values
        with pytest.raises(ValidationError):
            TestModel(value=-1)
        with pytest.raises(ValidationError):
            TestModel(value=256)

    def test_int32_validation(self) -> None:
        """Test Int32 validation constraints."""

        class TestModel(BaseModel):
            value: int32

        # Valid values
        assert TestModel(value=0).value == 0
        assert TestModel(value=-(2**31)).value == -(2**31)
        assert TestModel(value=2**31 - 1).value == 2**31 - 1

        # Invalid values
        with pytest.raises(ValidationError):
            TestModel(value=-(2**31) - 1)
        with pytest.raises(ValidationError):
            TestModel(value=2**31)

    def test_optional_fields(self) -> None:
        """Test optional primitive type fields."""

        class TestModel(BaseModel):
            required_value: uint8
            optional_value: uint16 | None = None

        # Valid with both fields
        model = TestModel(required_value=100, optional_value=1000)
        assert model.required_value == 100
        assert model.optional_value == 1000

        # Valid with only required field
        model = TestModel(required_value=50)
        assert model.required_value == 50
        assert model.optional_value is None

    def test_float_types(self) -> None:
        """Test float primitive types."""

        class TestModel(BaseModel):
            f32: float32
            f64: float64

        model = TestModel(f32=3.14, f64=2.71828)
        assert model.f32 == 3.14
        assert model.f64 == 2.71828

    def test_conflicting_validation_criteria(self) -> None:
        """Test that Field constraints closest to use take precedence over primitive
        type constraints."""

        # Int32 has built-in constraints: ge=-(2**31), le=2**31-1
        # But we'll add more restrictive constraints that should win
        class TestModelRestrictive(BaseModel):
            # This should use le=5 instead of the Int32's le=2**31-1
            value: Annotated[int32, Field(le=5)]

        # Valid values within the more restrictive bound
        assert TestModelRestrictive(value=0).value == 0
        assert TestModelRestrictive(value=5).value == 5
        assert TestModelRestrictive(value=-5).value == -5

        # Should fail with the more restrictive constraint (le=5), not the primitive type constraint
        with pytest.raises(ValidationError) as exc_info:
            TestModelRestrictive(value=6)

        # Verify the error message references the closer constraint (le=5), not Int32's constraint
        error_msg = str(exc_info.value)
        assert "less than or equal to 5" in error_msg

        # Test with less restrictive constraints that should still be overridden
        class TestModelPermissive(BaseModel):
            # Int32 has ge=-(2**31) but we set ge=-10, so ge=-10 should win
            value: Annotated[int32, Field(ge=-10)]

        # Valid with the closer constraint
        assert TestModelPermissive(value=-10).value == -10
        assert TestModelPermissive(value=0).value == 0

        # Should fail with the closer constraint (ge=-10), not the primitive type constraint
        with pytest.raises(ValidationError) as exc_info:
            TestModelPermissive(value=-11)

        error_msg = str(exc_info.value)
        assert "greater than or equal to -10" in error_msg

        # Test multiple overlapping constraints - closest should win
        class TestModelMultiple(BaseModel):
            # Multiple Field annotations - the outermost (closest to use) should win
            value: Annotated[int32, Field(ge=0), Field(le=10)]

        # Valid within all constraints
        assert TestModelMultiple(value=5).value == 5
        assert TestModelMultiple(value=0).value == 0
        assert TestModelMultiple(value=10).value == 10

        # Should fail the closest constraints
        with pytest.raises(ValidationError):
            TestModelMultiple(value=-1)  # violates ge=0
        with pytest.raises(ValidationError):
            TestModelMultiple(value=11)  # violates le=10


class TestNestedAnnotations:
    def test_nested_annotations_with_pydantic_fields(self) -> None:
        """Test nested annotations combined with Pydantic Field constraints."""
        # and add additional Field constraints
        ConstrainedUInt8 = Annotated[
            Annotated[uint8, Field(description="inner constraint")],
            Field(le=100, description="outer constraint"),
        ]

        class TestModel(BaseModel):
            value: ConstrainedUInt8

        # Should work within all constraints
        model = TestModel(value=50)
        assert model.value == 50

        # Test that the outer constraint (le=100) is applied along with UInt8's constraints
        with pytest.raises(ValidationError):
            TestModel(value=150)  # Violates outer le=100

        # Test that UInt8's constraints (ge=0) are still applied
        with pytest.raises(ValidationError):
            TestModel(value=-1)  # Violates UInt8's ge=0
