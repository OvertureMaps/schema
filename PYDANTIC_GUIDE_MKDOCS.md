# Overture Maps Pydantic Schema Guide

This guide helps you work with Overture Maps Pydantic schemas - Python models that define geospatial data structures with automatic validation. Whether you're new to Pydantic or migrating from JSON Schema, this guide provides a progressive learning path from basics to advanced patterns.

## Table of Contents

- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
    - [Models and Inheritance](#models-and-inheritance)
    - [Field Types](#field-types)
    - [Field Enhancement](#field-enhancement)
    - [Collections and Lists](#collections-and-lists)
    - [Enumerations](#enumerations)
- [Advanced Patterns](#advanced-patterns)
    - [Relationship Patterns](#relationship-patterns)
    - [Discriminated Unions](#discriminated-unions)
    - [Pattern Properties (Constrained Key-Value Maps)](#pattern-properties-constrained-key-value-maps)
    - [Nested List Validation](#nested-list-validation)
    - [Type Aliases for Reusable Patterns](#type-aliases-for-reusable-patterns)
- [Integration Guide](#integration-guide)
    - [Project Architecture](#project-architecture)
    - [Migrating from JSON Schema](#migrating-from-json-schema)
- [Reference](#reference)
    - [Complete Templates](#complete-templates)
    - [Quick Reference](#quick-reference)

---

# Quick Start

### Essential Imports

Copy what you need for most models:

```python
# Basic Python types
from typing import Annotated, Literal
from enum import Enum

# Pydantic essentials
from pydantic import BaseModel, Field

# Overture core models
from overture.schema.core import OvertureFeature
from overture.schema.system.primitive import Geometry, GeometryType, GeometryTypeConstraint

# Validation system
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields

# Common types
from overture.schema.system.string import (
    CountryCodeAlpha2,
    NoWhitespaceString,
    StrippedString,
)
from overture.schema.core.types import (
    ConfidenceScore,
    LanguageTag,
)

# Numeric primitives (use these instead of int/float)
from overture.schema.system.primitive import (
    int8, int32, int64,
    uint8, uint16, uint32,
    float32, float64
)
```

### Basic Model Template

```python
from typing import Annotated
from pydantic import BaseModel, Field
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.primitive import int8, float64

@no_extra_fields
class MyCustomType(BaseModel):
    """Brief description of what this represents."""

    # Required fields (no default value)
    name: str
    category: str

    # Optional fields (with None default)
    description: str | None = None

    # Field with constraints and description
    priority: Annotated[
        int8 | None,
        Field(
            ge=1,
            le=10,
            description="Priority level from 1 (lowest) to 10 (highest)"
        )
    ] = None
```

### Feature Template

```python
from typing import Annotated, Literal
from pydantic import Field
from overture.schema.core import OvertureFeature
from overture.schema.system.primitive import Geometry, GeometryType, GeometryTypeConstraint

class MyFeature(OvertureFeature[Literal["my_theme"], Literal["my_type"]]):
    """Description of what this feature represents."""

    # Geometry with constraints
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POINT),
        Field(description="Location of this feature"),
    ]

    # Custom fields
    my_field: str | None = None
```

# Core Concepts

## Models and Inheritance

Overture Maps Pydantic schemas are based on Python classes. You define a schema by creating a class that inherits from `pydantic.BaseModel`. For example:

```python
from pydantic import BaseModel

class Location(BaseModel):
    latitude: float
    longitude: float
```

### Inheritance

Schemas can inherit from other schemas, allowing you to build complex data models. For example:

```python
class Place(Location):
    name: str
    description: str = None
```

## Field Types

Pydantic provides a variety of field types that you can use in your schemas. Some common ones include:

- `str`: String type
- `int`: Integer type
- `float`: Floating-point number
- `bool`: Boolean type
- `list`: List type
- `dict`: Dictionary type

You can also use `Optional` to indicate that a field is optional:

```python
from typing import Optional

class User(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
```

## Field Enhancement

Pydantic allows you to enhance fields with additional validation and metadata. Some common enhancements include:

- `title`: A short title for the field
- `description`: A longer description of the field
- `default`: A default value for the field
- `example`: An example value for the field

For example:

```python
class Product(BaseModel):
    id: int
    name: str
    price: float = Field(..., gt=0, description="The price must be greater than zero")
```

## Collections and Lists

You can define fields that are lists or other collections. For example:

```python
from typing import List

class Order(BaseModel):
    id: int
    products: List[Product]
```

Pydantic will validate that the `products` field is a list of `Product` items.

## Enumerations

Enumerations (enums) are a way to define a set of named values. Pydantic supports enums out of the box. For example:

```python
from enum import Enum

class Status(Enum):
    active = "active"
    inactive = "inactive"
    pending = "pending"
```

You can use enums as field types in your schemas:

```python
class User(BaseModel):
    id: int
    name: str
    status: Status
```

# Advanced Patterns

## Relationship Patterns

Pydantic schemas can represent complex relationships between data, such as one-to-many and many-to-many relationships. For example:

```python
class Author(BaseModel):
    id: int
    name: str

class Book(BaseModel):
    id: int
    title: str
    author: Author
```

## Discriminated Unions

Discriminated unions allow you to define a field that can be one of several types. For example:

```python
from typing import Union

class Circle(BaseModel):
    radius: float

class Square(BaseModel):
    side: float

Shape = Union[Circle, Square]

class Drawing(BaseModel):
    id: int
    shape: Shape
```

## Pattern Properties (Constrained Key-Value Maps)

Pydantic allows you to define patterns for the keys and values in a dictionary. For example:

```python
from pydantic import constr

class Metadata(BaseModel):
    __root__: dict[constr(regex=r'^\w+$'), str]
```

This schema defines a dictionary with string keys that match the given regex pattern.

## Nested List Validation

Pydantic can validate nested lists and other complex structures. For example:

```python
class Team(BaseModel):
    name: str
    members: List[User]
```

## Type Aliases for Reusable Patterns

You can define type aliases for commonly used patterns to make your schemas more concise and readable. For example:

```python
from typing import NewType

PositiveInt = NewType('PositiveInt', int)

class Product(BaseModel):
    id: PositiveInt
    name: str
```

# Integration Guide

## Project Architecture

When integrating Overture Maps Pydantic schemas into your project, consider the following architecture:

```
your_project/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── models.py
│
└── requirements.txt
```

- Place your Pydantic schemas in the `models.py` file.
- Use the `main.py` file to run your application and import the schemas as needed.

## Migrating from JSON Schema

If you're migrating from JSON Schema, here are some tips to help you transition to Pydantic:

- JSON Schema `type` keywords map to Pydantic field types (e.g., `string`, `number`, `boolean`).
- JSON Schema `properties` map to Pydantic model attributes.
- JSON Schema `required` keywords map to Pydantic required fields.
- JSON Schema `items` for arrays map to Pydantic list item types.

# Reference

## Complete Templates

For a complete list of Pydantic field types, validators, and configuration options, refer to the [Pydantic documentation](https://pydantic-docs.helpmanual.io/).

## Quick Reference

Here's a quick reference for some common Pydantic field types and their JSON Schema equivalents:

| JSON Schema Type | Pydantic Field Type |
|------------------|---------------------|
| `string`         | `str`               |
| `number`         | `float`             |
| `integer`        | `int`               |
| `boolean`        | `bool`              |
| `array`          | `List[...]`         |
| `object`         | `dict[...]`         |

For more details, consult the [Pydantic documentation](https://pydantic-docs.helpmanual.io/).
