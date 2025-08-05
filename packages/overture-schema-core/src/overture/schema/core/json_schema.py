from types import UnionType
from typing import Any, get_origin

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import core_schema

from ._cache import get_type_adapter


class OptionalFieldGenerator(GenerateJsonSchema):
    """Simplify the generated JSON Schema for nullable fields by removing null from
    anyOf and removing null defaults."""

    def nullable_schema(self, schema: core_schema.NullableSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a nullable schema.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        # Generate the default nullable schema first
        json_schema = super().nullable_schema(schema)

        # Remove null from anyOf to make field truly optional
        if "anyOf" in json_schema:
            json_schema["anyOf"] = [
                x for x in json_schema["anyOf"] if x.get("type") != "null"
            ]

            if len(json_schema["anyOf"]) == 1:
                json_schema = json_schema["anyOf"][0]

        # Remove null defaults to make fields truly optional
        if json_schema.get("default") is None:
            json_schema.pop("default", None)

        return json_schema

    def model_field_schema(self, schema: core_schema.ModelField) -> JsonSchemaValue:
        """Override model field schema generation to remove null defaults."""
        json_schema = super().model_field_schema(schema)

        # Remove null defaults to make fields truly optional
        if json_schema.get("default") is None:
            json_schema.pop("default", None)

        return json_schema


def json_schema(models: type[BaseModel] | UnionType | type) -> dict[str, Any]:
    """Generate JSON schema for a Pydantic model or union of models.

    Args:
        models: Either a Pydantic BaseModel class or a union type (possibly
                annotated with discriminator information) of BaseModels.

    Returns:
        dict: JSON schema representation of the model(s).

    Raises:
        TypeError: If models is not a BaseModel or union type.
    """
    if isinstance(models, type) and issubclass(models, BaseModel):
        return models.model_json_schema(schema_generator=OptionalFieldGenerator)

    if get_origin(models) is not None:
        adapter = get_type_adapter(models)
        return adapter.json_schema(schema_generator=OptionalFieldGenerator)

    raise TypeError(f"Expected BaseModel or union type, got {type(models)}")
