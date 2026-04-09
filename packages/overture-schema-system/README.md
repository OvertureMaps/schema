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

## Also Included

- **Optionality** -- `Omitable[T]` models JSON Schema's "may be absent but not null" semantics, which Pydantic's `T | None` conflates with nullable.
- **DocumentedEnum** -- base class for enumerations whose members carry their own docstrings, enabling code generation tools to produce documented output.
- **Metadata** -- internal key-value store used by model constraints to attach data to classes.
- **JSON Schema** -- schema generator that treats `T | None = None` as "omit when unset" rather than Pydantic's default "nullable with null default." Also handles unions of models.
