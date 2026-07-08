# Overture Schema System

Write Pydantic models once, get validated data that serializes correctly to JSON, Parquet, and Spark. This package provides the primitive types, constraint decorators, and GeoJSON-aware base class that make Pydantic models portable across serialization targets.

## Installation

```bash
pip install overture-schema-system
```

## Feature

GeoJSON-compatible Pydantic base model. Subclasses serialize to the GeoJSON format automatically -- `geometry` and `id` at the top level, everything else under `properties` -- and validate from it:

```python
from overture.schema.system.feature import Feature
from overture.schema.system.primitive import Geometry, float32

class Mountain(Feature):
    name: str
    max_elevation: float32

m = Mountain(
    geometry=Geometry.from_wkt("POINT(86.9252 27.9888)"),
    name="Mount Everest",
    max_elevation=8848.86,
)
```

## Primitive Types

Using `int` and `float` in a Pydantic model produces valid Python but loses information downstream -- an `int` field becomes a 64-bit integer in Parquet, Arrow, and Spark StructTypes, even when the domain is 0--255. The primitive types (`uint8`, `int32`, `float32`, etc.) carry range constraints and map to the correct wire type so data round-trips cleanly between Python, Parquet files, PostgreSQL, and JSON Schema:

```python
from pydantic import BaseModel
from overture.schema.system.primitive import uint8, float32

class Building(BaseModel):
    height: float32 | None = None
    num_floors: uint8 | None = None
```

Integer types: `uint8`, `uint16`, `uint32`, `int8`, `int16`, `int32`, `int64`. Float types: `float32`, `float64`. Geometry types: `Geometry`, `BBox`, `GeometryType`, `GeometryTypeConstraint`.

## String Types

Validated string types that carry their constraints into generated JSON Schemas and downstream code generation. Using `CountryCodeAlpha2` instead of `str` means Pydantic rejects `"USA"` at validation time, JSON Schema gets the right pattern, and codegen tools produce typed output:

```python
from overture.schema.system.string import CountryCodeAlpha2, LanguageTag
```

Available types: `CountryCodeAlpha2`, `RegionCode`, `LanguageTag`, `HexColor`, `JsonPointer`, `PhoneNumber`, `StrippedString`, `SnakeCaseString`, `NoWhitespaceString`, `WikidataId`.

## Field Constraints

Annotations for Pydantic fields that enforce domain rules beyond what the type alone expresses. Each constraint produces the corresponding JSON Schema keywords (e.g., `pattern`, `uniqueItems`) and is introspectable by code generation tools -- unlike Pydantic's `@field_validator`, which runs in Python only. Apply via `Annotated`:

```python
from typing import Annotated
from pydantic import BaseModel, Field
from overture.schema.system.field_constraint import UniqueItemsConstraint, PatternConstraint

OsmIdConstraint = PatternConstraint(
    pattern=r"^[nwr]\d+$",
    error_message="invalid OSM ID format: {value}. Must be n123, w123, or r123.",
)

class MyModel(BaseModel):
    osm_id: Annotated[str, OsmIdConstraint]
    tags: Annotated[list[str], UniqueItemsConstraint()] = Field(min_length=1)
```

Built-in constraints include `PatternConstraint`, `StrippedConstraint`, `UniqueItemsConstraint`, and all the string-type constraints (`CountryCodeAlpha2Constraint`, `HexColorConstraint`, etc.). All produce error messages with domain context.

## Model Constraints

Class-level decorators for cross-field validation -- relationships between fields that no single field annotation can express. Each decorator produces corresponding JSON Schema constructs (`if`/`then`, `anyOf`, etc.) and is introspectable for code generation:

```python
from pydantic import BaseModel
from overture.schema.system.model_constraint import require_any_of

@require_any_of("email", "phone")
class Contact(BaseModel):
    email: str | None = None
    phone: str | None = None
```

