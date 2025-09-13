# Overture Schema

[Pydantic](https://docs.pydantic.dev/latest/) schemas for [Overture Maps data](https://docs.overturemaps.org/guides/).

## Overview

This project provides type-safe Python models for validating and working with [Overture Maps Foundation](https://overturemaps.org/) data. Overture Maps is an open geospatial dataset containing buildings, places, addresses, transportation networks, and administrative boundaries curated from multiple sources.

Use these schemas to:

- Validate Overture Maps data
- Build data processing pipelines with type safety
- Extend schemas with custom fields and validation rules

## Getting Started

- Install [Python](https://www.python.org/downloads/) 3.10 or newer
- Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- Clone this repository: `git clone https://github.com/OvertureMaps/schema.git`
- Install dependencies: `uv sync --all-packages`
- Run tests to ensure that everything is configured correctly: `make check` (on Windows, without `make`: `uv run pytest packages`)

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

### Usage (Python)

Install the main package using `pip` (or your package manager of choice):

```shell
pip install overture-schema
```

```python
from overture.schema.buildings.building import Building
from overture.schema.places.place import Place
import json

# Validate data - supports both flat/tabular- (Parquet-style) and GeoJSON-formatted dicts
building = Building.model_validate(feature_data)
building_geojson = Building.model_validate(geojson_feature)

# Parse and validate JSON strings
building_from_json = Building.model_validate_json(json_string)

# Convert to GeoJSON format
geojson_output = building.model_dump(mode="json")
```

## Schema Extension

The library is designed to support data producer extensions through multiple patterns. This extensibility is a core feature that allows organizations to add custom fields and types while maintaining compatibility with the base Overture schema. We are in the process of determining how this should work.

### Model Registration via Entry Points

Models are registered using [setuptools entry points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html) in each package's `pyproject.toml` file. This enables automatic discovery and loading of models at runtime without requiring explicit imports.

Registration is done in the `[project.entry-points."overture.models"]` section:

```toml
[project.entry-points."overture.models"]
"buildings.building" = "overture.schema.buildings.building.models:Building"
"buildings.building_part" = "overture.schema.buildings.building_part.models:BuildingPart"
```

The discovery system provides programmatic access to registered models:

```python
from overture.schema.core.discovery import discover_models, get_registered_model

# Discover all registered models
all_models = discover_models()
# Returns:
# {
#   ("buildings", "building"): BuildingModel,
#   ("places", "place"): PlaceModel,
# ...
# }

# Get a specific model by theme and type
building_model = get_registered_model("buildings", "building")
if building_model:
    # Use the model class
    building = building_model.model_validate(building_data)
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
# Install dependencies for entire workspace
uv sync --all-packages

# Run all tests and type/code quality checks
make check

# Run tests for specific package
uv run pytest packages/overture-schema-buildings-theme/

# Run tests matching a pattern
uv run pytest -k "buildings"
```

Auto-format / fix code to align with project expectations:

```shell
uv run ruff check --fix
uv run ruff format
uv run docformatter --in-place --recursive packages/
```
