# overture-schema-extensions-operating-hours

An example Overture schema **extension** package. It contributes an `operating_hours` field to the
`Place` model, demonstrating how a third-party package can extend an existing Overture model without
modifying its source.

## How it works

`OperatingHours` is a plain Pydantic model decorated with `@extends(Place)`:

```python
from overture.schema.places import Place
from overture.schema.system.extension import extends


@extends(Place)
class OperatingHours(BaseModel):
    primary: list[HourSet]
    rules: list[Rule] | None = None
```

It is registered as a normal model entry point:

```toml
[project.entry-points."overture.models"]
operating_hours = "overture.schema.extensions.operating_hours:OperatingHours"
```

At discovery time, `discover_models()` wraps the extension into a standalone wrapper model
(`OperatingHoursExtension`) and merges an optional `operating_hours` field into `Place`. The wrapper
can also validate extension-only payloads on its own, which is useful when extension data is stored
separately and joined to a base feature later.