- `@require_any_of("a", "b", ...)` -- at least one field must be non-None
- `@require_any_true(cond1, cond2, ...)` -- at least one condition must evaluate to true
- `@radio_group("a", "b", ...)` -- at most one field may be truthy
- `@require_if("target", condition)` -- field required when condition holds
- `@forbid_if("target", condition)` -- field forbidden when condition holds
- `@min_fields_set(n, "a", "b", ...)` -- at least *n* fields must be set
- `@no_extra_fields` -- reject unrecognized fields (equivalent to `model_config = ConfigDict(extra="forbid")`)

## References

Foreign-key-style annotations that describe relationships between models. These carry no runtime enforcement but provide metadata for code generation and documentation tools:

```python
from typing import Annotated
from overture.schema.system.ref import Id, Identified, Reference, Relationship

class Park(Identified):
    pass

class ParkBench(Identified):
    park_id: Annotated[Id, Reference(Relationship.BELONGS_TO, Park)]
```

## Discovery

Packages register models on the `overture.models` Python entry point group. Each entry maps a name to a class import path:

```toml
[project.entry-points."overture.models"]
building      = "overture.schema.buildings:Building"
building_part = "overture.schema.buildings:BuildingPart"
```

`discover_models()` walks the group, loads each entry point, and returns a dict keyed by `ModelKey`. Consumers iterate over the result without knowing which package owns any given model -- the CLI and codegen tools both run discovery to assemble their working set.

