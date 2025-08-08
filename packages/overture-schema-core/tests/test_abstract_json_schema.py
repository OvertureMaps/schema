"""Tests for JSON Schema generation with abstract types."""

from overture.schema.core.json_schema import json_schema
from overture.schema.core.types.abstract import (
    Float32,
    Float64,
    Int32,
    UInt8,
)
from pydantic import BaseModel


class TestAbstractTypeJSONSchema:
    """Test JSON Schema generation for models using abstract types."""

    def test_uint8_json_schema(self) -> None:
        """Test JSON Schema generation for UInt8 fields."""

        class TestModel(BaseModel):
            value: UInt8
            optional_value: UInt8 | None = None

        schema = json_schema(TestModel)

        # Check required field
        value_prop = schema["properties"]["value"]
        assert value_prop["type"] == "integer"
        assert value_prop["minimum"] == 0
        assert value_prop["maximum"] == 255

        # Check optional field
        optional_prop = schema["properties"]["optional_value"]
        assert optional_prop["type"] == "integer"
        assert optional_prop["minimum"] == 0
        assert optional_prop["maximum"] == 255
        assert "default" not in optional_prop  # Should be truly optional

        # Check required fields
        assert schema["required"] == ["value"]

    def test_int32_json_schema(self) -> None:
        """Test JSON Schema generation for Int32 fields."""

        class TestModel(BaseModel):
            value: Int32

        schema = json_schema(TestModel)

        value_prop = schema["properties"]["value"]
        assert value_prop["type"] == "integer"
        assert value_prop["minimum"] == -(2**31)
        assert value_prop["maximum"] == 2**31 - 1

    def test_float_types_json_schema(self) -> None:
        """Test JSON Schema generation for Float32 and Float64."""

        class TestModel(BaseModel):
            f32: Float32
            f64: Float64

        schema = json_schema(TestModel)

        # Float32 should have explicit type override
        f32_prop = schema["properties"]["f32"]
        assert f32_prop["type"] == "number"

        # Float64 should have explicit type override
        f64_prop = schema["properties"]["f64"]
        assert f64_prop["type"] == "number"

    def test_mixed_abstract_types_json_schema(self) -> None:
        """Test JSON Schema generation for model with mixed abstract types."""

        class MixedModel(BaseModel):
            id: UInt8
            score: Float32
            count: Int32 | None = None

        schema = json_schema(MixedModel)

        # Verify all properties exist
        expected_props = {"id", "score", "count"}
        assert set(schema["properties"].keys()) == expected_props

        # Verify required fields
        assert set(schema["required"]) == {"id", "score"}

        # Spot check a few properties
        assert schema["properties"]["id"]["type"] == "integer"
        assert schema["properties"]["id"]["minimum"] == 0
        assert schema["properties"]["id"]["maximum"] == 255

        assert schema["properties"]["score"]["type"] == "number"

        # Optional field should not have default
        assert "default" not in schema["properties"]["count"]
