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

# Validate a Python object (a dict or a model instance)
feature = validate({"type": "segment", "id": "...", "geometry": "..."})

# Validate a JSON document
feature = validate_json('{"type": "segment", "id": "...", "geometry": "..."}')
```

Both raise `pydantic.ValidationError` when the input matches no model. Which models participate is resolved at runtime by entry-point discovery, so installing additional Overture theme packages widens what these functions accept.
