"""
JSON Schemas of Overture-based Pydantic models.
"""

from enum import Enum
from types import UnionType
from typing import Annotated, Any, Union, cast, get_args, get_origin

from pydantic import BaseModel, TypeAdapter
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import core_schema
from typing_extensions import override


class GenerateOmitNullableOptionalJsonSchema(GenerateJsonSchema):
    """
    Generates a JSON Schema in which optional values that allow `None` are omitted instead of being
    assigned a `null` value.

    Example
    -------
    >>> import json
    >>> from pydantic import BaseModel, Field
    >>>
    >>> class FooModel(BaseModel):
    ...     foo: str | None = None
    ...
    >>> print(json.dumps(FooModel.model_json_schema(
    ...     schema_generator=GenerateOmitNullableOptionalJsonSchema
    ... ), indent=2))
    {
      "properties": {
        "foo": {
          "title": "Foo",
          "type": "string"
        }
      },
      "title": "FooModel",
      "type": "object"
    }


    ⚠️ Warning
    ----------
    When using this class to generate a JSON Schema, you must dump your model JSON carefully to
    ensure that it matches the JSON Schema.

    When using `BaseModel.model_dump_json` or `TypeAdapter.dump_json`, use the argument
    `exclude_unset=True` to ensure unset optional fields are omitted from the dumped JSON. Failing
    to do so will result in JSON that includes explicit `null` values that the JSON Schema
    generated with this generator class does not allow, as shown below:

    >>> print(FooModel().model_dump_json())
    {"foo":null}
    >>> print(FooModel().model_dump_json(exclude_unset=True))
    {}

    Background
    ----------
    An optional field in Pydantic is a field with a default value. If a model field has a specified
    default value, the field does not need to be explicitly set on a model instance. Optional
    fields, and only optional fields, can be "unset" in a Pydantic model.

    A nullable field in Pydantic is a field that can hold the value `None`.

    A field may be optional only, nullable only, or both optional and nullable (or neither).

    The default Pydantic behavior for nullable optional fields is to give them a JSON Schema in
    which the field may hold the JSON literal value `null`.

    >>> FooModel.model_fields['foo'].is_required()
    False
    >>> FooModel().model_fields_set
    set()
    >>> FooModel(foo='bar').model_fields_set
    {'foo'}
    >>> print(json.dumps(FooModel.model_json_schema(), indent=2))
    {
      "properties": {
        "foo": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Foo"
        }
      },
      "title": "FooModel",
      "type": "object"
    }

    This default Pydantic behavior is reasonable, and aligns well with the Python internal
    representation. However, it doesn't take advantage of a quiet advantage of JSON and JSON Schema,
    which is that there's another concept of optionality that does not require the value `null` at
    all. In this paradigm, if the field is there, it has a set value; and if the field is missing,
    it does not. Pydantic does enable this alternative paradigm via the experimental `MISSING`
    sentinel, but this sentinel is not yet a full-fledged feature and has some rough edges.

    The purpose of this class is to generate a JSON Schema that aligns with the alternative paradigm
    where nullable optional fields are omitted from the JSON rather than assigned the literal value
    `null`.

    Transformations
    ---------------
    This class makes the following changes to the default Pydantic JSON Schema for nullable optional
    fields only:

    1. The JSON Schema type `null` is removed as an allowed type from the field's schema, which will
       usually result in eliminating the `"anyOf"` composition keyword from the field's schema.
    2. If the field's default value is `None` (JSON `null`), the default value is removed.
    """

    @override
    def default_schema(self, schema: core_schema.WithDefaultSchema) -> JsonSchemaValue:
        match GenerateOmitNullableOptionalJsonSchema._redact_nullable_schema(schema):
            case redacted if redacted and schema["default"] is None:
                return self.generate_inner(redacted["schema"])
            case redacted if redacted:
                return self.generate_inner(redacted)
            case _:
                return super().default_schema(schema)

    @staticmethod
    def _redact_nullable_schema(
        schema: core_schema.CoreSchema,
    ) -> core_schema.CoreSchema | None:
        match schema.get("schema", None):
            case sub_schema if sub_schema and sub_schema["type"] == "nullable":
                return {**schema, "schema": sub_schema["schema"]}
            case sub_schema if sub_schema:
                redacted = (
                    GenerateOmitNullableOptionalJsonSchema._redact_nullable_schema(
                        sub_schema
                    )
                )
                return None if not redacted else {**schema, "schema": redacted}
            case _:
                return None


def json_schema(thing: object) -> JsonSchemaValue:
    """
    Generate JSON Schema for a Pydantic model or union of models.

    Parameters
    ----------
    thing : object
        Either a Pydantic model or a union of Pydantic models

    Returns
    -------
    JsonSchemaValue
        JSON Schema for the model or union of models

    Raises
    ------
    TypeError
        If `models` is not a Pydantic model or union of Pydantic models
    """
    match _Kind.of(thing):
        case _Kind.BASE_MODEL:
            return cast(BaseModel, thing).model_json_schema(
                schema_generator=GenerateOmitNullableOptionalJsonSchema
            )
        case _Kind.UNION:
            tap: TypeAdapter = TypeAdapter(thing)
            return tap.json_schema(
                schema_generator=GenerateOmitNullableOptionalJsonSchema
            )
        case _:
            raise TypeError(
                f"`models` must be a subclass of `BaseModel` or a union of subclasses of "
                f"`BaseModel`, but {repr(thing)} is a "
                f"`{thing.__name__ if isinstance(thing, type) else type(thing).__name__}`"
            )


class _Kind(str, Enum):
    BASE_MODEL = "base_model"
    UNION = "union"

    @staticmethod
    def of(thing: Any) -> Union["_Kind", None]:
        if isinstance(thing, type) and issubclass(thing, BaseModel):
            return _Kind.BASE_MODEL
        else:
            match get_origin(thing):
                case a if a is Annotated:
                    return _Kind.of(get_args(thing)[0])
                case u if (u is UnionType or u is Union) and _Kind._union_args(thing):
                    return _Kind.UNION
                case _:
                    return None

    @staticmethod
    def _union_args(thing: Any) -> bool:
        return all(
            _Kind.of(a) in [_Kind.BASE_MODEL, _Kind.UNION] for a in get_args(thing)
        )
