"""Tests for abstract data types functionality."""

import pytest
from overture.schema.core.types.abstract import (
    AbstractType,
    AbstractTypeDefinition,
    AbstractTypeRegistry,
    Float32,
    Float64,
    Int8,
    Int32,
    Int64,
    UInt8,
    UInt16,
    UInt32,
    get_abstract_type,
    get_target_type,
)
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo


class TestAbstractType:
    """Test the AbstractType registry and dispatcher."""

    def test_registry_types_exist(self) -> None:
        """Test that all expected types exist in the registry."""
        expected_values = {
            "UINT8",
            "UINT16",
            "UINT32",
            "INT8",
            "INT32",
            "INT64",
            "FLOAT32",
            "FLOAT64",
            "GEOMETRY",
        }
        actual_values = set(AbstractTypeRegistry.TYPES.keys())
        assert actual_values == expected_values

    def test_dispatcher_creates_annotated_types(self) -> None:
        """Test that the dispatcher creates proper Annotated types."""
        uint8_type = AbstractType["UINT8"]  # type: ignore[misc,name-defined,type-arg]
        assert hasattr(uint8_type, "__metadata__")
        assert len(uint8_type.__metadata__) >= 1

        # First metadata item should be the AbstractTypeDefinition
        type_def = uint8_type.__metadata__[0]  # type: ignore[misc,valid-type]
        assert isinstance(type_def, AbstractTypeDefinition)
        assert type_def.base is int

    def test_get_target_type_scala(self) -> None:
        """Test getting Scala type mappings."""
        uint8_def = AbstractTypeRegistry.TYPES["UINT8"]
        int32_def = AbstractTypeRegistry.TYPES["INT32"]
        float64_def = AbstractTypeRegistry.TYPES["FLOAT64"]

        assert uint8_def.target_mappings["scala"] == "Byte"
        assert int32_def.target_mappings["scala"] == "Int"
        assert float64_def.target_mappings["scala"] == "Double"

    def test_get_target_type_spark(self) -> None:
        """Test getting Spark type mappings."""
        uint8_def = AbstractTypeRegistry.TYPES["UINT8"]
        int32_def = AbstractTypeRegistry.TYPES["INT32"]
        float32_def = AbstractTypeRegistry.TYPES["FLOAT32"]

        assert uint8_def.target_mappings["spark"] == "ByteType"
        assert int32_def.target_mappings["spark"] == "IntegerType"
        assert float32_def.target_mappings["spark"] == "FloatType"

    def test_get_target_type_parquet(self) -> None:
        """Test getting Parquet type mappings."""
        uint8_def = AbstractTypeRegistry.TYPES["UINT8"]
        int32_def = AbstractTypeRegistry.TYPES["INT32"]
        int64_def = AbstractTypeRegistry.TYPES["INT64"]
        float32_def = AbstractTypeRegistry.TYPES["FLOAT32"]
        float64_def = AbstractTypeRegistry.TYPES["FLOAT64"]

        assert uint8_def.target_mappings["parquet"] == "INT32"
        assert int32_def.target_mappings["parquet"] == "INT32"
        assert int64_def.target_mappings["parquet"] == "INT64"
        assert float32_def.target_mappings["parquet"] == "FLOAT"
        assert float64_def.target_mappings["parquet"] == "DOUBLE"

    def test_get_constraints(self) -> None:
        """Test getting Pydantic constraints."""

        def get_constraint_value(
            field_info: FieldInfo | None, constraint_type: str
        ) -> int | None:
            """Helper to extract constraint values from FieldInfo metadata."""
            if field_info is None:
                return None
            for constraint in field_info.metadata:
                if hasattr(constraint, constraint_type):
                    value = getattr(constraint, constraint_type)
                    return value if isinstance(value, int) else None
            return None

        uint8_def = AbstractTypeRegistry.TYPES["UINT8"]
        assert get_constraint_value(uint8_def.constraints, "ge") == 0
        assert get_constraint_value(uint8_def.constraints, "le") == 255

        int32_def = AbstractTypeRegistry.TYPES["INT32"]
        assert get_constraint_value(int32_def.constraints, "ge") == -(2**31)
        assert get_constraint_value(int32_def.constraints, "le") == 2**31 - 1

        float32_def = AbstractTypeRegistry.TYPES["FLOAT32"]
        assert float32_def.constraints is None

    def test_get_json_schema(self) -> None:
        """Test getting JSON Schema overrides."""
        uint8_def = AbstractTypeRegistry.TYPES["UINT8"]
        float32_def = AbstractTypeRegistry.TYPES["FLOAT32"]

        assert uint8_def.json_schema_override is None  # No override, uses constraints
        assert float32_def.json_schema_override == {"type": "number"}

    def test_get_target_type_nonexistent(self) -> None:
        """Test getting mappings for non-existent targets."""
        uint8_def = AbstractTypeRegistry.TYPES["UINT8"]
        assert uint8_def.target_mappings.get("nonexistent") is None

    def test_dispatcher_unknown_type(self) -> None:
        """Test that dispatcher raises error for unknown types."""
        with pytest.raises(ValueError, match="Unknown abstract type: UNKNOWN"):
            AbstractType["UNKNOWN"]  # type: ignore[misc]


