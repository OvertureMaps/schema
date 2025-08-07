"""Example usage of abstract types in models."""

from overture.schema.core.json_schema import json_schema
from overture.schema.core.types.abstract import (
    Float32,
    Int32,
    UInt8,
    get_target_type,
)
from pydantic import BaseModel, Field


class ExampleBuilding(BaseModel):
    """Example building feature using abstract data types."""

    # Direct usage of abstract types (recommended)
    height: Float32 | None = Field(None, description="Height of building in meters")

    num_floors: UInt8 | None = Field(None, description="Number of floors in building")

    area: Int32 | None = Field(None, description="Floor area in square meters")


def test_example_model_creation() -> None:
    """Test creating instances of the example model."""

    # Test with all fields
    building = ExampleBuilding(
        height=45.5, num_floors=12, area=2500, name="Example Tower"
    )

    assert building.height == 45.5
    assert building.num_floors == 12
    assert building.area == 2500

    # Test with partial fields
    building2 = ExampleBuilding(height=30.0, name="Small Building")
    assert building2.height == 30.0
    assert building2.num_floors is None
    assert building2.area is None


def test_example_model_validation() -> None:
    """Test validation constraints work correctly."""

    # Valid values
    building = ExampleBuilding(num_floors=50)
    assert building.num_floors == 50

    # Invalid values should raise validation errors
    try:
        ExampleBuilding(num_floors=256)  # > UInt8 max
        raise AssertionError("Should have raised validation error")
    except Exception:
        pass  # Expected

    try:
        ExampleBuilding(num_floors=-1)  # < UInt8 min
        raise AssertionError("Should have raised validation error")
    except Exception:
        pass  # Expected


def test_json_schema_generation() -> None:
    """Test JSON Schema generation for the example model."""

    schema = json_schema(ExampleBuilding)

    # Check that all fields are present and optional
    properties = schema["properties"]
    assert "height" in properties
    assert "num_floors" in properties
    assert "area" in properties

    # All fields should be optional
    assert schema.get("required", []) == []

    # Check types and constraints
    assert properties["height"]["type"] == "number"

    assert properties["num_floors"]["type"] == "integer"
    assert properties["num_floors"]["minimum"] == 0
    assert properties["num_floors"]["maximum"] == 255

    assert properties["area"]["type"] == "integer"
    assert properties["area"]["minimum"] == -(2**31)
    assert properties["area"]["maximum"] == 2**31 - 1


def test_language_mappings() -> None:
    """Test getting target language types from the model fields."""

    # Get Scala types
    assert get_target_type(Float32, "scala") == "Float"
    assert get_target_type(UInt8, "scala") == "Byte"
    assert get_target_type(Int32, "scala") == "Int"

    # Get Spark types
    assert get_target_type(Float32, "spark") == "FloatType"
    assert get_target_type(UInt8, "spark") == "ByteType"
    assert get_target_type(Int32, "spark") == "IntegerType"

    # Get Parquet types
    assert get_target_type(Float32, "parquet") == "FLOAT"
    assert get_target_type(UInt8, "parquet") == "INT32"  # Promoted
    assert get_target_type(Int32, "parquet") == "INT32"


def test_model_serialization() -> None:
    """Test model serialization works correctly."""

    building = ExampleBuilding(height=100.5, num_floors=25, area=5000)

    # Test Python dict serialization
    data = building.model_dump()
    expected = {
        "height": 100.5,
        "num_floors": 25,
        "area": 5000,
    }
    assert data == expected

    # Test JSON serialization
    json_str = building.model_dump_json()
    assert '"height":100.5' in json_str
    assert '"num_floors":25' in json_str
    assert '"area":5000' in json_str


if __name__ == "__main__":
    # Run example usage
    print("Creating example building...")
    building = ExampleBuilding(height=75.0, num_floors=20, area=3500)
    print(f"Building: {building}")

    print("\nGenerating JSON Schema...")
    schema = json_schema(ExampleBuilding)
    print(f"Schema properties: {list(schema['properties'].keys())}")

    print("\nLanguage mappings:")
    print(f"  Float32 -> Scala: {get_target_type(Float32, 'scala')}")
    print(f"  UInt8 -> Spark: {get_target_type(UInt8, 'spark')}")
    print(f"  Int32 -> Parquet: {get_target_type(Int32, 'parquet')}")
