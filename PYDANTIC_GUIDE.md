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

## Quick Start

### Essential Imports

Copy what you need for most models:

```python
# Basic Python types
from typing import Annotated, Literal
from enum import Enum

# Pydantic essentials
from pydantic import BaseModel, Field

# Overture core models
from overture.schema.core import Feature
from overture.schema.core.models import StrictBaseModel
from overture.schema.core.geometry import Geometry, GeometryType, GeometryTypeConstraint

# Validation system
from overture.schema.validation import UniqueItemsConstraint

# Common types
from overture.schema.core.types import (
    ConfidenceScore,
    CountryCode,
    LanguageTag,
    NoWhitespaceString,
    TrimmedString
)

# Numeric primitives (use these instead of int/float)
from overture.schema.core.primitives.numeric import (
    int8, int32, int64,
    uint8, uint16, uint32,
    float32, float64
)
```

### Basic Model Template

```python
from typing import Annotated
from pydantic import Field
from overture.schema.core.models import StrictBaseModel
from overture.schema.core.primitives.numeric import int8, float64

class MyCustomType(StrictBaseModel):
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
from overture.schema.core import Feature
from overture.schema.core.geometry import Geometry, GeometryType, GeometryTypeConstraint

class MyFeature(Feature[Literal["my_theme"], Literal["my_type"]]):
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

---

## Core Concepts

### Models and Inheritance

#### What are Pydantic models?

Pydantic models are Python classes that define data structures and their constraints. Think of them like UML classes with built-in data validation - each model defines what fields are allowed and what types of data they can contain.

#### Model Base Classes and Inheritance

**What is a "base class"?** A base class defines common fields and behaviors that other classes can reuse. Think of it like a slide template - you create one layout, then make specific slides that use that structure.

**What is "inheritance"?** Inheritance means one class automatically gets all the fields and behaviors from another class. If Building inherits from Feature, it automatically gets all of Feature's fields (like `id`, `geometry`) plus any new fields you add to Building (like `height`). When multiple parent classes have the same field name, Python uses a [specific order](https://docs.python.org/3/tutorial/classes.html#multiple-inheritance) to determine which one takes precedence.

**StrictBaseModel** - Use for structured data components that should reject unknown fields:

```python
from overture.schema.core.models import StrictBaseModel

class Address(StrictBaseModel):
    """A postal address - no extra fields allowed."""
    street: str
    city: str
    postal_code: str | None = None
    # Any field not defined here will cause validation to fail
```

**Feature[ThemeT, TypeT]** - A generic base class for all geospatial features with typed theme and type parameters:

```python
from typing import Literal
from overture.schema.core import Feature
from overture.schema.core.primitives import float64

class Building(Feature[Literal["buildings"], Literal["building"]]):
    """A building feature with strongly-typed theme and type."""
    # Inherits: id, theme, type, geometry, bbox, version, sources
    height: float64 | None = None
```

**What does "generic" mean?** The `Feature[ThemeT, TypeT]` syntax makes Feature a "generic" class - think of it like a template that can be customized with specific values. The square brackets `[]` contain "type parameters" that specify exactly what theme and type this feature represents.

**What are ThemeT and TypeT?** These are placeholders for specific text values:

- **ThemeT**: The data theme (like "buildings", "places", "transportation")
- **TypeT**: The specific feature type within that theme (like "building", "place", "segment")

**What is `Literal`?** `Literal` means the field must be exactly one of the specified values - nothing else is allowed. So `Literal["buildings"]` means this theme can only be "buildings", not any other string.

By specifying `Feature[Literal["buildings"], Literal["building"]]`, you're saying "this is a Feature that must have theme='buildings' and type='building'" - no other values are allowed. This prevents mistakes like accidentally creating a building with theme="places".

#### Inheritance Patterns

**Multiple inheritance** combines fields from several base classes:

```python
from typing import Literal
from overture.schema.core import Feature
from overture.schema.core.models import Named, Stacked
from overture.schema.core.primitives import float64

class Building(Feature[Literal["buildings"], Literal["building"]], Named, Stacked):
    # Gets fields from Feature: id, theme, type, geometry, etc.
    # Gets fields from Named: names
    # Gets fields from Stacked: level
    # Plus its own fields:
    height: float64 | None = None
```

#### Field Aliases

Sometimes you need a field name that conflicts with Python keywords or conventions (hint: you'll get an error when you try to use it). Use `Field(alias="<data field name>")` to map between Python-friendly field names and the actual data field names:

```python
from typing import Annotated
from pydantic import Field

class Building(Feature):
    # Use class_ in Python code, but "class" in the actual data
    class_: Annotated[str | None, Field(alias="class")] = None

    # Other common cases might include:
    type_: Annotated[str | None, Field(alias="type")] = None  # if type conflicts
    from_: Annotated[str | None, Field(alias="from")] = None  # from is a keyword