A `ModelKey` carries the entry point `name`, its `entry_point` value (`"module:Class"`), and a `frozenset[str]` of tags. [Tagging](#tagging) is how those tags get attached.

## Tagging

Tags classify discovered models. A package registers [tag providers](#providers) on `overture.tag_providers`; when `discover_models` runs, it asks every provider which tags apply to each model and attaches the resulting set to its `ModelKey`. Downstream tools read those tags -- the CLI's `--tag` filter, codegen's grouping logic, anything that reasons about a model without importing it.

```python
from overture.schema.system.discovery import (
    TagSelector,
    discover_models,
    filter_models,
)

models = discover_models()

selected = filter_models(
    models,
    TagSelector(include_any=("feature",), exclude_any=("draft",)),
)
```

### Format

Tags follow `[namespace:]predicate[=value]`:

- **Plain** -- `feature`, `overture`
- **Namespaced** -- `system:extension`
- **Key/value** -- `overture:theme=buildings`

`:` separates namespace from predicate -- one level only, no nested colons. `=` introduces a discrete value, one per tag. Predicate and namespace parts are lowercase alphanumeric (with `_`, `.`, `-`); values also accept uppercase. Matching is case-sensitive throughout.

Helpers in `overture.schema.system.discovery.tag` parse structured tags:

- `is_valid_tag(tag)` -- check whether a string matches the format
- `get_namespace(tag)` -- extract the namespace prefix, or `""` for a plain tag
- `get_values_for_key(tags, "overture:theme")` -- extract values from k/v tags with the given key

### Providers

A tag provider is a callable registered on the `overture.tag_providers` entry point group. Discovery passes it the concrete `BaseModel` subclasses for the entry point and a copy of the tags accumulated so far; tags it adds are merged into the running set after passing the reservation checks below.

```python
from collections.abc import Iterable
from pydantic import BaseModel
from overture.schema.system.discovery import ModelKey
from overture.schema.system.feature import Feature

def feature_provider(
    types: Iterable[type[BaseModel]],
    key: ModelKey,
    tags: set[str],
) -> set[str]:
    if any(issubclass(tp, Feature) for tp in types):
        tags.add("feature")
    return tags
```

```toml
[project.entry-points."overture.tag_providers"]
feature = "overture.schema.system.discovery.tag_providers:feature_provider"
```

Tags from one provider are visible to providers that run later, but execution order is unspecified -- a provider must not depend on tags added by another. Provider exceptions are caught, logged, and discarded; they do not abort discovery.

Discovery resolves the entry-point value to concrete classes before invoking providers. For class entries that yields a one-element iterable; for discriminated-union features (e.g. `Segment`, which loads as `Annotated[Union[...], Field(...)]`) it yields every arm. Providers therefore work uniformly with `issubclass` and never need to walk type expressions themselves.

### Reservation

Specific plain tags and namespaces are reserved for designated packages. For example:

| Tag or namespace | Owning package |
|---|---|
| `feature` (tag) | `overture-schema-system` |
| `system:` (namespace) | `overture-schema-system` |
| `overture:` (namespace) | `overture-schema-common` |

When a provider attempts to set a reserved tag from an unauthorized package, discovery logs a warning and discards the tag.

### Built-in Providers

- **`feature`** (in `system`) -- adds `feature` if any concrete arm is a `Feature` subclass.
- **`theme`** (in `common`) -- adds `overture:theme={theme}` for each `OvertureFeature` referenced. A discriminated-union feature whose arms span multiple themes contributes one tag per distinct theme.

### Selecting Models by Tag

`filter_models(models, selector)` applies `TagSelector` predicates against each `ModelKey.tags`:

- `include_any` -- OR scope; at least one tag must match (empty: no scope filter)
- `require_all` -- AND narrowing; every tag must be present (empty: no narrowing)
- `exclude_any` -- OR-NOT subtraction; any match drops the model

An empty selector returns the input unchanged.

## Also Included

- **Optionality** -- `Omitable[T]` models JSON Schema's "may be absent but not null" semantics, which Pydantic's `T | None` conflates with nullable.
- **DocumentedEnum** -- base class for enumerations whose members carry their own docstrings, enabling code generation tools to produce documented output.
- **Metadata** -- internal key-value store used by model constraints to attach data to classes.
- **JSON Schema** -- schema generator that treats `T | None = None` as "omit when unset" rather than Pydantic's default "nullable with null default." Also handles unions of models.

## Baseline Testing

`overture.schema.system.testing` provides a pytest plugin for golden-file baseline tests of generated JSON Schemas. Implementers building feature packages use it to detect unintended schema drift.

### Helpers

- `assert_golden(actual, golden_path, *, update)` -- compare a string against a golden file. On mismatch, raises `AssertionError` with a unified diff. When `update=True`, writes `actual` to `golden_path` instead of comparing.
- `assert_json_schema_golden(model_or_union, golden_path, *, update)` -- generate the JSON Schema for a Pydantic model (or discriminated union type alias) via `overture.schema.system.json_schema` and delegate to `assert_golden`.

### Opting In

Activation is opt-in so the `--update-baselines` flag does not pollute pytest runs of packages that do not declare it. Add the plugin to your package's `pyproject.toml`:

```toml
[project.entry-points.pytest11]
overture_baselines = "overture.schema.system.testing.plugin"
```

The plugin registers:

- `--update-baselines` -- pytest CLI flag.
- `update_baselines` -- bool fixture, true when the flag is passed.

### Writing a Baseline Test

```python
from pathlib import Path

import pytest
from overture.schema.system.testing import assert_json_schema_golden

from yourpackage import Mountain  # the model you're locking down

GOLDEN = Path(__file__).parent / "mountain_baseline_schema.json"


@pytest.mark.baseline
def test_mountain_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Mountain, GOLDEN, update=update_baselines)
```

Convention: the golden file lives next to the test, named `<feature>_baseline_schema.json`.

Mark each baseline test with `@pytest.mark.baseline` so it can be selected or skipped via `pytest -m baseline` / `pytest -m "not baseline"`. Register the marker in your pyproject:

```toml
[tool.pytest.ini_options]
markers = [
    "baseline: golden file baseline tests",
]
```

### Updating Baselines

After an intentional schema change:

```bash
pytest -m baseline --update-baselines
```

Inspect `git diff` on the regenerated golden files to confirm the changes are intended before committing.