class TestConcreteTypes:
    """Test the concrete NewType instances."""

    def test_all_types_accessible(self) -> None:
        """Test that all expected types can be resolved to their abstract type definitions."""
        expected_types = [
            (UInt8, "UINT8"),
            (UInt16, "UINT16"),
            (UInt32, "UINT32"),
            (Int8, "INT8"),
            (Int32, "INT32"),
            (Int64, "INT64"),
            (Float32, "FLOAT32"),
            (Float64, "FLOAT64"),
        ]
        for concrete_type, expected_type_name in expected_types:
            abstract_def = get_abstract_type(concrete_type)
            expected_def = AbstractTypeRegistry.TYPES[expected_type_name]
            assert abstract_def == expected_def

    def test_get_abstract_type(self) -> None:
        """Test getting abstract type definition from concrete type."""
        uint8_def = get_abstract_type(UInt8)
        int32_def = get_abstract_type(Int32)
        float64_def = get_abstract_type(Float64)

        assert uint8_def == AbstractTypeRegistry.TYPES["UINT8"]
        assert int32_def == AbstractTypeRegistry.TYPES["INT32"]
        assert float64_def == AbstractTypeRegistry.TYPES["FLOAT64"]

    def test_get_target_type(self) -> None:
        """Test getting target type from concrete type."""
        assert get_target_type(UInt8, "scala") == "Byte"
        assert get_target_type(Int32, "spark") == "IntegerType"
        assert get_target_type(Float32, "parquet") == "FLOAT"

    def test_get_target_type_unknown_type(self) -> None:
        """Test getting target type for unknown concrete type."""
        assert get_target_type(str, "scala") is None

    def test_get_target_type_unknown_language(self) -> None:
        """Test getting unknown target type."""
        assert get_target_type(UInt8, "unknown") is None


class TestValidation:
    """Test validation behavior of abstract types."""

    def test_uint8_validation(self) -> None:
        """Test UInt8 validation constraints."""

        class TestModel(BaseModel):
            value: UInt8

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
            value: Int32

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
        """Test optional abstract type fields."""

        class TestModel(BaseModel):
            required_value: UInt8
            optional_value: UInt16 | None = None

        # Valid with both fields
        model = TestModel(required_value=100, optional_value=1000)
        assert model.required_value == 100
        assert model.optional_value == 1000

        # Valid with only required field
        model = TestModel(required_value=50)
        assert model.required_value == 50
        assert model.optional_value is None

    def test_float_types(self) -> None:
        """Test float abstract types."""

        class TestModel(BaseModel):
            f32: Float32
            f64: Float64

        model = TestModel(f32=3.14, f64=2.71828)
        assert model.f32 == 3.14
        assert model.f64 == 2.71828

    def test_conflicting_validation_criteria(self) -> None:
        """Test that Field constraints closest to use take precedence over abstract type constraints."""
        from typing import Annotated

        from pydantic import Field

        # Int32 has built-in constraints: ge=-(2**31), le=2**31-1
        # But we'll add more restrictive constraints that should win
        class TestModelRestrictive(BaseModel):
            # This should use le=5 instead of the Int32's le=2**31-1
            value: Annotated[Int32, Field(le=5)]

        # Valid values within the more restrictive bound
        assert TestModelRestrictive(value=0).value == 0
        assert TestModelRestrictive(value=5).value == 5
        assert TestModelRestrictive(value=-5).value == -5

        # Should fail with the more restrictive constraint (le=5), not the abstract type constraint
        with pytest.raises(ValidationError) as exc_info:
            TestModelRestrictive(value=6)

        # Verify the error message references the closer constraint (le=5), not Int32's constraint
        error_msg = str(exc_info.value)
        assert "less than or equal to 5" in error_msg

        # Test with less restrictive constraints that should still be overridden
        class TestModelPermissive(BaseModel):
            # Int32 has ge=-(2**31) but we set ge=-10, so ge=-10 should win
            value: Annotated[Int32, Field(ge=-10)]

        # Valid with the closer constraint
        assert TestModelPermissive(value=-10).value == -10
        assert TestModelPermissive(value=0).value == 0

        # Should fail with the closer constraint (ge=-10), not the abstract type constraint
        with pytest.raises(ValidationError) as exc_info:
            TestModelPermissive(value=-11)

        error_msg = str(exc_info.value)
        assert "greater than or equal to -10" in error_msg

        # Test multiple overlapping constraints - closest should win
        class TestModelMultiple(BaseModel):
            # Multiple Field annotations - the outermost (closest to use) should win
            value: Annotated[Int32, Field(ge=0), Field(le=10)]

        # Valid within all constraints
        assert TestModelMultiple(value=5).value == 5
        assert TestModelMultiple(value=0).value == 0
        assert TestModelMultiple(value=10).value == 10

        # Should fail the closest constraints
        with pytest.raises(ValidationError):
            TestModelMultiple(value=-1)  # violates ge=0
        with pytest.raises(ValidationError):
            TestModelMultiple(value=11)  # violates le=10