```

A common example is `class_` with `Field(alias="class")` since "class" is a Python keyword but a common field name in data schemas.

### Field Types

#### Required vs Optional Fields

```python
class Building(Feature):
    # Required field (no default value)
    geometry: Geometry

    # Optional field (has default value of None)
    height: float64 | None = None
```

- **Required fields**: Must be provided when creating an instance
- **Optional fields**: Can be omitted; they have a default value (usually `None`)

> [!WARNING]
> **Always use `None` defaults** for optional fields. Non-`None` defaults create ambiguity between schema defaults and actual data values.

**Why do non-`None` defaults cause problems?**

1. **Data transformation ambiguity**: Pydantic adds default values that weren't in the input, making it impossible to distinguish between original data and schema defaults.

2. **Schema vs. data confusion**: Schemas serve multiple purposes:
   - **Validation only**: Check if existing data is valid (shouldn't transform it)
   - **Data processing**: Parse and potentially transform data with Pydantic
   - **Documentation**: Show developers what fields exist and what they mean

3. **Implicit semantic meaning**: Default values encode business logic into the schema, which should be in business logic instead.

**Better approaches:**

1. **Use `None` and document semantics:**

   ```python
   access_policy: Annotated[
       str | None,
       Field(description="Access policy for the place. When absent, assume 'open'")
   ] = None
   ```

2. **Always populate in data pipeline:**

   ```python
   # In your data processing pipeline, always set the value
   place.access_policy = place.access_policy or "open"
   ```

Keep the schema separate from business logic. The schema describes the shape of data, not the business rules about what missing values mean.

#### Numeric Primitives

**Always use specific numeric types instead of Python's generic `int`/`float`:**

```python
from overture.schema.core.primitives.numeric import (
    int8, int32, int64,        # Signed integers
    uint8, uint16, uint32,     # Unsigned integers
    float32, float64           # Floating point
)

class MyModel(StrictBaseModel):
    # Signed integers with specific ranges
    level: int8 | None = None           # -128 to 127
    year: int32 | None = None           # -2,147,483,648 to 2,147,483,647
    timestamp: int64 | None = None      # Full 64-bit range

    # Unsigned integers (0 and positive only)
    red_value: uint8 | None = None      # 0 to 255 (like RGB values)
    port: uint16 | None = None          # 0 to 65,535 (like network ports)
    population: uint32 | None = None    # 0 to 4,294,967,295

    # Floating point numbers
    height: float64 | None = None       # Double precision (recommended)
    ratio: float32 | None = None        # Single precision
```

**When to use each:**

- **`int32`**: Most integer fields (years, counts, IDs)
- **`uint8`**: Small positive values (0-255), like color components, confidence percentages
- **`uint16`**: Medium positive values (0-65K), like ports, small counts
- **`uint32`**: Large positive values, like population, large IDs
- **`float64`**: Most decimal numbers (heights, coordinates, measurements) - **this is the default choice**
- **`float32`**: When space is critical and precision isn't

When in doubt, use `int32` (equivalent to `int`), `int64` (equivalent to `long`, although [not safely representable in JSON](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER)), or `float64` (equivalent to `double`).

**Why specific numeric types matter:**

The specific numeric types are crucial for data interchange and storage compatibility:

- **Cross-platform consistency**: Ensures the same data types across Python, Arrow, Parquet, and other geospatial tools
- **Round-trip compatibility**: Data round-trips cleanly between Parquet files, databases (PostgreSQL, Trino), Shapefiles, and JSON Schema
- **Value range validation**: Prevents invalid values (e.g., negative heights, RGB values > 255)
- **Storage efficiency**: `uint8` uses 1 byte vs `int64` which uses 8 bytes
- **Built-in validation**: These types use Pydantic `Field()` constraints to validate ranges (e.g., `Field(ge=0, le=100)` ensures values stay within bounds)

#### Union Types

Union types allow a field to accept multiple different types. The `|` symbol means "or":

```python
from typing import Literal

class Building(Feature):
    # This field can be either a string OR None (most common union)
    name: str | None = None

    # This field can be one of specific string values OR None
    status: Literal["active", "inactive", "pending"] | None = None
```

**Common union patterns:**

```python
# Optional field (most common union)
height: float64 | None = None          # Can be a number or missing

# Specific string values (an alternative to enums where descriptions aren't needed)
priority: Literal["low", "medium", "high"] | None = None

# Boolean or None
is_verified: bool | None = None
```

**Union best practices:**

- Keep unions simple - avoid more than 2-3 types when possible
- Optional fields will include `None` to become optional
- Use `Literal` values for specific string choices rather than mixing basic types
- **Avoid mixed-type unions** like `str | int32` - these don't work well with many storage layers

> [!WARNING]
> **Storage compatibility**: Mixed-type unions (combining different basic types like `str | int32`) don't work with Parquet and other storage layers. Use `Literal` values or separate fields instead.

### Field Enhancement

#### Adding Descriptions and Constraints with Annotated

`Annotated` is Python's way to add extra information (metadata) to a type without changing the type itself. Think of it like adding notes or constraints to a field definition.

**Basic concept:**

```python
from typing import Annotated
from pydantic import Field

