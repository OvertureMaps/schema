r"""
Foundational types at the base of the Overture schema system.

A set of primitive types, constraint rules, and Pydantic base model classes that
can be used to create strongly-typed, predictably validated, data.

Subpackages
-----------
- :mod:`primitive <overture.schema.system.primitive>` Primitive data types, including numeric and
  geometry types.
- :mod:`field_constraint <overture.schema.system.field_constraint>` Constraints that can be
  annotated onto Pydantic model fields to force them to conform to well-known rules, for example "a
  collection that contains unique items" or "a string that is a valid country code".
- :mod:`model_constraint <overture.schema.system.model_constraint>` Constraints that can be
  decorated onto Pydantic model classes to add cross-field validation rules, for example "these two
  fields are mutually-exclusive" or "if this field is set, then that field must also be set".
- :mod:`string <overture.schema.system.string>` String types with built-in validation to conform to
  well-known patterns, for example a country code, a hexadecimal color code, a language tag, or just
  a string that doesn't contain whitespace.


Features
--------
- Integrates with Overture code generation tools, making Pydantic models built using these types
  portable across different programming languages (*e.g.*, Java) and serialization formats (*e.g.*,
  Parquet.)
- Tightly integrated with Pydantic's JSON Schema system, providing rich JSON Schemas and maximum
  parity between Pydantic, generated JSON Schemas, and Overture's code generation tools.
- First-class support for geospatial data using the geometry primitives.
- Conditional fields and validation on relationships between fields (*e.g.*, if the type field
  contains "region", then region code field must also be set).
- Constraint rules produce detailed and consistent error messages with useful domain knowledge.

Examples
--------
Make a simple Pydantic model using the fundamental types from this package and verify that it
rejects invalid input:

>>> from pydantic import BaseModel, ValidationError
>>> from overture.schema.system.primitive import uint32;
>>> from overture.schema.system.string import SnakeCaseString;
>>> class MyModel(BaseModel):
...     index: uint32
...     id: SnakeCaseString
>>> try:
...     MyModel(index=-1, id="FooBar")  # Index is not a valid uint32 (negative), "FooBar" is not snake_case
... except ValidationError:
...    print("Validation failed")
Validation failed

Valid inputs to the same model are accepted:

>>> from pydantic import BaseModel, ValidationError
>>> from overture.schema.system.primitive import uint32;
>>> from overture.schema.system.string import SnakeCaseString;
>>> class MyModel(BaseModel):
...     index: uint32
...     id: SnakeCaseString
>>> my_model = MyModel(index=42, id="foo_bar")
>>> assert my_model.index == 42
>>> assert my_model.id == "foo_bar"

Combine Overture and Pydantic constraints on a single field:

>>> from typing import Annotated
>>> from pydantic import BaseModel, Field
>>> from overture.schema.system.field_constraint import UniqueItemsConstraint
>>> class MyModel(BaseModel):
...    # Unique tags: at least one is required, at most 10 are allowed.
...    tags: Annotated[
...             list[str],
...             UniqueItemsConstraint()
...          ] = Field(..., min_length=1, max_length=10, description="Unique tags")

Create a custom regular expression pattern constraint:

>>> from overture.schema.system.field_constraint import PatternConstraint
>>> OsmIdConstraint = PatternConstraint(
...     pattern=r"^[nwr]\d+$",
...     error_message="Invalid OSM ID format: {value}. Must be n123, w123, or r123."
... )
>>>
>>> from pydantic import BaseModel, Field
>>> class MyModel(BaseModel):
...     osm_id: Annotated[str, OsmIdConstraint] = Field(..., description="OSM entity ID")
>>>
>>> from pydantic import ValidationError
>>> try:
...    MyModel(**{"osm_id": "foo"})
... except ValidationError as e:
...    assert "Invalid OSM ID format: foo. Must be n123, w123, or r123." in str(e)
...    print("Validation failed")
Validation failed

Use decorators to add complex multi-field constraints. In this example, a validation rule is added
saying that at least one of the two optional fields is required to have an explicit value, but
they aren't both required to:

>>> from pydantic import BaseModel, ValidationError
>>> from overture.schema.system.model_constraint import require_any_of
>>>
>>> @require_any_of("foo", "bar")
... class MyModel(BaseModel):
...     foo: int | None = None
...     bar: str | None = None
...
>>> MyModel(foo=42, bar="hello")    # validates OK
MyModel(foo=42, bar='hello')
>>> MyModel(foo=42)                 # validates OK
MyModel(foo=42, bar=None)
>>> MyModel(bar="hello")            # validates OK
MyModel(foo=None, bar='hello')
>>> MyModel(foo=None, bar=None)     # validates OK because foo and bar are explicitly set to `None`
MyModel(foo=None, bar=None)
>>>
>>> try:
...     MyModel()
... except ValidationError as e:
...    assert "at least one of these fields must be explicitly set, but none are: foo, bar" in str(e)
...    print("Validation failed")
Validation failed
"""

from . import field_constraint, metadata, model_constraint, primitive, string
from .create_model import create_model

__all__ = [
    "create_model",
    "field_constraint",
    "metadata",
    "model_constraint",
    "primitive",
    "string",
]
