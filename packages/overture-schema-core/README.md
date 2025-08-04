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
- **Scoping System**: Flexible conditional rule application framework

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
