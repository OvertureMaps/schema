# Overture Schema

Pydantic schemas for Overture Maps data structures.

## Overview

This project provides type-safe Python models for validating and working with [Overture Maps Foundation](https://overturemaps.org) data. The library uses a multi-package workspace architecture with theme-based namespaces, enabling modular development and extensibility.

## Packages

This workspace contains the following packages:

### Core Packages

- **`overture-schema`** - Main entrypoint package that aggregates all types for convenient usage
- **`overture-schema-core`** - Base classes, geometry models, and common structures shared across all themes
- **`overture-schema-validation`** - Validation system with constraints and mixins

### Theme Packages

- **`overture-schema-addresses-theme`** - Address features
- **`overture-schema-base-theme`** - Foundational geographic features (land, water, infrastructure, bathymetry, land cover, land use)
- **`overture-schema-buildings-theme`** - Building footprints and building parts with architectural details
- **`overture-schema-divisions-theme`** - Administrative boundaries, division areas, and political boundaries
- **`overture-schema-places-theme`** - Points of interest, businesses, and named locations
- **`overture-schema-transportation-theme`** - Road segments and transportation network connectors

### Usage Examples

```python
from overture.schema.buildings.building import Building
from overture.schema.places.place import Place
from overture.schema.transportation.segment import Segment

# Validate data
building = Building.model_validate(feature_data)
place = Place.model_validate(place_data)

# Extension development
from overture.schema.core import OvertureFeature
from overture.schema.validation.mixin import ValidationMixin
```

## Schema Extension

The library is designed to support data producer extensions through multiple patterns. This extensibility is a core feature that allows organizations to add custom fields and types while maintaining compatibility with the base Overture schema.

### Model Registration System

TODO this is out of date

The library uses a global model registry that enables modular packages while supporting centralized validation and schema generation:

```python
# Models register themselves on import
from overture.schema.core import OvertureFeature, register_model
from typing import Literal

class MyFeature(OvertureFeature):
    type: Literal["my_feature"] = "my_feature"
    custom_field: str

# Register when module is imported
register_model("places", "my_feature", MyFeature)
```

The registration system provides:

- **Import-time registration**: Models register automatically when modules are imported
- **Global registry**: Central mapping of `(theme, type)` tuples to Pydantic model classes
- **Explicit collection**: Tests and schema generation import all model modules to trigger registration

### Extension Patterns

#### New Columns

Add fields to existing types:

```python
from overture.schema.buildings.building import Building
from pydantic import Field

class ExtendedBuilding(Building):
    door_color: str = Field(description="Color of the building's front door")
    security_level: int = Field(ge=1, le=5, description="Security clearance level")
```

#### New Types

Create entirely new feature types:

```python
from overture.schema.core import OvertureFeature
from pydantic import Field
from typing import Literal

class EVCharger(OvertureFeature):
    """Electric vehicle charging station"""
    type: Literal["ev_charger"] = "ev_charger"
    connector_types: list[str] = Field(description="Available connector types")
    max_power_kw: float = Field(description="Maximum charging power in kilowatts")
    network_operator: str | None = Field(default=None)

# Register the new type
register_model("places", "ev_charger", EVCharger)
```

#### Value Expansion

Extend enums with additional values:

```python
from overture.schema.places.shared import PlaceCategory
from enum import Enum

class ExtendedPlaceCategory(PlaceCategory):
    """Extended categories including specialized types"""
    CRYPTOCURRENCY_ATM = "cryptocurrency_atm"
    DRONE_DELIVERY_HUB = "drone_delivery_hub"
```

### Development Experience

Extension authors typically:

1. **Depend on specific packages**: Import only the theme packages needed rather than the full `overture-schema` package
2. **Follow registration patterns**: Use `register_model()` to make extensions discoverable
3. **Test against examples**: Validate extensions using the same example/counterexample system
4. **Generate schemas**: Export JSON Schema for integration with other tools

```python
# Extension package structure
my_extension/
├── pyproject.toml  # Depends on specific overture-schema-* packages
└── src/
    └── my_extension/
        ├── models.py      # Extended/new models with registration
        └── __init__.py    # Import models to trigger registration
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
# Install dependencies for entire workspace
uv sync

# Run all tests across all packages
make test

# Run tests for specific package
uv run pytest packages/overture-schema-building-type/

# Run tests matching a pattern
uv run pytest -k "buildings"
```

Check code quality:

```shell
uv run ruff check
make mypy
```

Auto-format / fix code to align with project expectations:

```shell
uv run ruff check --fix
uv run ruff format
uv run docformatter --in-place --recursive packages/
```
