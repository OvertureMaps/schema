from types import UnionType
from typing import Any, get_origin

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import core_schema

from ._cache import get_type_adapter


# TODO: Vic - I think we can remove this once `Omitable[T]` is applied everywhere (and once the
#             @model_constraints are made `Omitable`-aware).
class EnhancedJsonSchemaGenerator(GenerateJsonSchema):
    """
    Enhanced JSON Schema generator with optional field support.

    This generator enhances the default Pydantic generator with the following:

    - Optional field handling: simplifies nullable fields by removing null from anyOf
      and removing null defaults to make fields truly optional.
    """

    def nullable_schema(self, schema: core_schema.NullableSchema) -> JsonSchemaValue:
        """
        Generate a JSON schema that matches a nullable schema.

        Parameters
        ----------
        schema : core_schema.NullableSchema
            The core schema for which to generate a JSON schema

        Return
        ------
        JsonSchemaValue
            The generated JSON schema
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

    Parameters
    ----------
    models : type[BaseModel] | UnionType | type
        Either a class that is a subclass of Pydantic's `BaseModel` class or a union type (possibly
        annotated with discriminator information) representing a union of `BaseModel` classes.

    Returns
    -------
    dict[str, Any]
        JSON schema representation of the model(s).

    Raises
    ------
    TypeError
        If `models` is not a subclass of `BaseModel` or a union of such classes
    """
    if isinstance(models, type) and issubclass(models, BaseModel):
        return models.model_json_schema(schema_generator=EnhancedJsonSchemaGenerator)

    if get_origin(models) is not None:
        adapter = get_type_adapter(models)
        return adapter.json_schema(schema_generator=EnhancedJsonSchemaGenerator)

    raise TypeError(
        f"`models` must be a subclass of `BaseModel` or a union of such subclasses, but {repr(models)} is a `{type(models).__name__}`"
    )
