# Overture Schema Core

Core foundation package for Overture Maps Pydantic schemas.

## Overview

This package provides the essential infrastructure for building Overture Maps schema models:

- **OvertureFeature**: Abstract base class for all Overture features
- **Geometry Types**: Geometry handling with Shapely integration
- **Model Registry**: Infrastructure for registering and validating theme/type combinations

## Key Components

### OvertureFeature

Abstract base class for all Overture features with standard fields:

- `id`: Feature identifier
- `geometry`: Geometry data
- `theme`: Top-level theme name
- `type`: Feature type within theme
- `version`: Feature version number
- `sources`: Source attribution

Supports `ext_*` prefixed fields for schema extensions.

### Geometry

Wrapper around Shapely geometries supporting multiple input formats (GeoJSON, WKT, WKB) and dual
serialization modes (Shapely for `python` and GeoJSON for `json`).

### Model Registry

Infrastructure for registering and validating Pydantic models by theme and type.

## Installation

```bash
pip install overture-schema-core
```

## Usage

```python
from overture.schema.core.base import OvertureFeature, register_model

# Define a feature model
class MyFeature(OvertureFeature):
    name: str

# Register the model
register_model("my_theme", "my_type", MyFeature)
```
