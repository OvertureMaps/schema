# overture-schema

Type-safe Python models for [Overture Maps Foundation](https://overturemaps.org/) data.

This package provides Pydantic models for validating and working with Overture Maps data, including buildings, places, addresses, transportation networks, and administrative boundaries.

## Installation

```bash
pip install overture-schema
```

## Usage

Import and use schemas:

```python
from overture.schema import Building, Place
import json

# Validate Overture Maps data (supports both flat/tabular and GeoJSON formats)
building = Building.model_validate(feature_data)
place = Place.model_validate(geojson_feature)

# Parse and validate JSON strings
building_from_json = Building.model_validate_json(json_string)

# Convert to GeoJSON format for output
geojson_output = building.model_dump(mode="json")
```

### Available Models

```python
# All models are re-exported from their respective theme packages for convenience
from overture.schema import (
    # Addresses theme
    Address,

    # Base theme
    Bathymetry,
    Infrastructure,
    Land,
    LandCover,
    LandUse,
    Water,

    # Buildings theme
    Building,
    BuildingPart,

    # Divisions theme
    Division,
    DivisionArea,
    DivisionBoundary,

    # Places theme
    Place,

    # Transportation theme
    Connector,
    Segment,
)
```

### Utility Functions

The package also exports several utility functions:

```python
from overture.schema import parse, discover_models, json_schema
from overture.schema import Building

# Parse any Overture feature (auto-discovers all registered models)
validated_feature = parse(feature_data, mode="json")    # Parses GeoJSON format
validated_feature = parse(feature_data, mode="python")  # Parses flat format

# Discover all registered models programmatically
all_models = discover_models()
# Returns:
# {
#   ("buildings", "building"): BuildingModel,
#   ("places", "place"): PlaceModel,
# ...
# }

# Generate JSON Schema for models or unions
schema = json_schema(Building)
union_schema = json_schema(Building | Place)  # Works with unions too
```