# Without Annotated - just the type
height: float64 | None = None

# With Annotated - type + extra information
height: Annotated[
    float64 | None,        # The actual type (what kind of data)
    Field(description="Height in meters")  # Extra metadata
] = None
```

**What goes inside `Annotated`:**

1. **First argument**: The actual type (`str`, `int32`, `list[str]`, etc.)
2. **Additional arguments**: Metadata like constraints, descriptions, validation rules

#### Field Constraints

Use Pydantic's `Field()` function to add constraints and descriptions:

**Numeric constraints:**

```python
from typing import Annotated
from pydantic import Field

class Building(Feature):
    # Range constraints
    height: Annotated[
        float64 | None,
        Field(ge=0, le=1000, description="Height in meters (0-1000m)")
    ] = None

    # Integer constraints
    floors: Annotated[
        int32 | None,
        Field(gt=0, lt=200, description="Number of floors (1-199)")
    ] = None
```

**Numeric constraint options:**

- **`ge`**: Greater than or equal to (≥)
- **`gt`**: Greater than (>)
- **`le`**: Less than or equal to (≤)
- **`lt`**: Less than (<)

**String constraints:**

```python
class Place(Feature):
    # Length constraints
    name: Annotated[
        str | None,
        Field(min_length=1, max_length=100, description="Place name (1-100 chars)")
    ] = None

    # Pattern matching
    postal_code: Annotated[
        str | None,
        Field(pattern=r"^\d{5}(-\d{4})?$", description="US postal code")
    ] = None
```

**String constraint options:**

- **`min_length`**: Minimum string length
- **`max_length`**: Maximum string length
- **`pattern`**: Regular expression pattern (regex)

### Collections and Lists

#### Basic List Fields

```python
class Building(Feature):
    # Simple list of strings
    tags: list[str] | None = None

    # List of complex objects
    access_rules: list[AccessRule] | None = None
```

#### List Constraints

```python
from overture.schema.validation import UniqueItemsConstraint

class Building(Feature):
    # List with size and uniqueness constraints
    categories: Annotated[
        list[str] | None,
        Field(min_length=1, max_length=10, description="1-10 categories"),
        UniqueItemsConstraint()  # Must come AFTER Field()
    ] = None
```

**List constraint options:**

- **`min_length`**: Minimum number of items
- **`max_length`**: Maximum number of items
- **`UniqueItemsConstraint()`**: No duplicate items (custom validation)

**Important**: `UniqueItemsConstraint()` must come AFTER `Field()` for proper JSON Schema generation.

> [!CAUTION]
> **Constraint order matters**: Always put `Field()` before `UniqueItemsConstraint()` or JSON Schema generation will create `minLength` (string constraint) instead of `minItems` (array constraint).
>
> **Why**: Pydantic processes annotations in order for JSON Schema generation. `Field()` must come first to set up the field properly. For lists, `Field(min_length=1)` creates a `minItems` constraint in the JSON Schema because the type immediately before it is a list. If `UniqueItemsConstraint()` comes first, Pydantic doesn't see the list type and treats `min_length` as a string constraint (`minLength`).

#### List Behavior

Lists maintain their **insertion order** (the order data exists in the field), but they are **not automatically sorted**.

### Enumerations

**What is an enumeration (enum)?** An enumeration is a way to define a fixed set of allowed values for a field. Think of it like a multiple-choice question - you define all the valid answers ahead of time, and users can only pick from those options.

For example, instead of allowing any string for a "status" field (which could lead to typos like "activ" or "Active"), you create an enum with exactly "active", "inactive", and "pending" as the only allowed values.

**Enums vs Literal:** You can achieve similar results with `Literal["active", "inactive", "pending"]`, but formal enums are better when you need descriptions, documentation, or want to reuse the same set of values across multiple fields.

#### Creating Enums

Enums define a fixed set of allowed values:

```python
from enum import Enum

class BuildingClass(str, Enum):
    """Further delineation of the building's built purpose."""

    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    CIVIC = "civic"

# Usage in a model
class Building(Feature):
    class_: Annotated[BuildingClass | None, Field(alias="class")] = None
