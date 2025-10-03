# Overture Schema Validation

This is a constraint-based validation library intended for use with Overture Maps Pydantic schemas.
This package provides reusable validation constraints that enforce data quality and business rules
across Overture Maps feature data.

## Overview

This package provides constraint-based validation utilities for Overture Maps Pydantic schemas,
offering both field-level and model-level validation capabilities.

## Benefits of Using Constraints

- **Cleaner code**: Less boilerplate validation logic
- **Consistency**: Standardized validation patterns
- **Reusability**: Constraints can be composed and reused
- **Better errors**: Consistent, detailed validation error messages
- **JSON Schema integration**: Constraints enhance generated JSON schemas

## Installation

```bash
pip install overture-schema-validation
```

## Quick Start

```python
from typing import Annotated, List
from pydantic import Field
from overture.schema.core import StrictBaseModel
from overture.schema.validation import (
    LanguageTagConstraint,
    CountryCodeAlpha2Constraint,
    UniqueItemsConstraint,
)

class PlaceProperties(StrictBaseModel):
    # String pattern validation
    language: Annotated[str, LanguageTagConstraint()] = Field(
        ..., description="IETF BCP-47 language tag"
    )

    # Country code validation
    country: Annotated[str, CountryCodeAlpha2Constraint()] = Field(
        ..., description="ISO 3166-1 alpha-2 country code"
    )

    # Collection uniqueness
    categories: Annotated[
        List[str],
        UniqueItemsConstraint()
    ] = Field(..., description="Unique place categories")
```

## Constraint Categories

### String Pattern Constraints

Validate string formats against common patterns:

| Constraint | Purpose | Example |
|------------|---------|---------|
| `PatternConstraint` | Generic regex pattern matching | Custom patterns |
| `LanguageTagConstraint` | IETF BCP-47 language tags | `"en-US"`, `"fr-CA"` |
| `CountryCodeAlpha2Constraint` | ISO 3166-1 alpha-2 codes | `"US"`, `"CA"`, `"GB"` |
| `RegionCodeConstraint` | ISO 3166-2 subdivision codes | `"US-CA"`, `"CA-ON"` |
| `ISO8601DateTimeConstraint` | ISO 8601 datetime strings | `"2023-12-25T10Z"` |
| `HexColorConstraint` | Hexadecimal color codes | `"#FF0000"` |
| `JSONPointerConstraint` | RFC 6901 JSON Pointers | `"/properties/name"` |
| `WhitespaceConstraint` | Prevents leading/trailing whitespace | Trims input |
| `NoWhitespaceConstraint` | Prevents whitespace characters | `"identifier123"` |

### Collection Constraints

Validate array and object collections:

| Constraint | Purpose |
|------------|---------|
| `UniqueItemsConstraint` | Ensure all items in a list are unique |

**Example - Uniqueness:**

```python
# Ensure destination labels are unique by (value, type) combination
destinations: Annotated[
    list[DestinationLabel],
    # Field must come immediately after the list to generate minItems instead of minLength
    Field(min_length=1, description="Destination labels"),
    UniqueItemsConstraint()
]
```

### Numeric Constraints

Validate numeric ranges and formats:

| Constraint | Purpose | Range |
|------------|---------|-------|
| `ConfidenceScoreConstraint` | Probability/confidence values | 0.0 - 1.0 |
| `ZoomLevelConstraint` | Map zoom levels | 0 - 23 |

### Specialized Constraints

Domain-specific validation logic:

| Constraint | Purpose |
|------------|---------|
| `LinearReferenceRangeConstraint` | Linear referencing ranges [start, end] |
| | where 0 ≤ start < end ≤ 1 |

## Ready-to-Use Types

Pre-configured type aliases for common use cases:

```python
from overture.schema.core import StrictBaseModel
from overture.schema.validation import (
    # String types
    LanguageTag,          # Annotated[str, LanguageTagConstraint()]
    CountryCodeAlpha2,          # Annotated[str, CountryCodeAlpha2Constraint()]
    RegionCode,           # Annotated[str, RegionCodeConstraint()]
    ISO8601DateTime,      # Annotated[str, ISO8601DateTimeConstraint()]
    JSONPointer,          # Annotated[str, JSONPointerConstraint()]
    StrippedString,       # Annotated[str, StrippedConstraint()]
    HexColor,             # Annotated[str, HexColorConstraint()]
    NoWhitespaceString,   # Annotated[str, NoWhitespaceConstraint()]

    # Numeric types
    ConfidenceScore,      # Annotated[float, ConfidenceScoreConstraint()]
    ZoomLevel,            # Annotated[int, ZoomLevelConstraint()]
    NonNegativeFloat,     # Annotated[float, Field(ge=0.0)]
    NonNegativeInt,       # Annotated[int, Field(ge=0)]

    # Collection types
    LinearReferenceRange, # Annotated[List[float], LinearReferenceRangeConstraint()]
)

class MyModel(StrictBaseModel):
    language: LanguageTag = Field(..., description="IETF BCP-47 language tag")
    country: CountryCodeAlpha2 = Field(..., description="ISO 3166-1 alpha-2 country code")
    region: RegionCode = Field(None, description="ISO 3166-2 region code")
    confidence: ConfidenceScore = Field(..., description="ML confidence score")
    zoom: ZoomLevel = Field(..., description="Map zoom level")
    color: HexColor = Field("#FFFFFF", description="Hex color code")
    range: LinearReferenceRange = Field(..., description="Linear reference range")
```

## Advanced Usage

### Constraint Composition

Combine multiple constraints on a single field:

```python
tags: Annotated[
    List[str],
    UniqueItemsConstraint()  # Must be unique
] = Field(..., min_length=1, max_length=10, description="Feature tags")
```

