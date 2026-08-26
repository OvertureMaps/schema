# overture-schema

Type-safe Python models for [Overture Maps Foundation](https://overturemaps.org/) data.

This package provides Pydantic models for validating and working with Overture Maps data, including buildings, places, addresses, transportation networks, and administrative boundaries.

## Installation

```bash
pip install overture-schema
```

`overture-schema` is a metapackage: it pulls in every theme package plus the
validation library and the CLI, and ships no code of its own. `overture.schema`
is a namespace root, so import from the theme and system packages rather than
from `overture.schema` directly.

## Usage

Import models from the theme package that defines them:

```python
from overture.schema.buildings import Building
from overture.schema.places import Place
```

### Tabular data, and GeoJSON for compatibility

Overture publishes data in one shape: flat and tabular -- the column layout of the
Parquet release, with `theme`, `type`, and `version` as top-level columns and
geometry as WKT. That is what **Python mode** (`model_validate`) reads.

The models also accept and emit GeoJSON, through **JSON mode**
(`model_validate_json`), so the schema works with tools that expect features
rather than rows. The generated JSON Schema describes that representation.

The modes are not interchangeable. Passing a GeoJSON dict to `model_validate`
reports `theme`/`version` missing and `type` set to `'Feature'`, because it is
reading GeoJSON keys as flat columns.

```python
# Flat / tabular (Parquet-shaped) dict
building = Building.model_validate(feature_row)

# GeoJSON -- JSON mode, from a string or bytes
building = Building.model_validate_json(geojson_text)

# Serialize back to GeoJSON. by_alias=True is required: without it,
# aliased fields serialize under their Python names (`class_`, not
# `class`) and the output will not re-validate.
geojson_output = building.model_dump(mode="json", by_alias=True, exclude_none=True)
```

### Available Models

Each model lives in its theme package. The metapackage installs all of them:

```python
from overture.schema.addresses import Address
from overture.schema.base import (
    Bathymetry,
    Infrastructure,
    Land,
    LandCover,
    LandUse,
    Water,
)
from overture.schema.buildings import Building, BuildingPart
from overture.schema.divisions import Division, DivisionArea, DivisionBoundary
from overture.schema.places import Place
from overture.schema.transportation import Connector, Segment
```

`Segment` is a discriminated union alias rather than a class, so it validates
through a `TypeAdapter`:

```python
from pydantic import TypeAdapter

segments = TypeAdapter(Segment)
segment = segments.validate_json(geojson_text)
```

### Validating without knowing the type

`overture-schema-validation` validates against the union of every installed
model, picking the right one from the data:

```python
from overture.schema.validation import validate, validate_json

feature = validate(feature_row)  # flat / tabular dict
feature = validate_json(geojson_text)  # GeoJSON
```

### Discovering models programmatically

Discovery lives in `overture-schema-system`. `discover_models()` returns a dict
keyed by `ModelKey` -- entry point `name`, its `entry_point` value, and the set
of tags attached during discovery:

```python
from overture.schema.system.discovery import discover_models, get_registered_model

all_models = discover_models()
# {
#   ModelKey(name="building", entry_point="overture.schema.buildings:Building",
#            tags=frozenset({"feature", "overture", "overture:theme=buildings"})): Building,
#   ModelKey(name="place", entry_point="overture.schema.places:Place",
#            tags=frozenset({"feature", "overture", "overture:theme=places"})): Place,
#   ...
# }

building_model = get_registered_model("building")  # None if not installed
```

### Generating JSON Schema

```python
from overture.schema.system.json_schema import json_schema

schema = json_schema(Building)
union_schema = json_schema(Building | Place)  # emits an anyOf
```

See the [`overture-schema-system` README](../overture-schema-system/README.md)
for tag format, tag providers, and the discovery API in full.
