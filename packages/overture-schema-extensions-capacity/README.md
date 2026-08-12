# overture-schema-extensions-capacity

An example Overture schema **extension** package that demonstrates a *non-model* (scalar) extension.
It contributes a `capacity` field to both the `Place` and `Building` models.

## How it works

`Capacity` is a `NewType` over a constrained `uint8`, with `Extends(...)` metadata declaring its
target models via `typing.Annotated`:

```python
from typing import Annotated, NewType
from pydantic import Field
from overture.schema.buildings import Building
from overture.schema.places import Place
from overture.schema.system.extension import Extends
from overture.schema.system.primitive import uint8

Capacity = NewType(
    "Capacity",
    Annotated[uint8, Field(description="..."), Extends(Place, Building)],
)
```

It is registered as a normal model entry point:

```toml
[project.entry-points."overture.models"]
capacity = "overture.schema.extensions.capacity:Capacity"
```

At discovery time, `discover_models()` wraps it into a `CapacityExtension` model with a single
optional `capacity` field (preserving the `uint8` range constraint) and merges that field into both
`Place` and `Building`.
