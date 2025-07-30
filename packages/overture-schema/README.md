# overture-schema

Overture Maps schema test harness and validation framework.

This package provides testing infrastructure for Overture Maps Pydantic schemas. It includes a pytest-based test harness that validates schema models against curated examples and counterexamples.

## Installation

```bash
pip install overture-schema
```

## Usage

This package serves as a test harness and validation framework. Import specific schemas from their
respective theme packages:

```python
# Addresses theme
from overture.schema.addresses import Address
```

TK

```python
from overture.schema import Types # returns a Union annotated for use by Pydantic as a discriminated union
```

### JSON Schema

TK

```python
from overture.schema import Types, json_schema

# TODO output JSON
print(json_schema(Types))
```

### Utilities

The package includes test utilities for:

- Loading and parsing GeoJSON and YAML test files
- Converting between GeoJSON and flat/tabular data formats
- Deep comparison of validation results

## Schema Validation

All models are validated to test:

- Geometry validation for GeoJSON-compatible structures
- Theme and type consistency checking
- Field-level constraints (country codes, language tags, etc.)
- Cross-field validation rules
- Source attribution validation

## Extension

TK using setuptools entry points

## Testing

This package includes test suites that validate schemas against curated examples and counterexamples. Tests ensure that:

- Valid examples pass validation
- Invalid counterexamples properly fail validation
- Schemas work with both GeoJSON and flat/tabular data formats

Run tests with:

```bash
uv run pytest
```