### Custom Pattern Constraints

Create domain-specific pattern validators:

```python
from overture.schema.validation import PatternConstraint

OSMIdConstraint = PatternConstraint(
    pattern=r"^[nwr]\d+$",
    error_message="Invalid OSM ID format: {value}. Must be n123, w123, or r123"
)

osm_id: Annotated[str, OSMIdConstraint] = Field(..., description="OSM ID")
```

### Differences from Traditional Validators

#### Replacing @field_validator

Instead of using Pydantic's `@field_validator` decorator, use constraint annotations. This will
enable support for richer JSON Schema constraints and preservation of constraint logic in generated
code.

**Before (using @field_validator):**

```python
class PlaceProperties(BaseModel):
    country: str = Field(..., description="Country code")
    language: str = Field(..., description="Language tag")
    categories: List[str] = Field(..., description="Categories")
    wikidata_id: Optional[str] = Field(None, description="Wikidata ID")

    @field_validator("country")
    @classmethod
    def validate_country_code(cls, v):
        if not re.match(r"^[A-Z]{2}$", v):
            raise ValueError("Invalid ISO 3166-1 alpha-2 country code")
        return v

    @field_validator("language")
    @classmethod
    def validate_language_tag(cls, v):
        if not re.match(r"^[a-z]{2,3}(-[A-Za-z]{2,8})*$", v):
            raise ValueError("Invalid IETF BCP-47 language tag")
        return v

    @field_validator("categories")
    @classmethod
    def validate_unique_categories(cls, v):
        if len(v) != len(set(v)):
            raise ValueError("Categories must be unique")
        return v

    @field_validator("wikidata_id")
    @classmethod
    def validate_wikidata_format(cls, v):
        if v is not None and not re.match(r"^Q\d+$", v):
            raise ValueError("Invalid Wikidata identifier format")
        return v
```

**After (using constraints):**

```python
class PlaceProperties(BaseModel):
    country: Annotated[str, CountryCodeAlpha2Constraint()] = Field(
        ..., description="Country code"
    )
    language: Annotated[str, LanguageTagConstraint()] = Field(
        ..., description="Language tag"
    )
    categories: Annotated[List[str], UniqueItemsConstraint()] = Field(
        ..., description="Categories"
    )
    # Domain-specific constraints removed for incremental approach
```

#### Using Constraint-Based Validation

For complex model-level validation, use the mixin-based constraint system:

```python
from overture.schema.validation.mixin import ConstraintValidatedModel, at_least_one_of

@at_least_one_of("max_speed", "min_speed")
class SpeedLimitRule(ConstraintValidatedModel, BaseModel):
    max_speed: Optional[Speed] = None
    min_speed: Optional[Speed] = None
```

##### ⚠️ CRITICAL: Inheritance Order Matters

When using `ConstraintValidatedModel`, it **MUST** come first in the inheritance list:

```python
# ✅ CORRECT - ConstraintValidatedModel first
class MyModel(ConstraintValidatedModel, BaseModel):
    pass

# ❌ WRONG - Will not generate JSON Schema metadata
class MyModel(BaseModel, ConstraintValidatedModel):
    pass
```

This is due to Python's Method Resolution Order (MRO). When `ConstraintValidatedModel` comes first,
its `model_json_schema` method is called, which adds constraint metadata to the generated JSON
Schema.

## Error Messages

Constraints provide detailed, consistent error messages:

```python
# Invalid country code
ValidationError: 1 validation error for MyModel
country
  Invalid ISO 3166-1 alpha-2 country code: USA [type=value_error]

# Mutual exclusion violation
ValidationError: 1 validation error for BoundaryModel
is_land, is_territorial
  Fields is_land, is_territorial are mutually exclusive and cannot all be true [type=value_error]
```

## JSON Schema Generation

Constraints automatically enhance generated JSON schemas with appropriate metadata:

```python
model_schema = MyModel.model_json_schema()
# Results in enhanced JSON schema with pattern, format, and constraint information
{
  "properties": {
    "language": {
      "type": "string",
      "pattern": "^[a-z]{2,3}(-[A-Za-z]{2,8})*(-[0-9][A-Za-z0-9]{3})*$",
      "description": "IETF BCP-47 language tag"
    },
    "categories": {
      "type": "array",
      "items": {"type": "string"},
      "uniqueItems": true,
      "minItems": 1
    }
  }
}
```

## Integration with Overture Schema

This validation package integrates with Overture Maps schema packages using a hybrid approach:

- **Field-level constraints**: Used for single-field validation
- **Mixin-based constraints**: Used for complex model-level validation
- **@model_validator**: Used for custom cross-field validation

```python
# In your schema models
from typing import Annotated, Literal
from pydantic import model_validator
from overture.schema.validation import CountryCodeAlpha2, LanguageTag
from overture.schema.validation.mixin import ConstraintValidatedModel

# Base properties with field-level validation
class OvertureFeatureProperties(BaseModel):
    theme: str = Field(..., description="Overture theme")
    type: str = Field(..., description="Feature type")
    country: Optional[CountryCodeAlpha2] = None
    names: Annotated[
        dict[LanguageTag, str],
        Field(json_schema_extra={"additionalProperties": False})
    ]

# Division-specific validation with mixin constraints
@required_if("subtype", "region", ["parent_division_id"])
class DivisionProperties(ConstraintValidatedModel, OvertureFeatureProperties):
    theme: Literal["divisions"] = Field(...)
    type: Literal["division"] = Field(...)

    subtype: PlaceType = Field(..., description="Administrative level")
    parent_division_id: Optional[str] = Field(None, description="Parent ID")
```
