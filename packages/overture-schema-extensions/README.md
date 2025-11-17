# overture-schema-extensions

Overture Maps schema extensions with additional feature properties like operating hours.

## Overview

This package provides a simple extension model that contains just an ID and operating hours information. Unlike full Overture features, this model doesn't require geometry, version, theme, or other standard feature fields, making it perfect for datasets that only need to associate operating hours with IDs.

## Features

### ExtendedFeature

A simple model with just two fields:

**Fields:**

- `id`: Unique identifier (required, inherited from the `Identified` mixin)
- `operating_hours`: Operating hours specification (optional)

### OperatingHours

A structured model for operating hours information:

- `primary`: Primary operating hours (required string, e.g., `"Mo-Fr 09:00-17:00; Sa 10:00-14:00"`)

## Installation

This package is part of the Overture Maps schema workspace. Install it using:

```bash
uv pip install overture-schema-extensions
```

Or include it in your project dependencies:

```toml
[project]
dependencies = [
    "overture-schema-extensions",
]
```

## Usage

### Basic Example

```python
from overture.schema.extensions import ExtendedFeature, OperatingHours

# Create a simple feature with just ID and operating hours
feature = ExtendedFeature(
    id="example-123",
    operating_hours=OperatingHours(
        primary="Mo-Fr 09:00-17:00; Sa 10:00-14:00"
    )
)

# You can also create a feature with just an ID
minimal_feature = ExtendedFeature(id="example-456")
```

### JSON Schema Generation

Generate JSON Schema for validation:

```python
import json
from overture.schema.extensions import ExtendedFeature

schema = ExtendedFeature.model_json_schema()
print(json.dumps(schema, indent=2))
```

### Validation

The models use Pydantic for automatic validation:

```python
from overture.schema.extensions import ExtendedFeature

# This will raise validation errors if required fields are missing
# or if field values don't match constraints
try:
    feature = ExtendedFeature(
        id="test",
        operating_hours=OperatingHours(primary="Mo-Fr 09:00-17:00")
    )
    print("Valid feature!")
except ValueError as e:
    print(f"Validation error: {e}")
```

## Development

### Running Tests

```bash
uv run pytest packages/overture-schema-extensions/
```

### Type Checking

The package includes a `py.typed` marker for full type hint support:

```bash
mypy src/overture/schema/extensions/
```

## Use Cases

This package is ideal for:

- **Lightweight datasets**: When you only need to track operating hours by ID, without full geospatial features
- **Operating hours updates**: Maintaining a separate dataset of operating hours that can be joined with full feature data
- **Simple extensions**: Demonstrating how to create minimal Pydantic models that reuse Overture's ID system

## Schema Patterns

This package follows the Overture Maps Pydantic schema conventions:

- Uses `@no_extra_fields` decorator for strict validation
- Follows the `OvertureFeature[ThemeT, TypeT]` generic pattern
- Uses `Annotated` types with `Field()` for descriptions and constraints
- All optional fields default to `None` (never non-None defaults)
- Numeric types use specific primitives (`int32`, `float64`, etc.)

For more information on schema patterns, see the [Pydantic Guide](../../PYDANTIC_GUIDE.md).

## License

MIT License - See LICENSE file for details.

## Related Packages

- `overture-schema-core`: Base classes and common structures
- `overture-schema-system`: Primitives, constraints, and validation
- `overture-schema-places-theme`: Places features (inspiration for operating hours)
- `overture-schema-buildings-theme`: Buildings features

## Contributing

This package demonstrates how to create simple extensions to the Overture Maps schema:

1. Inherit from `Identified` to get the `id` field (instead of full `OvertureFeature`)
2. Add custom fields with proper annotations and descriptions
3. Create supporting models with `@no_extra_fields` decorator
4. Register your feature in `pyproject.toml` entry points

This approach lets you create lightweight models that don't require all the standard Overture feature fields like geometry, version, theme, and type.