```

#### Documenting Enum Values

Add documentation to describe what the enum and its values mean. In Python, you do this with **docstrings** - text enclosed in triple quotes `"""` that describes what something does:

```python
class VehicleType(str, Enum):
    """Types of vehicles for transportation."""

    CAR = "car"  # Standard passenger vehicle
    TRUCK = "truck"  # Commercial freight vehicle
    BICYCLE = "bicycle"  # Human-powered two-wheeler
    MOTORCYCLE = "motorcycle"  # Motorized two-wheeler
```

#### Why str, Enum?

Inheriting from `str, Enum` makes enum values work as both enums and strings, which is useful for JSON serialization and compatibility.

---

## Advanced Patterns

### Relationship Patterns

**What are relationships?** Relationships (or "associations") represent connections between different features or models. Think of them like links that connect related pieces of information - for example, a city center that belongs to an administrative area, or a transportation segment that connects to specific intersections.

Pydantic provides several ways to express these relationships, each suited to different use cases and complexity levels.

#### 1. Direct References (Foreign Keys)

The fundamental pattern is a direct reference where one feature "points to" another using an ID field with type safety and semantic information. This creates a one-way relationship - like a building knowing which neighborhood it belongs to, but the neighborhood doesn't automatically know about all its buildings.

```python
from typing import Annotated, Literal
from pydantic import Field
from overture.schema.core import Feature
from overture.schema.core.ref import Reference, Relationship
from overture.schema.core.types import Id

class DivisionArea(Feature[Literal["divisions"], Literal["division_area"]]):
    """Area polygon that belongs to a division."""

    # Required reference - every division area must belong to a division
    division_id: Annotated[
        Id,
        Reference(Relationship.BELONGS_TO, Division),
        Field(description="Division this area belongs to")
    ]

    # Optional reference - may or may not be associated with a place
    place_id: Annotated[
        Id | None,
        Reference(Relationship.CONNECTS_TO, Place),
        Field(description="Place this area is associated with")
    ] = None
```

**Available relationship types (see [Relationship](packages/overture-schema-core/src/overture/schema/core/ref.py)):**

- **`BELONGS_TO`**: The referencing feature belongs to the referenced feature (division area belongs to division)
- **`CONNECTS_TO`**: The referencing feature connects to the referenced feature (segment connects to connector)
- **`BOUNDARY_OF`**: The referencing feature forms a boundary of the referenced feature (boundary line defines area)

#### 2. Association as a Separate Feature (Complex Relationships)

When the relationship itself needs to store information, create a dedicated feature to represent that relationship. This is like creating a "relationship record" that describes how two things are connected.

**Simple relationship (use Pattern 1):**

- "Building A belongs to Neighborhood B" - just needs an ID reference

**Complex relationship (use Pattern 2):**

- "Admin Area X has City Center Y as its primary center since 2010 with 85% confidence" - the relationship has properties (`type=primary`, `date=2010`, `confidence=85%`)

```python
class AdminCityCenterAssociation(Feature[Literal["associations"], Literal["admin_city_center"]]):
    """Describes how an administrative area relates to a city center."""

    # The two things being connected
    admin_area_id: Annotated[Id, Reference(Relationship.CONNECTS_TO, AdminArea)]
    city_center_id: Annotated[Id, Reference(Relationship.CONNECTS_TO, CityCenter)]

    # Information about the relationship itself
    relationship_type: Literal["primary_center", "secondary_center"] = "primary_center"
    established_date: str | None = None
    confidence_score: Annotated[float64, Field(ge=0.0, le=1.0)] | None = None
```

When to use separate association features:

- The relationship has properties: confidence scores, dates, types, notes
- Many-to-many connections: one admin area can have multiple city centers, one city center can serve multiple admin areas
- You need to query the relationships: "show me all primary city center relationships established after 2015"

This focuses on the core concept: when relationships carry data, they become features themselves.

#### 3. Collection References

When a feature needs to reference multiple other features, use a list of references:

```python
class Route(Feature[Literal["transportation"], Literal["route"]]):
    """A transportation route that passes through multiple segments."""

    segment_ids: Annotated[
        list[Id],
        Field(min_length=1, description="Ordered list of segments in this route"),
        UniqueItemsConstraint(),  # No duplicate segments
        Reference(Relationship.CONNECTS_TO, TransportationSegment)  # All IDs reference segments
    ]

class Building(Feature[Literal["buildings"], Literal["building"]]):
    """A building that may contain multiple building parts."""

    part_ids: Annotated[
        list[Id] | None,
        Field(description="Building parts that belong to this building"),
        Reference(Relationship.BOUNDARY_OF, BuildingPart)  # All IDs reference building parts
    ] = None
```

#### Best Practices

**1. Always Use Reference Annotations**

Include `Reference` annotations for semantic clarity and documentation:

```python
# Good - complete relationship information
division_id: Annotated[
    Id,
    Reference(Relationship.BELONGS_TO, Division),
    Field(description="Division this area belongs to")
]

# Avoid - missing semantic information
division_id: Id
```

**2. Choose the Right Pattern**

- **Simple relationships** → Direct references (foreign keys)
- **Relationships with metadata** → Separate association features

```python
# Simple: just a link
admin_area_id: Annotated[Id, Reference(Relationship.BELONGS_TO, AdminArea)]

# Complex: relationship has properties
class AdminCityCenterAssociation(Feature[...]):
    admin_area_id: Annotated[Id, Reference(Relationship.CONNECTS_TO, AdminArea)]
    city_center_id: Annotated[Id, Reference(Relationship.CONNECTS_TO, CityCenter)]
    relationship_type: Literal["primary", "secondary"] = "primary"
```

#### Association Pattern Examples

**Transportation Network:**

```python
# Segments connect to connectors (intersection points)
class Segment(Feature[Literal["transportation"], Literal["segment"]]):
    from_connector_id: Annotated[Id, Reference(Relationship.CONNECTS_TO, Connector)]
    to_connector_id: Annotated[Id, Reference(Relationship.CONNECTS_TO, Connector)]

# Routes contain multiple segments in order
class Route(Feature[Literal["transportation"], Literal["route"]]):
    segment_ids: Annotated[
        list[Id],
        Reference(Relationship.CONNECTS_TO, TransportationSegment),
        Field(description="Ordered list of segments in this route")
    ]
```

**Administrative Hierarchy:**

```python
# Division areas belong to divisions
class DivisionArea(Feature[Literal["divisions"], Literal["division_area"]]):
    division_id: Annotated[Id, Reference(Relationship.BELONGS_TO, Division)]

# Places belong to administrative areas
class Place(Feature[Literal["places"], Literal["place"]]):
    admin_area_id: Annotated[Id | None, Reference(Relationship.BELONGS_TO, AdminArea)] = None
```

**Building Relationships:**

```python
# Building parts belong to buildings
class BuildingPart(Feature[Literal["buildings"], Literal["building_part"]]):
    building_id: Annotated[Id, Reference(Relationship.BELONGS_TO, Building)]

# Buildings can reference their address
class Building(Feature[Literal["buildings"], Literal["building"]]):
    address_id: Annotated[Id | None, Reference(Relationship.CONNECTS_TO, Address)] = None
```

### Discriminated Unions

**What is a discriminated union?** A discriminated union is a type that can be backed by one of several different models, where a specific field (the "discriminator") determines which model it actually is. Think of it like a form that changes its fields based on a category selection.

```python
from typing import Annotated, Literal
from pydantic import Field
from overture.schema.core import Feature

# Base class with common fields
class TransportationSegment(Feature[Literal["transportation"], Literal["segment"]]):
    subtype: Subtype  # This is the discriminator field
    # ... common fields for all segments

# Specific segment types
class RoadSegment(TransportationSegment):
    subtype: Literal[Subtype.ROAD]  # Must be "road"
    class_: Annotated[RoadClass, Field(alias="class")]
    speed_limits: SpeedLimits | None = None
    # ... road-specific fields

class RailSegment(TransportationSegment):
    subtype: Literal[Subtype.RAIL]  # Must be "rail"
    class_: Annotated[RailClass, Field(alias="class")]
    rail_flags: RailFlags | None = None
    # ... rail-specific fields

# Union type that automatically picks the right model based on subtype
Segment = Annotated[
    RoadSegment | RailSegment | WaterSegment,
    Field(discriminator="subtype")
]
```

The `discriminator="subtype"` tells Pydantic to look at the `subtype` field to determine which specific model to use. If `subtype` is "road", it uses `RoadSegment`; if "rail", it uses `RailSegment`.

#### Abstract vs Concrete Classes

**What's the difference?** In UML and traditional OOP, abstract classes cannot be instantiated - they serve as templates for concrete classes. In Pydantic, by default, **all classes are concrete** (can be instantiated), but you can make classes abstract when needed.

**Current pattern (all concrete):**

```python
# Both can be instantiated as map features
base_segment = TransportationSegment(subtype=Subtype.ROAD, geometry=...)  # Valid
road_segment = RoadSegment(subtype=Subtype.ROAD, geometry=..., class_=...)  # Valid
```

**Making the base class abstract:**

```python
from abc import ABC, abstractmethod
from typing import Annotated, Literal
from pydantic import Field

class TransportationSegment(Feature[Literal["transportation"], Literal["segment"]], ABC):
    """Abstract base - cannot be instantiated directly."""

    subtype: Subtype  # Discriminator field

    @abstractmethod
    def get_speed_limit(self) -> float:
        """Each concrete type must implement this."""
        pass

class RoadSegment(TransportationSegment):
    """Concrete class - can be instantiated."""
    subtype: Literal[Subtype.ROAD]
    speed_limits: SpeedLimits | None = None

    def get_speed_limit(self) -> float:
        return self.speed_limits.max_speed if self.speed_limits else 50.0

# Now only concrete classes can be instantiated
# base_segment = TransportationSegment(...)  # TypeError: Can't instantiate abstract class
road_segment = RoadSegment(subtype=Subtype.ROAD, ...)  # Valid
```

**Registration pattern (recommended when working with Overture models):**

Instead of making classes abstract, we use **entry point registration** where only specific concrete types are discoverable as map features:

```python
# In packages/overture-schema-transportation-theme/pyproject.toml
[project.entry-points."overture.models"]
"transportation.connector" = "overture.schema.transportation.connector.models:Connector"
"transportation.segment" = "overture.schema.transportation.segment.models:Segment"
```

**Real example:** See [`packages/overture-schema-transportation-theme/src/overture/schema/transportation/segment/models.py`](packages/overture-schema-transportation-theme/src/overture/schema/transportation/segment/models.py) where:

- **`Segment`** is a discriminated union: `RoadSegment | RailSegment | WaterSegment`
- **`TransportationSegment`** is the concrete base class that all segment types inherit from
- **Individual segment types** (`RoadSegment`, `RailSegment`, `WaterSegment`) are NOT directly registered

**This registration pattern means:**

1. Only **`Segment`** (the union type) is discoverable as an official map feature
2. The union automatically resolves to the correct concrete type based on the `subtype` field
3. All classes (`TransportationSegment`, `RoadSegment`, etc.) can be reused as base classes for alternate implementations

### Pattern Properties (Constrained Key-Value Maps)

**What are pattern properties?** Pattern properties let you create key-value maps where the keys must follow a specific pattern (like language codes) and values have specific types.

```python
from typing import Annotated
from pydantic import Field

class Names(StrictBaseModel):
    primary: str

    # Keys (strings) must match a language tag pattern, values are strings
    common: Annotated[
        dict[
            # The key type
            Annotated[
                str,
                Field(
                    pattern=r"^[a-z]{2,3}(-[A-Z]{2})?$",
                    description="Language tag (e.g., 'en', 'es-MX')"
                )
            ],
            str,  # The value type
        ],
        Field(json_schema_extra={"additionalProperties": False}),
    ] | None = None
```

**Example data:**

```json
{
    "primary": "New York City",
    "common": {
        "es": "Ciudad de Nueva York",
        "fr": "New York",
        "zh-CN": "纽约市"
    }
}
```

The `additionalProperties: False` ensures only keys matching the pattern are allowed when generated JSON Schema is used.

### Nested List Validation

**What is nested list validation?** This pattern validates both the outer list and the inner structure of each item, with constraints at multiple levels.

```python
from typing import Annotated
from pydantic import Field

# Each item has its own field validation
class HierarchyItem(StrictBaseModel):
    division_id: str
    name: str

class Division(Feature):
    # Nested list validation: outer list AND inner lists both have length constraints
    hierarchies: Annotated[
        list[  # Outer list
            Annotated[
                list[HierarchyItem],  # Inner list
                Field(min_length=1)   # Inner list must have at least 1 item
            ]
        ],
        Field(min_length=1)  # Outer list must have at least 1 hierarchy
    ]
```

This creates validation at three levels:

1. **Individual items**: Each `HierarchyItem` validates its own fields (`division_id`, `name`)
2. **Inner lists**: Each inner list must have at least 1 item (`min_length=1`)
3. **Outer list**: The `hierarchies` field must have at least 1 inner list (`min_length=1`)

### Type Aliases for Reusable Patterns

**What are type aliases?** Type aliases let you create custom names for complex or frequently-used types. Think of them like creating shortcuts or nicknames for long type definitions.

**What is `NewType`?** `NewType` creates a distinct type that's based on an existing type but is treated as different for type checking purposes. This helps prevent mistakes like using an email address where you need a country code, or using a person's name where you need an ID - they're all strings, but they have different meanings and shouldn't be interchangeable.

**Note**: `NewType` is primarily useful when working with Pydantic models in Python code (development, testing, certain data processing tasks). It doesn't affect data validation or JSON Schema generation - it's a development tool to catch mistakes before they happen.

> [!WARNING]
> **Naming conflicts**: Never use the same name for a model class and type alias in the same module - this creates circular references and confusing code.

**Guidelines:**

- **Model classes**: Use noun names (`SourceItem`, `AccessRule`, `GeometricScope`)
- **Type aliases**: Use plural or descriptive names (`Sources`, `AccessRules`, `ConnectivityData`)
- **Avoid using the same names**: Use different names for models and type aliases, even if they're related

```python
from typing import NewType, Annotated
from pydantic import Field

# Create distinct types for different kinds of strings
SegmentId = NewType("SegmentId", str)  # IDs are strings, but distinct
CountryCode = NewType("CountryCode", str)  # Country codes are strings, but distinct

# Create aliases for complex field patterns
EmailList = NewType("EmailList", Annotated[
    list[str],
    Field(min_length=1, description="List of email addresses")
])

class Contact(StrictBaseModel):
    # Clear, self-documenting field types
    id: SegmentId  # Can't accidentally use a CountryCode here
    country: CountryCode  # Can't accidentally use a SegmentId here
    emails: EmailList  # Reusable validation pattern
```

**Why use type aliases?**

1. **Prevent mistakes**: `SegmentId` and `CountryCode` are both strings, but you can't mix them up when they're created using `NewType`
2. **Reusable patterns**: Define complex field validation once, use it many times
3. **Self-documenting code**: `EmailList` is clearer than `list[str]`
4. **Consistency**: Everyone uses the same validation rules for the same concept

---

## Integration Guide

### Project Architecture

#### File Organization

Organize code by scope and avoid circular imports:

**Cross-theme shared**: `overture-schema-core` package

- Used by multiple themes (e.g., `LanguageTag`, `CountryCode`, `Feature`)

**Theme-level shared**: Theme package root (e.g., `overture-schema-transportation-theme/src/overture/schema/transportation/`)

- Used by multiple types within a theme (e.g., `AccessRules`, `RoadSurface`)

**Type-specific**: Type subdirectory (e.g., `overture-schema-transportation-theme/src/overture/schema/transportation/segment/`)

- Only used by one specific type (e.g., `SegmentType`, `LaneConfiguration`)

**File type rules:**

- **`models.py`**: Pydantic model classes (and type aliases that reference models)
- **`enums.py`**: Enum classes only, no project imports
- **`types.py`**: Type aliases that don't reference models, no project imports

#### Import Organization

```python
# Standard library imports first
from typing import Annotated, Literal, NewType
from enum import Enum

# Third-party imports
from pydantic import BaseModel, ConfigDict, Field

# Cross-theme imports
from overture.schema.core import Feature
from overture.schema.core.models import StrictBaseModel
from overture.schema.validation import UniqueItemsConstraint

# Local imports last
from .enums import SegmentType
from .types import SegmentId, LaneWidth  # Only non-model type aliases
```

`uv run ruff format <file>` will sort your imports in this order automatically.

#### Why Not Use @field_validator or @model_validator?

This project uses a custom validation system that generates better JSON Schema output and supports code generation (without additional work, `@field_validator` and `@model_validator` don't make their constraints discoverable). Always use constraints from `overture.schema.validation` instead of using Pydantic validation decorators:

```python
# Don't do this
@field_validator('categories')
def validate_categories_unique(cls, v):
    if v and len(v) != len(set(v)):
        raise ValueError('Categories must be unique')
    return v

# Do this instead
from overture.schema.validation import UniqueItemsConstraint

class Building(Feature):
    categories: Annotated[
        list[str] | None,
        Field(min_length=1, description="Building categories"),
        UniqueItemsConstraint()
    ] = None
```

### Migrating from JSON Schema

If you're familiar with JSON Schema files (like `schema/schema.yaml`), this section helps translate those patterns to Pydantic models.

#### How $defs and $ref Translate

**JSON Schema approach:**

```yaml
# In defs.yaml
"$defs":
  propertyDefinitions:
    address:
      type: object
      properties:
        freeform: { type: string }
        locality: { type: string }

# In building.yaml
properties:
  address: { "$ref": "../defs.yaml#/$defs/propertyDefinitions/address" }
```

**Pydantic approach:**

```python
# In overture-schema-core/src/overture/schema/core/models.py
class Address(StrictBaseModel):
    """A postal address."""
    freeform: str | None = None
    locality: str | None = None

# In overture-schema-buildings-theme/src/overture/schema/buildings/building/models.py
class Building(Feature):
    address: Address | None = None
```

**Primary differences:**

- JSON Schema uses `$ref` to reference definitions; Pydantic uses direct Python imports
- JSON Schema definitions live in `$defs`; Pydantic models are regular Python classes grouped into modules
- JSON Schema allows inline definitions; Pydantic encourages separate model classes

#### How Containers Work

**JSON Schema containers** (like `namesContainer`, `shapeContainer`) are reusable property groups:

```yaml
# In defs.yaml
propertyContainers:
  namesContainer:
    properties:
      names: { "$ref": "#/$defs/propertyDefinitions/allNames" }

  shapeContainer:
    properties:
      height: { type: number }
      num_floors: { type: integer }

# In building.yaml
allOf:
  - "$ref": ../defs.yaml#/$defs/propertyContainers/namesContainer
  - "$ref": ./defs.yaml#/$defs/propertyContainers/shapeContainer
```

**Pydantic equivalent** uses **mixin classes**:

```python
# In core/models.py
class Named(BaseModel):
    """Properties defining the names of a feature."""
    names: Names | None = None

# In buildings/models.py
class Shape(BaseModel):
    """Properties of the building's shape."""
    height: float64 | None = None
    num_floors: int32 | None = None

