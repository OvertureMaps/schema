# Writing models

Read this guide if you write Pydantic models that work with the Overture tools, either for
Overture's themes or as feature types of your own. You should know Python classes and type
hints. Use it to write a model, package and register it so the tools find it, and start
from a template. If you're on Overture staff or at a member organization and changing the
schema repository, also read [CONTRIBUTING.md](../CONTRIBUTING.md).

Every code block in this guide runs against the repository, and
`tests/test_documented_imports.py` checks that its imports resolve.

## Write a model

### Imports

These imports cover most models:

```python
# Basic Python types
from typing import Annotated, Literal
from enum import Enum

# Pydantic essentials
from pydantic import BaseModel, Field

# Overture common models
from overture.schema.common import OvertureFeature
from overture.schema.system.geometric import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)

# Validation system
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields

# Common types
from overture.schema.system.string import (
    CountryCodeAlpha2,
    NoWhitespaceString,
    StrippedString,
)
from overture.schema.common.confidence import ConfidenceScore
from overture.schema.system.string import LanguageTag

# Numeric types (use these instead of int/float)
from overture.schema.system.numeric import (
    int8,
    int32,
    int64,
    uint8,
    uint16,
    uint32,
    float32,
    float64,
)
```

### Base classes

A model gets every field of the classes it inherits from. When two parents define a field
with the same name, Python's
[method resolution order](https://docs.python.org/3/tutorial/classes.html#multiple-inheritance)
decides which definition wins.

Build a structure that appears inside a feature, such as an address or a source record, on
`BaseModel`. Add `@no_extra_fields` so the model rejects fields it doesn't define:

```python
from overture.schema.system.model_constraint import no_extra_fields


@no_extra_fields
class Address(BaseModel):
    """A postal address - no extra fields allowed."""

    street: str
    city: str
    postal_code: str | None = None
    # Any field not defined here will cause validation to fail
```

Build a feature type on `OvertureFeature`. It has the fields every Overture feature needs:
`id`, `theme`, `type`, `geometry`, `bbox`, `version` and `sources`.

```python
from typing import Literal
from overture.schema.common import OvertureFeature
from overture.schema.system.numeric import float64


class Building(OvertureFeature[Literal["buildings"], Literal["building"]]):
    """A building feature with strongly-typed theme and type."""

    # Inherits: id, theme, type, geometry, bbox, version, sources
    height: float64 | None = None
```

`OvertureFeature` takes two type parameters: the theme and the type. Write each one as a
`Literal`, so the field accepts only that value.
`OvertureFeature[Literal["buildings"], Literal["building"]]` is a feature whose `theme`
must be `"buildings"` and whose `type` must be `"building"`.

To combine fields from several classes, inherit from all of them:

```python
from typing import Literal
from overture.schema.common import OvertureFeature
from overture.schema.common.level import Stacked
from overture.schema.common.names import Named
from overture.schema.system.numeric import float64


class Building(
    OvertureFeature[Literal["buildings"], Literal["building"]], Named, Stacked
):
    # Gets fields from Feature: id, theme, type, geometry, etc.
    # Gets fields from Named: names
    # Gets fields from Stacked: level
    # Plus its own fields:
    height: float64 | None = None
```

### Field aliases

When a field's name in the data is a Python keyword, such as `class`, give the model
attribute a different name and set the name in the data with `Field(alias=...)`:

```python
from typing import Annotated
from pydantic import Field


class Building(OvertureFeature):
    # Use class_ in Python code, but "class" in the actual data
    class_: Annotated[str | None, Field(alias="class")] = None

    # Other common cases might include:
    type_: Annotated[str | None, Field(alias="type")] = None  # if type conflicts
    from_: Annotated[str | None, Field(alias="from")] = None  # from is a keyword
```

The model attribute is `class_`, and the field in the data is `class`. When you write data
back out, pass `by_alias=True` so the output uses `class`.

### Required and optional fields

```python
class Building(OvertureFeature):
    # Required field (no default value)
    geometry: Geometry

    # Optional field (has default value of None)
    height: float64 | None = None
```

A field with no default is required. A field with a default is optional, and the data can
leave it out.

> [!WARNING]
> Give every optional field a default of `None`.

A default other than `None` causes three problems. Pydantic fills in defaults that weren't
in the input, so you can't tell the original data from the schema's defaults. The schema
is used to validate data as well as to process it, and validation shouldn't change the
data. And a default puts a business rule, what a missing value means, into the schema.

Instead, use `None`, and say in the field's description what a missing value means:

```python
access_policy: Annotated[
    str | None,
    Field(description="Access policy for the place. When absent, assume 'open'"),
] = None
```

If your pipeline needs a value, set it there:

```python
# In your data processing pipeline, always set the value
place.access_policy = place.access_policy or "open"
```

The schema describes the structure of the data. Rules about what a missing value means
belong in the code that uses the data.

### Numeric types

Use the schema's numeric types instead of Python's `int` and `float`:

```python
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.numeric import (
    int8,
    int32,
    int64,  # Signed integers
    uint8,
    uint16,
    uint32,  # Unsigned integers
    float32,
    float64,  # Floating point
)


@no_extra_fields
class MyModel(BaseModel):
    # Signed integers with specific ranges
    level: int8 | None = None  # -128 to 127
    year: int32 | None = None  # -2,147,483,648 to 2,147,483,647
    timestamp: int64 | None = None  # Full 64-bit range

    # Unsigned integers (0 and positive only)
    red_value: uint8 | None = None  # 0 to 255 (like RGB values)
    port: uint16 | None = None  # 0 to 65,535 (like network ports)
    population: uint32 | None = None  # 0 to 4,294,967,295

    # Floating point numbers
    height: float64 | None = None  # Double precision (recommended)
    ratio: float32 | None = None  # Single precision
```

Each type declares a width. The width decides which column type the field becomes in
Parquet and Arrow and which range of values it accepts, so the same data round-trips
between Python, Parquet, databases and JSON Schema. A `uint8` takes 1 byte, where an
`int64` takes 8.

Use `int32` for most whole numbers, such as years and counts, and `float64` for most
decimal numbers, such as heights and measurements. When values can't be negative, use the
smallest unsigned type whose range fits: `uint8`, `uint16` or `uint32`. Use `float32` only
when space matters more than precision. Use `int64` only when values can exceed the range
of `int32`, because JavaScript, and so many JSON tools,
[can't represent every 64-bit integer exactly](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER).

### Union types

A union lets a field accept more than one type. Write it with `|`:

```python
from typing import Literal


class Building(OvertureFeature):
    # This field can be either a string OR None (most common union)
    name: str | None = None

    # This field can be one of specific string values OR None
    status: Literal["active", "inactive", "pending"] | None = None
```

These are the unions you'll write most often:

```python
# Optional field (most common union)
height: float64 | None = None  # Can be a number or missing

# Specific string values (an alternative to enums where descriptions aren't needed)
priority: Literal["low", "medium", "high"] | None = None

# Boolean or None
is_verified: bool | None = None
```

Keep unions small. Don't mix base types, as in `str | int32`, because Parquet and other
storage formats can't store a column that holds more than one type. Use `Literal` values
or separate fields instead.

### Descriptions and constraints

Use `Annotated` to attach a description and constraints to a field's type. The first
argument is the type, and the rest are metadata, such as `Field()` and constraint objects.
See the [Python docs on `Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated).

```python
from typing import Annotated
from pydantic import Field

# Without Annotated - just the type
height: float64 | None = None

# With Annotated - type + extra information
height: Annotated[
    float64 | None,  # The actual type (what kind of data)
    Field(description="Height in meters"),  # Extra metadata
] = None
```

Use Pydantic's `Field()` to add constraints. For numbers:

```python
from typing import Annotated
from pydantic import Field


class Building(OvertureFeature):
    # Range constraints
    height: Annotated[
        float64 | None, Field(ge=0, le=1000, description="Height in meters (0-1000m)")
    ] = None

    # Integer constraints
    floors: Annotated[
        int32 | None, Field(gt=0, lt=200, description="Number of floors (1-199)")
    ] = None
```

`ge` means greater than or equal to, `gt` greater than, `le` less than or equal to, and
`lt` less than.

For strings:

```python
class Place(OvertureFeature):
    # Length constraints
    name: Annotated[
        str | None,
        Field(min_length=1, max_length=100, description="Place name (1-100 chars)"),
    ] = None

    # Pattern matching
    postal_code: Annotated[
        str | None, Field(pattern=r"^\d{5}(-\d{4})?$", description="US postal code")
    ] = None
```

For strings, `min_length` and `max_length` limit the length, and `pattern` takes a regular
expression.

### Constraints instead of validators

Write rules as constraints from `overture.schema.system`, not with Pydantic's
`@field_validator` or `@model_validator` decorators. The JSON Schema generator and the
code generator can read constraints, but they can't see the rules inside a validator
function:

```python
# Don't do this
@field_validator("categories")
def validate_categories_unique(cls, v):
    if v and len(v) != len(set(v)):
        raise ValueError("Categories must be unique")
    return v


# Do this instead
from overture.schema.system.field_constraint import UniqueItemsConstraint


class Building(OvertureFeature):
    categories: Annotated[
        list[str] | None,
        Field(min_length=1, description="Building categories"),
        UniqueItemsConstraint(),
    ] = None
```

### Lists

A list field holds a list of values or of models:

```python
class Building(Feature):
    # Simple list of strings
    tags: list[str] | None = None

    # List of complex objects
    access_rules: list[AccessRule] | None = None
```

To limit the length of a list or require unique items, add constraints:

```python
from overture.schema.system.field_constraint import UniqueItemsConstraint


class Building(OvertureFeature):
    # List with size and uniqueness constraints
    categories: Annotated[
        list[str] | None,
        Field(min_length=1, max_length=10, description="1-10 categories"),
        UniqueItemsConstraint(),  # Must come AFTER Field()
    ] = None
```

`min_length` and `max_length` limit the number of items, and `UniqueItemsConstraint()`
rejects duplicates.

> [!CAUTION]
> Put `Field()` before `UniqueItemsConstraint()`. Pydantic reads the annotations in
> order. With `Field()` first, it applies `min_length` to the list and writes `minItems` in
> the JSON Schema. With `UniqueItemsConstraint()` first, it treats `min_length` as a string
> constraint and writes `minLength`.

### Enums

An enum defines a fixed set of allowed values. A `Literal`, such as
`Literal["active", "inactive"]`, does the same for a single field. Use an enum when the
values need descriptions or when more than one field uses them:

```python
from enum import Enum


class BuildingClass(str, Enum):
    """Further delineation of the building's built purpose."""

    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    CIVIC = "civic"


# Usage in a model
class Building(OvertureFeature):
    class_: Annotated[BuildingClass | None, Field(alias="class")] = None
```

#### Documented enums

When enum members need their own descriptions, for generated docs and code, use
`DocumentedEnum` from `overture.schema.system.doc`. Give each documented member a
`(value, description)` tuple:

```python
from overture.schema.system.doc import DocumentedEnum


class VehicleType(str, DocumentedEnum):
    """Types of vehicles for transportation."""

    CAR = ("car", "Standard passenger vehicle")
    TRUCK = ("truck", "Commercial freight vehicle")
    BICYCLE = ("bicycle", "Human-powered two-wheeler")
    MOTORCYCLE = ("motorcycle", "Motorized two-wheeler")
```

Members without a description use the plain value, so you can document only the members
that need it:

```python
class ConnectionState(str, DocumentedEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    QUIESCING = (
        "quiescing",
        "Gracefully shutting down, rejecting new requests but completing existing ones",
    )
```

Use `DocumentedEnum` when the meaning of a member isn't clear from its name. Use a plain
`str, Enum` when every value explains itself. Inheriting from `str` makes each member work
as a string too, which keeps JSON serialization simple.

### Relationships

A relationship links one feature or model to another: for example, a building part to its
building, or a division area to its division. To model one, first choose its type, then
choose how to write it.

#### Relationship types

The schema defines four relationship types, from the strongest coupling to the weakest.
Each type describes how the two features depend on each other: whether one owns the
other, and whether one can exist without the other. The type doesn't say which feature is
the parent. The feature that has the reference is the source, and the type it refers to is
the target.

##### `COMPOSITION`

The part belongs to a whole and means nothing without it. If you delete the whole, the
part is no longer valid. Use `COMPOSITION` if keeping the part after you delete the whole
would make no sense.

**Examples:**
- `BuildingPart` → `Building`: part *is part of* building
- `DivisionBoundary` → `Division`: boundary line *defines the boundary of* division

##### `AGGREGATION`

The features form a group or collection, and each member is valid on its own. A member
can move to another group, or belong to no group, and still be valid. Use `AGGREGATION`
if both sides could belong to something else, or to nothing, and still be valid map
features.

**Examples:**
- `Route` → `Segment`: route *groups* segments
- `TrailSegment` → `NationalPark`: segment *is grouped by* park

##### `HIERARCHY`

One feature is nested under another for administrative or classification reasons, not
because it's physically part of it. Use `HIERARCHY` for administrative parents,
taxonomies and categories.

**Examples:**
- `DivisionArea` → `Division`: area *is child of* division
- `Division` → `Division`: child division nested under parent

##### `ASSOCIATION`

The two features are peers. Neither owns, contains or nests under the other. Use
`ASSOCIATION` when none of the stronger types applies.

**Examples:**
- `Segment` → `Connector`: segment references its start/end connector
- `Building` → `Address`: a building references its address, neither owns the other

#### Choosing a relationship type

When a relationship could fit more than one type, start with `COMPOSITION`. If it doesn't
fit, choose between `AGGREGATION` and `HIERARCHY` by the kind of coupling. Use
`ASSOCIATION` only when no stronger type applies.

```text
    COMPOSITION
       / \
AGGREGATION  HIERARCHY
       \ /
    ASSOCIATION
```

| If the relationship implies...                          | Use            |
|---------------------------------------------------------|----------------|
| Structural whole-part with lifecycle dependency         | `COMPOSITION`  |
| Geometric boundary definition (lifecycle dependent)     | `COMPOSITION`  |
| Grouping/collection without lifecycle dependency        | `AGGREGATION`  |
| Organizational nesting or classification tree           | `HIERARCHY`    |
| Peer-level reference, no ownership or nesting           | `ASSOCIATION`  |

#### The `role` parameter

The `Reference` annotation takes an optional `role`: a snake_case string that says more
about the relationship from the source's side. It doesn't affect validation. Documentation
and tools use it. Use `role` when the type alone is ambiguous, for example when a model has
more than one `HIERARCHY` reference:

```python
# Without role, two HIERARCHY references to Division: which is which?
parent_division_id: Annotated[Id, Reference(Relationship.HIERARCHY, Division)]
capital_division_ids: Annotated[list[Id], Reference(Relationship.HIERARCHY, Division)]

# With role: unambiguous
parent_division_id: Annotated[
    Id, Reference(Relationship.HIERARCHY, Division, role="child_of")
]
capital_division_ids: Annotated[
    list[Id], Reference(Relationship.HIERARCHY, Division, role="has_as_capital")
]
```

A `role` MUST be a non-empty snake_case string of lowercase letters, digits and
underscores. Phrase it from the source's side, as the source's role relative to the target.

#### Ways to write a relationship

Write a relationship as a direct reference, an association feature, or a list of
references.

##### Direct references

In a direct reference, one feature points to another with an ID field. The `Reference`
annotation records the relationship type and the target.

```python
from typing import Annotated, Literal
from pydantic import Field
from overture.schema.common import OvertureFeature
from overture.schema.system.ref import Id, Reference, Relationship


# COMPOSITION: part points to its whole
class BuildingPart(OvertureFeature[Literal["buildings"], Literal["building_part"]]):
    """A structural part of a building."""

    building_id: Annotated[
        Id,
        Reference(Relationship.COMPOSITION, Building, role="part_of"),
        Field(description="The building to which this part belongs"),
    ]


# HIERARCHY: child points to parent
class DivisionArea(OvertureFeature[Literal["divisions"], Literal["division_area"]]):
    """Area polygon nested under a division."""

    division_id: Annotated[
        Id,
        Reference(Relationship.HIERARCHY, Division, role="child_of"),
        Field(description="Division ID of the parent division of this area."),
    ]


# ASSOCIATION: peer reference, no ownership
class ConnectorReference(BaseModel):
    """Reference to a connector feature."""

    connector_id: Annotated[
        Id, Reference(Relationship.ASSOCIATION, Connector, role="connects_to")
    ]
```

##### Association features

When the relationship has information of its own, make it a separate feature. This works
for any of the four relationship types. "Building part A is part of building B" needs only
an ID reference. "Admin area X has city center Y as its primary center since 2010, with 85%
confidence" has properties of its own, so it needs an association feature:

```python
class AdminCityCenterAssociation(
    OvertureFeature[Literal["associations"], Literal["admin_city_center"]]
):
    """Describes how an administrative area relates to a city center."""

    admin_area_id: Annotated[Id, Reference(Relationship.ASSOCIATION, AdminArea)]
    city_center_id: Annotated[Id, Reference(Relationship.ASSOCIATION, CityCenter)]

    # Information about the relationship itself
    relationship_type: Literal["primary_center", "secondary_center"] = "primary_center"
    established_date: str | None = None
    confidence_score: Annotated[float64, Field(ge=0.0, le=1.0)] | None = None
```

Use an association feature when the relationship has properties, such as confidence
scores, dates, types or notes; when the relationship is many-to-many; or when you need to
query relationships on their own.

##### Lists of references

When a feature refers to several other features, use a list of references. The
relationship type still matters:

```python
# COMPOSITION: boundary defines two divisions
class DivisionBoundary(
    OvertureFeature[Literal["divisions"], Literal["division_boundary"]]
):
    """A boundary line between two divisions."""

    division_ids: Annotated[
        list[
            Annotated[
                Id, Reference(Relationship.COMPOSITION, Division, role="boundary_of")
            ]
        ],
        Field(min_length=2, max_length=2, description="Left and right divisions"),
    ]


# AGGREGATION: route groups segments
class Route(OvertureFeature[Literal["transportation"], Literal["route"]]):
    """A transportation route passing through multiple segments."""

    segment_ids: Annotated[
        list[Id],
        Reference(Relationship.AGGREGATION, TransportationSegment, role="groups"),
        Field(min_length=1, description="Ordered segments in this route"),
        UniqueItemsConstraint(),
    ]
```

#### Reference annotations

Always include a `Reference` annotation on a reference field, so documentation and tools
know what kind of relationship it is:

```python
# Good: complete relationship information with semantic type and role
division_id: Annotated[
    Id,
    Reference(Relationship.HIERARCHY, Division, role="child_of"),
    Field(description="Division ID of the parent division of this area."),
]

# Avoid: missing semantic information
division_id: Id
```

To model a relationship, choose its type first, using the descriptions and order above.
Then choose how to write it: a direct reference for a simple link, an association feature
for a relationship with properties, or a list of references when one feature refers to
several.

### Discriminated unions

A discriminated union is a type made of several models. The value of one field, the discriminator, decides which model applies.

```python
from typing import Annotated, Literal
from pydantic import Field
from overture.schema.common import OvertureFeature


# Base class with common fields
class TransportationSegment(
    OvertureFeature[Literal["transportation"], Literal["segment"]]
):
    subtype: Subtype  # This is the discriminator field
    # ... common fields for all segments


# Specific segment types
class RoadSegment(TransportationSegment):
    subtype: Literal[Subtype.ROAD]  # Must be "road"
    class_: Annotated[RoadClass, Field(alias="class")]
    speed_limits: SpeedLimits | None = None
    # ... road-specific fields


class RailSegment(TransportationSegment):
    subtype: Literal[Subtype.RAIL]  # Must be "rail"
    class_: Annotated[RailClass, Field(alias="class")]
    rail_flags: RailFlags | None = None
    # ... rail-specific fields


# Union type that automatically picks the right model based on subtype
Segment = Annotated[
    RoadSegment | RailSegment | WaterSegment, Field(discriminator="subtype")
]
```

`discriminator="subtype"` tells Pydantic to read the `subtype` field to choose the model.
If `subtype` is `"road"`, Pydantic uses `RoadSegment`, and if it's `"rail"`, it uses
`RailSegment`.

#### Abstract and concrete base classes

In Pydantic, every class is concrete by default, so you can create an instance of a base
class such as `TransportationSegment`:

```python
# Both can be instantiated as map features
base_segment = TransportationSegment(subtype=Subtype.ROAD, geometry=...)  # Valid
road_segment = RoadSegment(subtype=Subtype.ROAD, geometry=..., class_=...)  # Valid
```

To stop a base class from being used on its own, make it abstract:

```python
from abc import ABC, abstractmethod
from typing import Annotated, Literal
from pydantic import Field


class TransportationSegment(
    OvertureFeature[Literal["transportation"], Literal["segment"]], ABC
):
    """Abstract base - cannot be instantiated directly."""

    subtype: Subtype  # Discriminator field

    @abstractmethod
    def get_speed_limit(self) -> float:
        """Each concrete type must implement this."""
        pass


class RoadSegment(TransportationSegment):
    """Concrete class - can be instantiated."""

    subtype: Literal[Subtype.ROAD]
    speed_limits: SpeedLimits | None = None

    def get_speed_limit(self) -> float:
        return self.speed_limits.max_speed if self.speed_limits else 50.0


# Now only concrete classes can be instantiated
# base_segment = TransportationSegment(...)  # TypeError: Can't instantiate abstract class
road_segment = RoadSegment(subtype=Subtype.ROAD, geometry=...)  # Valid
```

Overture's models don't make base classes abstract. Instead, each theme registers only the
types that should be discoverable as map features, through entry points:

```toml
# In packages/overture-schema-theme-transportation/pyproject.toml
[project.entry-points."overture.models"]
connector = "overture.schema.transportation:Connector"
segment = "overture.schema.transportation:Segment"
```

The transportation theme's
[`segment/__init__.py`](../packages/overture-schema-theme-transportation/src/overture/schema/transportation/segment/__init__.py)
works this way:

- `Segment` is a discriminated union of `RoadSegment`, `RailSegment` and `WaterSegment`.
  It's the only one of them that's registered, so it's the one that's discoverable as a
  map feature.
- `TransportationSegment` is the concrete base class that all three segment types inherit
  from.
- Pydantic resolves `Segment` to the right concrete type from the `subtype` field.
- You can reuse any of these classes as a base class for your own models.

### Pattern properties

Use pattern properties for a map whose keys must match a pattern, such as language codes, and whose values have a given type.

```python
from typing import Annotated
from pydantic import BaseModel, Field


@no_extra_fields
class Names(BaseModel):
    primary: str

    # Keys (strings) must match a language tag pattern, values are strings
    common: (
        Annotated[
            dict[
                # The key type
                Annotated[
                    str,
                    Field(
                        pattern=r"^[a-z]{2,3}(-[A-Z]{2})?$",
                        description="Language tag (e.g., 'en', 'es-MX')",
                    ),
                ],
                str,  # The value type
            ],
            Field(json_schema_extra={"additionalProperties": False}),
        ]
        | None
    ) = None
```

Data that matches this model looks like this:

```json
{
    "primary": "New York City",
    "common": {
        "es": "Ciudad de Nueva York",
        "fr": "New York",
        "zh-CN": "纽约市"
    }
}
```

`additionalProperties: False` in the generated JSON Schema means that only keys matching the
pattern are allowed.

### Nested lists

This pattern validates the outer list and the structure of each item in it.

```python
from typing import Annotated
from pydantic import Field


# Each item has its own field validation
@no_extra_fields
class HierarchyItem(BaseModel):
    division_id: str
    name: str


class Division(OvertureFeature):
    # Nested list validation: outer list AND inner lists both have length constraints
    hierarchies: Annotated[
        list[  # Outer list
            Annotated[
                list[HierarchyItem],  # Inner list
                Field(min_length=1),  # Inner list must have at least 1 item
            ]
        ],
        Field(min_length=1),  # Outer list must have at least 1 hierarchy
    ]
```

This model validates at three levels. Each `HierarchyItem` validates its own fields,
`division_id` and `name`. Each inner list must have at least one item. The `hierarchies`
field must have at least one inner list.

### Type aliases

A type alias gives a name to a long or frequently used type. `NewType` makes a distinct
type from an existing one, so a type checker treats, for example, a `SegmentId` and a
`CountryCode` as different types even though both are strings. A `NewType` can also wrap
an `Annotated` type, so its constraints apply everywhere you use it, and the code generator
uses its name in the reference docs.

Use noun names for model classes, such as `SourceItem` and `AccessRule`, and plural or
descriptive names for type aliases, such as `Sources` and `AccessRules`. Don't give a model
class and a type alias the same name in the same module, because it causes circular
references.

```python
from typing import NewType, Annotated
from pydantic import BaseModel, Field

# Create distinct types for different kinds of strings
SegmentId = NewType("SegmentId", str)  # IDs are strings, but distinct
CountryCode = NewType("CountryCode", str)  # Country codes are strings, but distinct

# Create aliases for complex field patterns
EmailList = NewType(
    "EmailList",
    Annotated[list[str], Field(min_length=1, description="List of email addresses")],
)


@no_extra_fields
class Contact(BaseModel):
    # Clear, self-documenting field types
    id: SegmentId  # Can't accidentally use a CountryCode here
    country: CountryCode  # Can't accidentally use a SegmentId here
    emails: EmailList  # Reusable validation pattern
```

Type aliases keep you from mixing up values that share a base type. They also let you
define a field's validation once and reuse it, and they make code easier to read:
`EmailList` says more than `list[str]`.

## Package and register your models

Once you register your models, the Overture tools treat them like Overture's own. The CLI
discovers them, `validate()` accepts them, and the generated docs and JSON Schema include
them. Nothing in the tools treats Overture's models as a special case.

To register a feature type, define the model, then add an entry point to your package's
`pyproject.toml`:

```python
# mypkg/src/mypkg/models.py
from typing import Literal
from overture.schema.common import OvertureFeature
from overture.schema.system.numeric import float32


class Vineyard(OvertureFeature[Literal["agriculture"], Literal["vineyard"]]):
    """A cultivated area planted with grapevines."""

    area_hectares: float32 | None = None
```

```toml
# mypkg/pyproject.toml
[project]
name = "mypkg"
version = "0.1.0"
dependencies = ["overture-schema-common"]

[project.entry-points."overture.models"]
vineyard = "mypkg.models:Vineyard"
```

`uv init --lib mypkg` creates this layout with a build backend. Add the `dependencies` and
entry-point lines to its `pyproject.toml`. Then install `mypkg` into the same environment
as the Overture tools. In a project that already has `overture-schema-cli`, run
`uv add --editable ./mypkg`. Your type then appears in the tools:

```bash
uv run overture-schema list-types
uv run overture-schema validate vineyard.json
uv run overture-codegen generate --format markdown --output-dir out
```

To add tags of your own, register a tag provider on the `overture.tag_providers` entry-point
group:

```python
def experimental_provider(types, key, tags):
    if any(getattr(t, "__experimental__", False) for t in types):
        tags.add("mypkg:experimental")
    return tags
```

```toml
[project.entry-points."overture.tag_providers"]
experimental = "mypkg.tags:experimental_provider"
```

Some tag namespaces are reserved. `feature` and `system:` belong to
`overture-schema-system`, and `overture:` belongs to `overture-schema-common`. If a
provider in another package sets a reserved tag, discovery logs a warning and drops the
tag, so use a namespace of your own.

You don't have to build on `OvertureFeature`. To make a model that serializes to GeoJSON
without the Overture conventions, subclass `system.Feature` directly.

### Entry points

Each package registers its models as
[entry points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html) in its
`pyproject.toml`, under `[project.entry-points."overture.models"]`. The tools find the
models at runtime, without importing them by name:

```toml
[project.entry-points."overture.models"]
building = "overture.schema.buildings:Building"
building_part = "overture.schema.buildings:BuildingPart"
```

To get the registered models in Python, use the discovery functions:

```python
from overture.schema.system.discovery import discover_models, get_registered_model

# Discover all registered models, keyed by ModelKey
all_models = discover_models()

# Get a specific model by name
building_model = get_registered_model("building")
if building_model:
    building = building_model.model_validate(building_data)
```

### Tags

Each `ModelKey` that `discover_models()` returns has a `frozenset[str]` of tags. Tags
classify a model independently of its name: for example, whether it's a `Feature`
subclass, and which Overture theme or package it comes from. The CLI, the code generator
and other tools use tags to select models without importing every one:

```python
from overture.schema.system.discovery import (
    TagSelector,
    discover_models,
    filter_models,
)

models = discover_models()
# {
#   ModelKey(name="building", entry_point="overture.schema.buildings:Building",
#            tags=frozenset({"feature", "overture", "overture:theme=buildings"})): Building,
#   ModelKey(name="place",    entry_point="overture.schema.places:Place",
#            tags=frozenset({"feature", "overture", "overture:theme=places"})):    Place,
#   ...
# }

buildings = filter_models(
    models,
    TagSelector(include_any=("overture:theme=buildings",)),
)
```

Tag providers registered on the `overture.tag_providers` entry-point group produce the
tags. The `system` and `common` packages include the built-in providers for `feature` and
`overture:theme=*`. For the tag format, the reserved namespaces and how to write a
provider, see the
[`overture-schema-system` README](../packages/overture-schema-system/README.md#tagging).

To generate a format the Overture tools don't support yet, such as Arrow or Avro schemas,
add a target to the code generator. See
[Adding a codegen target](../packages/overture-schema-codegen/docs/adding-a-target.md).

## Templates

Copy one of these templates to start a model. Overture's own themes also follow the naming
and unit conventions in [CONTRIBUTING.md](../CONTRIBUTING.md#names-and-units).

### Model

```python
from typing import Annotated
from pydantic import BaseModel, Field
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.numeric import int8, float64


@no_extra_fields
class MyCustomType(BaseModel):
    """Brief description of what this represents."""

    # Required fields (no default value)
    name: str
    category: str

    # Optional fields (with default values)
    description: str | None = None

    # Field with constraints and description
    priority: Annotated[
        int8 | None,
        Field(
            ge=1, le=10, description="Priority level from 1 (lowest) to 10 (highest)"
        ),
    ] = None
```
### Feature

```python
from typing import Annotated, Literal
from pydantic import Field
from overture.schema.common import OvertureFeature
from overture.schema.system.geometric import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)


class MyFeature(OvertureFeature[Literal["my_theme"], Literal["my_type"]]):
    """Description of what this feature represents."""

    # Geometry with constraints
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POINT),
        Field(description="Location of this feature"),
    ]

    # Custom fields
    my_field: str | None = None
```
### Enum

```python
from enum import Enum


class MyEnum(str, Enum):
    """Description of what this enum represents."""

    VALUE_ONE = "value_one"
    VALUE_TWO = "value_two"
    VALUE_THREE = "value_three"
```
### Model with constraints

```python
from typing import Annotated
from pydantic import BaseModel, Field
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields


@no_extra_fields
class Contact(BaseModel):
    """Contact information with validation constraints."""

    name: str
    email: str | None = None
    phone: str | None = None

    # List with constraints
    tags: Annotated[
        list[str] | None,
        Field(min_length=1, description="Contact tags"),
        UniqueItemsConstraint(),  # No duplicate tags
    ] = None
```
### Association feature

```python
from typing import Annotated, Literal
from pydantic import Field
from overture.schema.common import OvertureFeature
from overture.schema.system.numeric import float64
from overture.schema.system.ref import Id, Reference, Relationship


class MyAssociation(
    OvertureFeature[Literal["associations"], Literal["my_association"]]
):
    """Represents a relationship between two features with metadata."""

    # References to the associated features
    # Relationship takes a *kind* (COMPOSITION / AGGREGATION / HIERARCHY /
    # ASSOCIATION); what the reference means comes from `role`. Two
    # references to related features need distinct roles to stay unambiguous.
    feature_a_id: Annotated[
        Id,
        Reference(Relationship.ASSOCIATION, FeatureA, role="connects_from"),
        Field(description="First feature in the relationship"),
    ]

    feature_b_id: Annotated[
        Id,
        Reference(Relationship.ASSOCIATION, FeatureB, role="connects_to"),
        Field(description="Second feature in the relationship"),
    ]

    # Relationship metadata
    relationship_type: Literal["primary", "secondary"] = "primary"
    confidence: Annotated[float64 | None, Field(ge=0.0, le=1.0)] = None

    # Optional contextual information
    notes: str | None = None
```
### Constraint reference

| Type | Constraint | JSON Schema | Example |
|------|------------|-------------|---------|
| **Numeric** | `ge=0, le=100` | `minimum`, `maximum` | `Field(ge=0, le=100)` |
| **String** | `min_length=1, pattern=r"..."` | `minLength`, `pattern` | `Field(min_length=1, pattern=r"^[A-Z]+$")` |
| **List** | `min_length=1, UniqueItemsConstraint()` | `minItems`, `uniqueItems` | `Field(min_length=1), UniqueItemsConstraint()` |
| **Custom** | `LanguageTagConstraint()` | Custom validation | `LanguageTagConstraint()` |

---

## Next steps

In this guide, you wrote a model with the schema's base classes, field types, constraints
and enums. You modeled its relationships to other features, and you registered it so the
Overture tools find it. The templates give you a starting point for your next model.

- To list your models, validate data against them, or generate JSON Schema and reference
  docs from them, follow [the schema guides](README.md). Your registered types work
  with every command in them.
- To learn why the schema is split into packages and how tags work, read
  [Concepts](concepts.md).
- To add an output format to the code generator, read
  [Adding a codegen target](../packages/overture-schema-codegen/docs/adding-a-target.md).
- If you're on Overture staff or at a member organization and want to add your model to
  one of Overture's themes, follow [CONTRIBUTING.md](../CONTRIBUTING.md).
- To ask a question or suggest a change to this guide, post in [GitHub Discussions](https://github.com/orgs/OvertureMaps/discussions).
