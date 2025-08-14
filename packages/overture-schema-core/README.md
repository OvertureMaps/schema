# Overture Schema Core

Core Pydantic models and base classes for Overture Maps schemas, providing foundational types, geometry handling, and a comprehensive scoping system for conditional rule application.

## Installation

```bash
pip install overture-schema-core
```

## Key Components

- **Base Classes**: Extensible base models for Overture Maps features
- **Geometry Types**: WKB geometry type hints and utilities
- **Common Structures**: Shared models used across all themes
- **Abstract Data Types**: Validated primitive types with multi-target serialization support
- **Scoping System**: Flexible conditional rule application framework

## Abstract Data Types

The abstract data types system provides validated primitive types with automatic
constraint checking and multi-target serialization support. This enables consistent type
definitions that can generate appropriate representations for different targets
(Scala, Spark, Parquet, JSON Schema).

### Available Types

#### Integer Types

- **`UInt8`**: 8-bit unsigned integer (0-255)
- **`UInt16`**: 16-bit unsigned integer (0-65535)
- **`UInt32`**: 32-bit unsigned integer (0-4294967295)
- **`Int8`**: 8-bit signed integer (-128 to 127)
- **`Int32`**: 32-bit signed integer (-2³¹ to 2³¹-1)
- **`Int64`**: 64-bit signed integer (-2⁶³ to 2⁶³-1)

#### Floating Point Types

- **`Float32`**: 32-bit floating point number
- **`Float64`**: 64-bit floating point number

### Basic Usage

```python
from pydantic import BaseModel, Field
from overture.schema.core.types.abstract import (
    UInt8, UInt32, Float32
)

class Building(BaseModel):
    """Building feature with abstract data types."""

    height: Float32 | None = Field(
        None,
        description="Height of building in meters"
    )

    num_floors: UInt8 | None = Field(
        None,
        description="Number of floors in building"
    )

    area: UInt32 | None = Field(
        None,
        description="Floor area in square meters"
    )
```

### Automatic Validation

Abstract types automatically validate constraints:

```python
# Valid values
building = Building(height=45.5, num_floors=12, area=2500)

# Invalid values raise ValidationError
Building(num_floors=256)  # Error: 256 > UInt8 maximum (255)
Building(num_floors=-1)   # Error: -1 < UInt8 minimum (0)
```

### Multi-Target Type Mappings

Abstract types can be mapped to different target systems:

```python
from overture.schema.core.types.abstract import Float32, Int32, UInt8, get_target_type

# Scala types
get_target_type(UInt8, "scala")     # "Byte"
get_target_type(Float32, "scala")   # "Float"
get_target_type(Int32, "scala")     # "Int"

# Spark SQL types
get_target_type(UInt8, "spark")     # "ByteType"
get_target_type(Float32, "spark")   # "FloatType"

# Parquet physical types
get_target_type(UInt8, "parquet")   # "INT32" (promoted)
get_target_type(Float32, "parquet") # "FLOAT"
```