# Usage with multiple inheritance
class Building(Feature, Named, Shape):
    pass  # "pass" means "do nothing" - Building inherits names, height, num_floors, etc. from its parents
```

JSON Schema containers become **mixin classes** in Pydantic that you inherit from.

#### Common Translation Patterns

| JSON Schema | Pydantic | Notes |
|-------------|----------|-------|
| `"$ref": "other.yaml#/path"` | `from other import Model` | Direct Python imports |
| `allOf: [ref1, ref2]` | `class Model(Base1, Base2)` | Multiple inheritance |
| `minLength: 1` | `Field(min_length=1)` | Field constraints |
| `minimum: 0, maximum: 100` | `Field(ge=0, le=100)` | Numeric ranges |
| `uniqueItems: true` | `UniqueItemsConstraint()` | Custom constraint |
| `enum: [a, b, c]` | `class E(str, Enum): A="a"` | Enum class |
| `type: ["string", "null"]` | `str \| None = None` | Optional types |
| `if/then` conditional | Custom validation constraints | Model constraints |

---

## Reference

### Complete Templates

#### Basic Model Template

```python models.py
from typing import Annotated
from pydantic import Field
from overture.schema.core.models import StrictBaseModel
from overture.schema.core.primitives.numeric import int8, float64

class MyCustomType(StrictBaseModel):
    """Brief description of what this represents."""

    # Required fields (no default value)
    name: str
    category: str

    # Optional fields (with default values)
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

