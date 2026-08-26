# overture-schema-validation

Validate data against the union of all discovered Overture Maps models.

This package provides `validate` and `validate_json`, which check a Python object or JSON document against every Overture model registered on the `overture.models` entry point and return the matching validated model instance.

## Installation

```bash
pip install overture-schema-validation
```

## Usage

```python
from overture.schema.validation import validate, validate_json

# A Python object -- the flat, tabular (Parquet-style) shape
feature = validate(feature_row)

# A JSON document -- GeoJSON
feature = validate_json(geojson_text)
```

The two entry points are not interchangeable. `validate` runs Pydantic's Python mode, which reads the flat column layout of the Parquet release -- the shape Overture publishes. `validate_json` runs JSON mode, which reads the GeoJSON representation the models support for compatibility with tools that expect features rather than rows. Handing a GeoJSON dict to `validate` reports `theme` and `version` missing and `type` set to `'Feature'`.

Both raise `pydantic.ValidationError` when the input matches no model. Which models participate is resolved at runtime by entry-point discovery, so installing additional Overture theme packages widens what these functions accept.
