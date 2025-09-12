from overture.schema.core.json_schema import EnhancedJsonSchemaGenerator
from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema


class TestEnhancedJsonSchemaGenerator:
    """Test the EnhancedJsonSchemaGenerator class."""

    def test_nullable_with_none_default_becomes_optional(self) -> None:
        """Test that X | None = None becomes optional without default."""

        class TestModel(BaseModel):
            nullable_field: str | None = None
            required_field: str

        schema = TestModel.model_json_schema(
            schema_generator=EnhancedJsonSchemaGenerator
        )

        # The nullable_field should not appear in required fields
        assert "required" in schema
        assert "nullable_field" not in schema["required"]
        assert schema["required"] == ["required_field"]

        # The nullable_field should not have a default in its schema
        properties = schema["properties"]
        assert "default" not in properties["nullable_field"]

        # The nullable_field should be a string type (not anyOf with null)
        nullable_field_schema = properties["nullable_field"]
        assert nullable_field_schema["type"] == "string"
        assert "anyOf" not in nullable_field_schema

    def test_nullable_with_other_default_keeps_default(self) -> None:
        """Test that X | None = 'value' keeps the default value."""

        class TestModel(BaseModel):
            nullable_field: str | None = "default_value"

        schema = TestModel.model_json_schema(
            schema_generator=EnhancedJsonSchemaGenerator
        )

        properties = schema["properties"]
        nullable_field_schema = properties["nullable_field"]

        # Should have the default value preserved and be simplified to string type
        assert nullable_field_schema["default"] == "default_value"
        assert nullable_field_schema["type"] == "string"
        assert "anyOf" not in nullable_field_schema

    def test_regular_defaults_preserved(self) -> None:
        """Test that regular non-nullable defaults are preserved."""

        class TestModel(BaseModel):
            string_field: str = "default"
            int_field: int = 42
            bool_field: bool = True

        schema = TestModel.model_json_schema(
            schema_generator=EnhancedJsonSchemaGenerator
        )

        properties = schema["properties"]

        assert properties["string_field"]["default"] == "default"
        assert properties["int_field"]["default"] == 42
        assert properties["bool_field"]["default"] is True

    def test_required_fields_unchanged(self) -> None:
        """Test that required fields without defaults are unchanged."""

        class TestModel(BaseModel):
            required_str: str
            required_int: int
            optional_with_none: str | None = None

        schema = TestModel.model_json_schema(
            schema_generator=EnhancedJsonSchemaGenerator
        )

        assert schema["required"] == ["required_str", "required_int"]

        properties = schema["properties"]
        assert "default" not in properties["required_str"]
        assert "default" not in properties["required_int"]
        assert "default" not in properties["optional_with_none"]

    def test_comparison_with_standard_generator(self) -> None:
        """Test behavior differs from standard GenerateJsonSchema."""

        class TestModel(BaseModel):
            nullable_field: str | None = None

        # Standard generator schema
        standard_schema = TestModel.model_json_schema(
            schema_generator=GenerateJsonSchema
        )

        # Our custom generator schema
        custom_schema = TestModel.model_json_schema(
            schema_generator=EnhancedJsonSchemaGenerator
        )

        # Standard should have default: null
        standard_field = standard_schema["properties"]["nullable_field"]
        assert standard_field["default"] is None
        assert "anyOf" in standard_field

        # Custom should not have default and should be simple string type
        custom_field = custom_schema["properties"]["nullable_field"]
        assert "default" not in custom_field
        assert custom_field["type"] == "string"
        assert "anyOf" not in custom_field

    def test_multiple_nullable_fields(self) -> None:
        """Test handling of multiple nullable fields with None defaults."""

        class TestModel(BaseModel):
            opt_str: str | None = None
            opt_int: int | None = None
            opt_bool: bool | None = None
            required_field: str

        schema = TestModel.model_json_schema(
            schema_generator=EnhancedJsonSchemaGenerator
        )

        assert schema["required"] == ["required_field"]

        properties = schema["properties"]

        # All optional fields should be simple types without defaults
        assert properties["opt_str"]["type"] == "string"
        assert "default" not in properties["opt_str"]

        assert properties["opt_int"]["type"] == "integer"
        assert "default" not in properties["opt_int"]

        assert properties["opt_bool"]["type"] == "boolean"
        assert "default" not in properties["opt_bool"]

    def test_complex_optional_types(self) -> None:
        """Test with more complex optional types."""

        class NestedModel(BaseModel):
            value: str

        class TestModel(BaseModel):
            opt_list: list[str] | None = None
            opt_dict: dict[str, str] | None = None
            opt_nested: NestedModel | None = None

        schema = TestModel.model_json_schema(
            schema_generator=EnhancedJsonSchemaGenerator
        )

        properties = schema["properties"]

        # All should be their base types without null and without defaults
        assert properties["opt_list"]["type"] == "array"
        assert "default" not in properties["opt_list"]

        assert properties["opt_dict"]["type"] == "object"
        assert "default" not in properties["opt_dict"]

        assert "$ref" in properties["opt_nested"]
        assert "default" not in properties["opt_nested"]

        # None should be in required
        assert "required" not in schema or len(schema["required"]) == 0

    def test_union_types_with_none_default(self) -> None:
        """Test union types like str | int | None = None."""

        class TestModel(BaseModel):
            union_field: str | int | None = None

        schema = TestModel.model_json_schema(
            schema_generator=EnhancedJsonSchemaGenerator
        )

        properties = schema["properties"]
        union_schema = properties["union_field"]

        # Should be anyOf without null type and without default
        assert "anyOf" in union_schema
        assert "default" not in union_schema

        # Should only contain string and integer, not null
        types = {item["type"] for item in union_schema["anyOf"]}
        assert types == {"string", "integer"}
        assert "null" not in types