#### Feature Template

```python models.py
from typing import Annotated, Literal
from pydantic import Field
from overture.schema.core import Feature
from overture.schema.core.geometry import Geometry, GeometryType, GeometryTypeConstraint

class MyFeature(Feature[Literal["my_theme"], Literal["my_type"]]):
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

#### Enum Template

```python enums.py
from enum import Enum

class MyEnum(str, Enum):
    """Description of what this enum represents."""

    VALUE_ONE = "value_one"
    VALUE_TWO = "value_two"
    VALUE_THREE = "value_three"
```

#### Model with Validation Constraints

```python models.py
from typing import Annotated
from pydantic import Field
from overture.schema.validation import UniqueItemsConstraint
from overture.schema.core.models import StrictBaseModel

class Contact(StrictBaseModel):
    """Contact information with validation constraints."""

    name: str
    email: str | None = None
    phone: str | None = None

    # List with constraints
    tags: Annotated[
        list[str] | None,
        Field(min_length=1, description="Contact tags"),
        UniqueItemsConstraint()  # No duplicate tags
    ] = None
```

#### Association Feature Template

```python models.py
from typing import Annotated, Literal
from pydantic import Field
from overture.schema.core import Feature
from overture.schema.core.ref import Reference, Relationship
from overture.schema.core.types import Id
from overture.schema.core.primitives.numeric import float64