This currently supports [low-level Parquet
types](https://parquet.apache.org/docs/file-format/types/). We may consider [Parquet
logical types](https://github.com/apache/parquet-format/blob/master/LogicalTypes.md) in
the future.

### JSON Schema Generation

Abstract types integrate with JSON Schema generation:

```python
from overture.schema.core.json_schema import json_schema

schema = json_schema(Building)

# UInt8 generates proper integer constraints
assert schema["properties"]["num_floors"]["type"] == "integer"
assert schema["properties"]["num_floors"]["minimum"] == 0
assert schema["properties"]["num_floors"]["maximum"] == 255

# Float types get an explicit number type
assert schema["properties"]["height"]["type"] == "number"
```

### Type Registry

The system maintains a registry mapping concrete types to their abstract definitions:

```python
from overture.schema.core.types.abstract import (
    Float32,
    get_abstract_type
)

# Get the abstract type for a concrete type
abstract_type = get_abstract_type(UInt8)
abstract_type.get_target_type("scala")  # "Byte"
get_abstract_type(Float32).get_target_type("parquet")  # "FLOAT"
```

### Type Safety

The abstract data types provide strong type safety guarantees at both static and runtime levels:

**Static Type Checking**: mypy can distinguish between different abstract types, preventing common errors:

```python
from overture.schema.core.types.abstract import UInt8, UInt32

def process_floor_count(floors: UInt8) -> str:
    return f"Building has {floors} floors"

def process_area(area: UInt32) -> str:
    return f"Area: {area} sq meters"

# Type checker prevents mixing incompatible types
floors: UInt8 = 12
area: UInt32 = 2500

process_floor_count(area)   # mypy error: Expected UInt8, got UInt32
process_area(floors)        # mypy error: Expected UInt32, got UInt8
```

**Runtime Validation**: Pydantic automatically validates bounds and type constraints:

```python
# Automatic range validation
Building(num_floors=300)    # ValidationError: 300 exceeds UInt8 max (255)
Building(height=-10.5)      # ValidationError: negative height invalid
```

## Scoping System

The scoping system enables precise conditional application of rules based on geometric, temporal, directional, and subjective criteria. This is essential for transportation rules like speed limits, access restrictions, and other regulations that apply under specific conditions.

### Architecture

The scoping system follows a **mix-in architecture** with two tiers:

1. **Geometric Scoping**: Where along a linear feature (using linear referencing)
2. **Conditional Scoping**: When and how rules apply (temporal, directional, subjective)

### Core Scopes

#### Individual Scopes

Each scope class handles a specific dimension of conditional logic:

- **`GeometricRangeScope`**: Linear referencing with `between: [start, end]`
- **`TemporalScope`**: Time-based conditions using OSM opening hours format
- **`HeadingScope`**: Directional application (`forward`/`backward`)
- **`TravelModeScope`**: Travel mode filtering (car, bike, foot, etc.)
- **`PurposeOfUseScope`**: Usage purpose filtering (delivery, destination, etc.)
- **`RecognizedStatusScope`**: Recognition status (private, employee, etc.)
- **`VehicleScope`**: Vehicle attribute constraints (weight, height, etc.)

#### Composite Scoping

**`ScopingConditions`**: Inherits from all individual scopes to provide comprehensive scoping capabilities in a single class.

### Usage Patterns

#### Basic Geometric Scoping

```python
from overture.schema.core.common import GeometricRangeScope

class WidthRule(GeometricRangeScope):
    width: Dimension
```

#### Complex Conditional Scoping

```python
from overture.schema.core.common import GeometricRangeScope, ScopingConditions

class SpeedLimitWhenClause(
    TemporalScope,
    HeadingScope,
    PurposeOfUseScope,
    RecognizedStatusScope,
    TravelModeScope,
    VehicleScope
):
    pass

class SpeedLimitRule(GeometricRangeScope):
    max_speed: Speed
    when: Optional[SpeedLimitWhenClause] = None
```

#### Full Scoping Integration

```python
class AccessRestrictionRule(GeometricRangeScope):
    access_type: AccessType
    when: Optional[AccessRestrictionWhenClause] = None
```

### Examples

#### Temporal Speed Limit

```yaml
speed_limits:
  - between: [0, 1]
    max_speed: {value: 30, unit: km/h}
    when:
      during: "Mo-Fr 07:00-09:00,17:00-19:00"  # Rush hours only
```

#### Vehicle-Specific Access Restriction

```yaml
access_restrictions:
  - between: [0.2, 0.8]
    access_type: denied
    when:
      vehicle:
        - dimension: weight
          comparison: greater_than
          value: 7.5
          unit: t
```

#### Multi-Dimensional Scoping

```yaml
access_restrictions:
  - between: [0, 1]
    access_type: denied
    when:
      mode: [bus]
      during: "Mo-Fr 15:00-18:00"
      heading: forward
      using: [to_deliver]
```

### Design Principles

1. **Composability**: Mix-in design allows combining only needed scoping dimensions
2. **Reusability**: Base scope classes work across all rule types and themes
3. **Extensibility**: Easy to add new scoping dimensions or modify existing ones
4. **Type Safety**: Full Pydantic validation for all scoping conditions
5. **Linear Reference Integration**: Seamless integration with geometric positioning

### Rule Complexity Patterns

- **Simple Rules** (flags, dimensions): Geometric scoping only
- **Complex Rules** (speed limits, access): Geometric + conditional scoping
- **Transition Rules**: Full scoping including directional constraints

This scoping system provides the foundation for precise, flexible rule specification across all Overture Maps transportation features.
