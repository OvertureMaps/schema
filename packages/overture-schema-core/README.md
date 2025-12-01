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
- **Primitive Data Types**: Validated primitive types with multi-target serialization support
- **Scoping System**: Flexible conditional rule application framework

## Enhanced Primitive Types

The enhanced primitive types system provides validated primitive types with automatic
constraint checking and multi-target serialization support. This enables consistent type
definitions that can generate appropriate representations for different targets (Spark,
Parquet, etc.).

### Available Types

Built-in Python primitive types (`str`, `int`, `float`, `bool`, `list`, etc.) are
automatically mapped.

We also provide the following additional types:

#### Integer Types

- **`uint8`**: 8-bit unsigned integer (0-255)
- **`uint16`**: 16-bit unsigned integer (0-65535)
- **`uint32`**: 32-bit unsigned integer (0-4294967295)
- **`int8`**: 8-bit signed integer (-128 to 127)
- **`int32`**: 32-bit signed integer (-2³¹ to 2³¹-1)
- **`int64`**: 64-bit signed integer (-2⁶³ to 2⁶³-1)

#### Floating Point Types

- **`float32`**: 32-bit floating point number
- **`float64`**: 64-bit floating point number

### Basic Usage

```python
from pydantic import BaseModel, Field
from overture.schema.core.primitives import (
    uint8, uint32, float32
)

class Building(BaseModel):
    """Building feature with specific primitive data types."""

    height: float32 | None = Field(
        None,
        description="Height of building in meters"
    )

    num_floors: uint8 | None = Field(
        None,
        description="Number of floors in building"
    )

    area: uint32 | None = Field(
        None,
        description="Floor area in square meters"
    )
```

### Automatic Validation

Enhanced primitive types automatically validate constraints:

```python
# Valid values
building = Building(height=45.5, num_floors=12, area=2500)

# Invalid values raise ValidationError
Building(num_floors=256)  # Error: 256 > UInt8 maximum (255)
Building(num_floors=-1)   # Error: -1 < UInt8 minimum (0)
```

### Type Safety

The enhanced primitive types provide strong type safety guarantees at both static and
runtime levels:

**Static Type Checking**: mypy can distinguish between different primitive types,
*preventing common errors:

```python
from overture.schema.core.primitives import uint8, uint32

def process_floor_count(floors: uint8) -> str:
    return f"Building has {floors} floors"

def process_area(area: uint32) -> str:
    return f"Area: {area} sq meters"

# Type checker prevents mixing incompatible types
floors: uint8 = 12
area: uint32 = 2500

process_floor_count(area)   # mypy error: Expected UInt8, got UInt32
process_area(floors)        # mypy error: Expected UInt32, got UInt8
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
