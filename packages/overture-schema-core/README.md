# Overture Schema Core

Shared models and conventions for building Overture Maps feature types. Defines the base feature class all themes extend, a scoping framework for expressing conditional values (this speed limit applies *here*, *then*, to *these vehicles*), and common structures for names, sources, and cartographic hints.

## Installation

```bash
pip install overture-schema-core
```

## OvertureFeature

Every Overture feature type inherits from `OvertureFeature`, which extends `system.Feature` with the fields present on all Overture data: `id`, `theme`, `type`, `version`, `geometry`, and `sources`.

```python
from typing import Literal
from overture.schema.core import OvertureFeature

class Park(OvertureFeature[Literal["places"], Literal["park"]]):
    area_hectares: float | None = None
```

## Scoping

Many Overture values only apply under specific conditions -- a speed limit that holds during rush hour, along a sub-segment, in the forward direction. The `@scoped` decorator adds conditional fields to any Pydantic model:

```python
from pydantic import BaseModel
from overture.schema.core.scoping import Scope, scoped
from overture.schema.system.primitive import float32

@scoped(Scope.GEOMETRIC_RANGE, Scope.TEMPORAL)
class SpeedLimit(BaseModel):
    max_speed: float32
```

This produces a model with `between` (geometric range) and `when.during` (temporal) fields, both optional. The full set of scopes and the fields they inject:

| Scope                      | Field             |
|----------------------------|-------------------|
| `Scope.GEOMETRIC_POSITION` | `at`              |
| `Scope.GEOMETRIC_RANGE`    | `between`         |
| `Scope.HEADING`            | `when.heading`    |
| `Scope.TEMPORAL`           | `when.during`     |
| `Scope.TRAVEL_MODE`        | `when.mode`       |
| `Scope.PURPOSE_OF_USE`     | `when.using`      |
| `Scope.RECOGNIZED_STATUS`  | `when.recognized` |
| `Scope.SIDE`               | `side`            |
| `Scope.VEHICLE`            | `when.vehicle`    |

Scopes are optional by default. Make them mandatory via `required`:

```python
@scoped(Scope.TEMPORAL, required=(Scope.GEOMETRIC_POSITION, Scope.HEADING))
class TrafficSignal(BaseModel):
    signal_type: str
```

## Names

Multilingual naming with support for common names, name rules (official, alternate, short variants), and scoping by geometric range, side, or political perspective. Mix `Named` into a feature type to give it a `names` field:

```python
from typing import Literal
from overture.schema.core import OvertureFeature
from overture.schema.core.names import Named

class Lake(OvertureFeature[Literal["base"], Literal["water"]], Named):
    pass  # inherits names: Names | None from Named
```

Name rules support geometric range and side scoping for cases like a street whose name changes partway along or differs on each side. `NameRule` variants: `common`, `official`, `alternate`, `short`.

## Sources

Source attribution tracking. Each `SourceItem` identifies which dataset a feature or property came from, with optional license, record ID, update time, and confidence score. Source items support geometric range scoping for per-segment attribution.

```python
from overture.schema.core.sources import SourceItem

sources = [
    SourceItem(property="", dataset="OpenStreetMap"),
    SourceItem(property="/geometry", dataset="Microsoft ML Buildings"),
    # first 30% of the segment's geometry came from a different source
    SourceItem(property="/geometry", dataset="County GIS", between=[0, 0.3]),
]
```

## Cartography

Rendering hints for map-making: `prominence` (1--100 significance scale), `min_zoom`/`max_zoom` (tile zoom bounds), and `sort_key` (draw order). Mix `CartographicallyHinted` into a model to add a `cartography` field.

## Also Included

- **Types** -- domain-specific aliases built on system primitives: `ConfidenceScore` (0.0--1.0), `Level` (z-order), `FeatureVersion`.
- **Units** -- measurement enumerations: `SpeedUnit`, `LengthUnit`, `WeightUnit`.
- **Tag providers** -- `theme` provider for the discovery system in `overture-schema-system`. Tags `OvertureFeature`-derived models with `overture:theme={theme}`.
