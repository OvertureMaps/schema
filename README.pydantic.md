# Overture Schema

[Pydantic](https://docs.pydantic.dev/latest/) schemas for [Overture Maps
data](https://docs.overturemaps.org/guides/).

## Overview

This project provides type-safe Python models for validating and working with [Overture
Maps Foundation](https://overturemaps.org/) data. Overture Maps is an open geospatial
dataset containing buildings, places, addresses, transportation networks, and
administrative boundaries curated from multiple sources.

Use these schemas to:

- Validate Overture Maps data
- Build data processing pipelines with type safety
- Extend schemas with custom fields and validation rules

## Why Use Pydantic to Define Data Schemas?

This project addresses a fundamental challenge in data consumption: **bridging the
semantic gap between raw data and human understanding** while enabling
machine-actionable workflows.

### Why Schema at All: Beyond Raw Data

Take a column like `pop_2020`. Is it total population? Population density per square
kilometer? Working-age population? Without a schema, you're left sampling values and
guessing from column names.

Compare this to OpenStreetMap's approach: features use well-known key/value pairs like
`building=residential` or `addr:housenumber=42` that have semantic meaning and can be
looked up on the OSM wiki. This creates a step toward a schema - shared vocabulary with
documented semantics used across a vast dataset. However, OSM tags remain free-form:
multiple valid ways to express the same concept, no built-in validation, and complex
downstream validation because of undocumented keys that might have meaning to someone,
somewhere. A schema provides the structured alternative: explicit types, clear
validation rules, and semantic meaning that both humans and systems can rely on.

Data files containing only column names and values aren't fully documented. External
metadata files typically focus on how data was collected and encoded, not on semantic
meaning or validation rules. Data consumers struggle to understand what datasets contain
and which columns they need for their goals.

### Why Pydantic Over JSON Schema: Solving Multiple Problems

We initially chose JSON Schema because it aligned with our mental model and promised to
solve our problems as we understood them. But JSON Schema surfaced several pain points:

- **Authoring difficulty**: Hard to write correctly, difficult to verify, limited IDE
  support, no refactoring capabilities
- **Tooling gaps**: Generic tools can't tailor output for specific applications like
  ours
- **Development friction**: Schema changes required manual coordination across multiple
  artifacts

Pydantic addresses these systematically: author in Python with full IDE support,
generate tailored documentation, and automatically produce the specific artifacts each
workflow needs. Pydantic can also produce JSON Schema, so any application that requires
it can use it while we gain all the Python benefits during authoring.

### The Result: Faster Understanding, Higher Quality

Instead of spending time deciphering what columns mean and whether data matches
expectations, users can focus on their actual goals: analysis, visualization,
integration. Quality improves because validation happens automatically rather than
through manual inspection.

The fundamental approach - human-readable authoring that generates machine-actionable
outputs - has broader applications beyond Overture and geospatial data. We hope others
will adapt these patterns for linking with Overture data or modeling their own domains
entirely.

## Getting Started

- Install [Python](https://www.python.org/downloads/) 3.10 or newer
- Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- Clone this repository: `git clone https://github.com/OvertureMaps/schema.git`
- Install dependencies: `uv sync --all-packages`
- Run tests to ensure that everything is configured correctly: `make check` (on Windows,
  without `make`: `uv run pytest packages`)

## Packages

This workspace contains the following packages:

### Core Packages

- **`overture-schema`** - Main entrypoint package that aggregates all types for
  convenient usage
- **`overture-schema-core`** - Base classes, geometry models, and common structures
  shared across all themes
- **`overture-schema-system`** - Foundational system of primitive types and constraints

### Theme Packages

- **`overture-schema-addresses-theme`** - Address features
- **`overture-schema-base-theme`** - Foundational geographic features (land, water,
  infrastructure, bathymetry, land cover, land use)
- **`overture-schema-buildings-theme`** - Building footprints and building parts with
  architectural details
- **`overture-schema-divisions-theme`** - Administrative boundaries, division areas, and
  political boundaries
- **`overture-schema-places-theme`** - Points of interest, businesses, and named
  locations
- **`overture-schema-transportation-theme`** - Road segments and transportation network
  connectors

### Usage (Python)

Install the main package using `pip` (or your package manager of choice):

```shell
pip install overture-schema
```

```python
from overture.schema.buildings.building import Building
from overture.schema.places.place import Place
import json

# Validate data - supports both flat/tabular- (Parquet-style) and GeoJSON-formatted
# dicts
building = Building.model_validate(feature_data)
building_geojson = Building.model_validate(geojson_feature)

# Parse and validate JSON strings
building_from_json = Building.model_validate_json(json_string)

# Convert to GeoJSON format
geojson_output = building.model_dump(mode="json")
```

## Schema Extension

The library is designed to support data producer extensions through multiple patterns.
This extensibility is a core feature that allows organizations to add custom fields and
types while maintaining compatibility with the base Overture schema. We are in the
process of determining how this should work.

### Model Registration via Entry Points

Models are registered using [setuptools entry
points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html) in each
package's `pyproject.toml` file. This enables automatic discovery and loading of models
at runtime without requiring explicit imports.

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
# Install dependencies for the entire workspace
uv sync --all-packages

# Run all tests and type/code quality checks
make check

# Run tests for a specific package
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
