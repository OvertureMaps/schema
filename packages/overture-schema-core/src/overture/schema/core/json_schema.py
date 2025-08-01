from types import UnionType
from typing import Any, get_origin

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import core_schema

from ._cache import get_type_adapter


class OptionalWithoutDefaultGenerator(GenerateJsonSchema):
    """Simplify the generated JSON Schema for nullable fields by removing null from anyOf."""

    def default_schema(self, schema: core_schema.WithDefaultSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema with a default value.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        # Special case: For nullable fields (X | None), remove null from anyOf
        # and preserve non-None defaults, treating all as truly optional fields
        if schema.get("schema", {}).get("type") == "nullable":
            json_schema = self.generate_inner(schema["schema"])
            # Remove null from anyOf to make field truly optional
            json_schema["anyOf"] = [
                x for x in json_schema["anyOf"] if x.get("type") != "null"
            ]

            if len(json_schema["anyOf"]) == 1:
                json_schema = json_schema["anyOf"][0]

            # preserve non-None defaults
            default = self.get_default_value(schema)
            if default is not None:
                json_schema["default"] = default

            return json_schema

        # For all other cases, use parent implementation
        return super().default_schema(schema)


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
        return models.model_json_schema(
            schema_generator=OptionalWithoutDefaultGenerator
        )

    if get_origin(models) is not None:
        adapter = get_type_adapter(models)
        return adapter.json_schema(schema_generator=OptionalWithoutDefaultGenerator)

    raise TypeError(f"Expected BaseModel or union type, got {type(models)}")