class MyAssociation(Feature[Literal["associations"], Literal["my_association"]]):
    """Represents a relationship between two features with metadata."""

    # References to the associated features
    feature_a_id: Annotated[
        Id,
        Reference(Relationship.CONNECTS_TO, FeatureA),
        Field(description="First feature in the relationship")
    ]

    feature_b_id: Annotated[
        Id,
        Reference(Relationship.CONNECTS_TO, FeatureB),
        Field(description="Second feature in the relationship")
    ]

    # Relationship metadata
    relationship_type: Literal["primary", "secondary"] = "primary"
    confidence: Annotated[float64 | None, Field(ge=0.0, le=1.0)] = None

    # Optional contextual information
    notes: str | None = None
```

### Quick Reference

#### Essential Patterns (Most Common)

```python
# Basic field types
name: str                    # Required string
name: str | None = None     # Optional string
count: int32                # Required integer
priority: Literal["high", "medium", "low"] | None = None  # Constrained values

# Validated fields
height: Annotated[float64 | None, Field(ge=0, description="Height in meters")] = None
tags: Annotated[list[str] | None, Field(min_length=1), UniqueItemsConstraint()] = None

# Association patterns
parent_id: Annotated[Id | None, Reference(Relationship.BELONGS_TO, ParentModel)] = None
connector_ids: list[Id]  # References to multiple related features
```

#### Model Templates

```python
# Non-feature model
class Address(StrictBaseModel):
    street: str
    city: str | None = None

# Feature model
class Building(Feature[Literal["buildings"], Literal["building"]]):
    geometry: Geometry
    height: float64 | None = None

# Enum
class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
```

#### Constraint Reference

| Type | Constraint | JSON Schema | Example |
|------|------------|-------------|---------|
| **Numeric** | `ge=0, le=100` | `minimum`, `maximum` | `Field(ge=0, le=100)` |
| **String** | `min_length=1, pattern=r"..."` | `minLength`, `pattern` | `Field(min_length=1, pattern=r"^[A-Z]+$")` |
| **List** | `min_length=1, UniqueItemsConstraint()` | `minItems`, `uniqueItems` | `Field(min_length=1), UniqueItemsConstraint()` |
| **Custom** | `LanguageTagConstraint()` | Custom validation | `LanguageTagConstraint()` |

#### Import Cheatsheet

```python
# Essential imports for most models
from typing import Annotated, Literal
from enum import Enum
from pydantic import Field
from overture.schema.core import Feature
from overture.schema.core.models import StrictBaseModel
from overture.schema.validation import UniqueItemsConstraint
from overture.schema.core.primitives.numeric import int32, float64

# For associations and references
from overture.schema.core.ref import Reference, Relationship
from overture.schema.core.types import Id
```

#### Naming Conventions

- **Classes**: `PascalCase` (`Building`, `AccessRule`)
- **Fields**: `snake_case` (`construction_year`, `has_parts`)
- **Enums**: `UPPER_SNAKE_CASE = "value"` (`ACTIVE = "active"`)
