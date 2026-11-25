# Exploring the models

Use this guide to find out which feature types you have installed, which fields each one
has, and which values each field accepts. Install the packages first, as in
[Getting started with the schema](getting-started-with-the-schema.md).

You can look these up in two places. The Pydantic models are the code that runs when you
validate data, and you query them from Python, as in
[Model fields in Python](#model-fields-in-python). The JSON Schema is a
document that `overture-schema json-schema` generates from the models. Use it when the
rules need to go to a tool that doesn't run Python, such as a validator or code generator
in another language. See [The generated JSON Schema](#the-generated-json-schema). You'll get the same answers from both, because
the JSON Schema is generated from the models.

## Running Python against the models

From here on, most examples are Python. Run them with `uv run python` from your project
directory, or with plain `python` if you installed with `pip` and activated the
environment:

```bash
uv run python -c "from overture.schema.buildings import Building; print(len(Building.model_fields))"
```
```
26
```

For this guide, an interactive session (`uv run python`) is the easiest way to look things
up. For anything longer, save the code to a file and run `uv run python yourfile.py`.

If Python reports `ModuleNotFoundError: No module named 'overture'`, it's running outside
your project's environment. See
[that entry in Troubleshooting](troubleshooting.md#modulenotfounderror-no-module-named-overture).

## Listing feature types

You ran `list-types` in [Check the install](getting-started-with-the-schema.md#check-the-install):

```bash
uv run overture-schema list-types
```

Columns are: **type name**, then its **tags**. Group by a tag key:

```bash
uv run overture-schema list-types --group-by overture:theme
```

```
overture:theme=addresses (1)
→ address            feature  overture  overture:theme=addresses

overture:theme=base (6)
...
```

The trailing words, such as `feature`, `overture`, and `overture:theme=addresses`, are **tags**.
Every feature type has a few, and they are how you select a subset of types without
naming each one. A tag is either a bare word (`feature`), or a key and value joined by
`=` (`overture:theme=buildings`), where the part before the colon says who defined it.

Three options select by tag, and all three take a tag name and can be repeated. They are
shared by `list-types`, `validate`, and `json-schema`:

| Option | Keeps a type when… |
|---|---|
| `--tag` | it has **any** of the tags you listed |
| `--filter` | it has **all** of the tags you listed |
| `--exclude` | drops it if it has any of the tags you listed |

So this lists the buildings types and the places types, and nothing else:

```bash
uv run overture-schema list-types --tag overture:theme=buildings --tag overture:theme=places
```

Your own feature types join the set through tags too. See
[Tags](concepts.md#tags).

### Listing feature types in Python

To get the list of installed feature types in Python, call `discover_models()`. It
returns the same list that `overture-schema list-types` prints. Use it
when your code needs to handle whichever feature types are installed, instead of a list
you wrote out yourself.

```python
from overture.schema.system.discovery import discover_models

for key, model in sorted(discover_models().items(), key=lambda kv: kv[0].name):
    print(f"{key.name:20} {key.entry_point:45} {sorted(key.tags)}")
```

```
address              overture.schema.addresses:Address             ['feature', 'overture', 'overture:theme=addresses']
bathymetry           overture.schema.base:Bathymetry               ['feature', 'overture', 'overture:theme=base']
building             overture.schema.buildings:Building            ['feature', 'overture', 'overture:theme=buildings']
building_part        overture.schema.buildings:BuildingPart        ['feature', 'overture', 'overture:theme=buildings']
connector            overture.schema.transportation:Connector      ['feature', 'overture', 'overture:theme=transportation']
division             overture.schema.divisions:Division            ['feature', 'overture', 'overture:theme=divisions']
division_area        overture.schema.divisions:DivisionArea        ['feature', 'overture', 'overture:theme=divisions']
division_boundary    overture.schema.divisions:DivisionBoundary    ['feature', 'overture', 'overture:theme=divisions']
infrastructure       overture.schema.base:Infrastructure           ['feature', 'overture', 'overture:theme=base']
land                 overture.schema.base:Land                     ['feature', 'overture', 'overture:theme=base']
land_cover           overture.schema.base:LandCover                ['feature', 'overture', 'overture:theme=base']
land_use             overture.schema.base:LandUse                  ['feature', 'overture', 'overture:theme=base']
place                overture.schema.places:Place                  ['feature', 'overture', 'overture:theme=places']
segment              overture.schema.transportation:Segment        ['feature', 'overture', 'overture:theme=transportation']
water                overture.schema.base:Water                    ['feature', 'overture', 'overture:theme=base']
```

A `ModelKey` has `.name`, `.entry_point` (`"module:Class"`), and `.tags`
(a `frozenset[str]`). Filter the same way the CLI does:

```python
from overture.schema.system.discovery import TagSelector, discover_models, filter_models

models = discover_models()

buildings = filter_models(
    models, TagSelector(include_any=("overture:theme=buildings",))
)
print(sorted(key.name for key in buildings))
```
```
['building', 'building_part']
```

`TagSelector` takes `include_any` (OR scope), `require_all` (AND narrowing), and
`exclude_any` (OR-NOT). An empty selector returns the input unchanged.

## Importing the models

Before you can explore anything, you need to know where it lives. The Python module
path drops the `theme-` prefix:

| Package | Import from |
|---|---|
| `overture-schema-theme-buildings` | `overture.schema.buildings` |
| `overture-schema-theme-transportation` | `overture.schema.transportation` |
| `overture-schema-theme-places` | `overture.schema.places` |
| `overture-schema-theme-divisions` | `overture.schema.divisions` |
| `overture-schema-theme-addresses` | `overture.schema.addresses` |
| `overture-schema-theme-base` | `overture.schema.base` |
| `overture-schema-common` | `overture.schema.common` |
| `overture-schema-system` | `overture.schema.system` |
| `overture-schema-validation` | `overture.schema.validation` |

```python
from overture.schema.buildings import Building, BuildingClass
from overture.schema.transportation import Segment, Connector, RoadClass
from overture.schema.places import Place
```

`import overture.schema` gives you nothing directly. It's a namespace root
that ships only a `py.typed` marker, with no models and no functions. Always import from the
theme packages:

```python
from overture.schema.buildings import Building  # ✓
from overture.schema import Building  # ✗ ImportError
```

## Model fields in Python

The Pydantic models are the schema. The JSON Schema, the reference docs, and the PySpark
expressions are all generated from them, so the models are where to look for the
definitive answer.

`Building` is an ordinary Python class, and Pydantic gives every model a `model_fields`
dict describing each field: its type, whether it's required, its documentation, and its
constraints.

Start a session and look at what you have:

```bash
uv run python
```

```python
>>> from overture.schema.buildings import Building
>>> len(Building.model_fields)
26
>>> sorted(n for n, f in Building.model_fields.items() if f.is_required())
['geometry', 'id', 'theme', 'type', 'version']
```

All of the fields, required or not, are at the top level of the model, including `id` and
`geometry`.

Some fields have nested values. `names` is a `Names` object with its own fields, such as
`primary`, and `sources` is a list of source records. They nest the same way in Parquet,
where they're struct and list columns.

GeoJSON lays the same fields out differently. When you write a model out as GeoJSON, `id`,
`bbox`, and `geometry` stay at the top, the other fields go inside a `properties` object, and a
`"type": "Feature"` key is added. Those top-level keys are called the **envelope**. The
envelope exists only in GeoJSON, not in the Python object or in Parquet.

To learn more, see [The GeoJSON envelope](concepts.md#the-geojson-envelope) in the Concepts guide. 

### Every field at a glance

```python
from overture.schema.buildings import Building

print(Building.__doc__)

for name, f in Building.model_fields.items():
    flag = "required" if f.is_required() else "optional"
    print(f"{name:24} {flag:9} {f.annotation}")
```

```
height                   optional  typing.Optional[overture.schema.system.numeric.float64]
is_underground           optional  bool | None
num_floors               optional  typing.Optional[overture.schema.system.numeric.int32]
...
id                       required  overture.schema.system.ref.id.Id
geometry                 required  <class 'overture.schema.system.geometric.geom.Geometry'>
theme                    required  typing.Literal['buildings']
type                     required  typing.Literal['building']
version                  required  overture.schema.common.feature.FeatureVersion
class_                   optional  overture.schema.buildings.building.BuildingClass | None
```

Some of those types might look strange.
`typing.Optional[overture.schema.system.numeric.float64]` means **"a float, or nothing."**
`Optional[X]` means the field may be absent. `float64` is a Python `float` under another
name, defined in `overture-schema-system`:

```python
from overture.schema.system.numeric import float64

float64.__supertype__  # <class 'float'>
```

The schema authors use named types like `float64`, `int32`, and `uint8` so a field can
declare its width: which Parquet column type it becomes and what range of values it
accepts. In Python, the value is still a plain number. `Id` and `FeatureVersion` work the
same way. They're named types based on `str` and `int`, with constraints of their own: an
`Id` can't be empty or contain whitespace, and a `FeatureVersion` can't be negative.
`Literal['building']` is different. It means the field must be exactly that one string.

### One field in detail

Each entry includes the documentation and constraints from the model declaration:

```python
f = Building.model_fields["height"]
print(f.description)  # 'Height of the building or part in meters.\n\n...'
print(f.metadata)  # [Gt(gt=0)]
print(f.alias)  # None
print(Building.model_fields["class_"].alias)  # 'class'
```

Note `class_` and its alias `class`. `class` is a Python keyword, so the field is named
`class_` on the model and `class` in the data. That mismatch matters when you serialize.
See [Gotchas](troubleshooting.md#model-gotchas).

You'll see the same information in [the generated JSON Schema](#the-generated-json-schema), where it
goes by different names: `f.description` becomes `description`, the `[Gt(gt=0)]`
in `f.metadata` becomes `exclusiveMinimum: 0`, and `f.is_required()` becomes membership in
a list called `required`. 

## Reading enum member documentation

An enum can have two kinds of documentation. The class docstring describes the enum as a
whole. Member documentation describes one value. Only enums built on `DocumentedEnum` can
document individual members, by giving a value and a description as a pair:

```python
class TravelMode(str, DocumentedEnum):
    """Enumerates possible travel modes.

    Some modes represent groups of modes.
    """

    VEHICLE = "vehicle"
    MOTOR_VEHICLE = ("motor_vehicle", "Includes car, truck and motorcycle")
    CAR = "car"
```

Here, only `motor_vehicle` has documentation of its own.

Don't use `__doc__` to read member documentation. On a plain Python `Enum`, such as
`RoofShape`, every member's `__doc__` returns the class docstring, so each member looks
documented with the same sentence:

```python
from overture.schema.buildings import RoofShape

[(m.value, m.__doc__) for m in list(RoofShape)[:2]]
# [('dome', 'The shape of the roof.'), ('flat', 'The shape of the roof.')]
```

Use the codegen extractor instead. It works on plain enums like `RoofShape` and on
`DocumentedEnum` enums like `TravelMode`, and it gives you `None` for a member with no
documentation of its own:

```python
from overture.schema.codegen.extraction.enum_extraction import extract_enum
from overture.schema.common.scoping.travel_mode import TravelMode

spec = extract_enum(TravelMode)
for m in spec.members[:4]:
    print(f"{m.value:14} {m.description}")
```

```
vehicle        None
motor_vehicle  Includes car, truck and motorcycle
car            None
truck          None
```

The extractor needs `overture-schema-codegen`. See [Install from PyPI](getting-started-with-the-schema.md#install-from-pypi).

## The generated JSON Schema

The JSON Schema describes the same rules as the models, in a standard format that tools in
any language can read. A validator written in Go or a code generator that emits TypeScript
can't import Python classes, but it can read JSON Schema. Use it when you're handing the
rules to a tool like that, or when you want to see the rules as they apply to GeoJSON,
since that's the form the JSON Schema describes.

To generate it for one feature type:

```bash
uv run overture-schema json-schema --type building > building.schema.json
```

Because the JSON Schema describes the GeoJSON form, three things look different from the
model:

- **Most fields are under the envelope.** A building's fields are at
  `.properties.properties.properties`. The first and third `properties` are the JSON
  Schema keyword for "the fields of this object." The second is the GeoJSON field named
  `properties`. `id`, `geometry`, and `bbox` are one level up, at `.properties`.
- **Required fields come in two lists.** `.required` lists `id` and `geometry`, along with
  the GeoJSON keys `type` and `properties`. `.properties.properties.required` lists
  `theme`, `type`, and `version`. Together they're the same five fields that
  `model_fields` reports in [Model fields in Python](#model-fields-in-python).
- **Enums and shared structures are defined once**, under `$defs`, and the fields that use
  them refer to them there.

Each field's rules are written as JSON Schema keywords. Here's `height`:

```json
{
  "description": "Height of the building or part in meters.\n\nThis is the distance from the lowest point to the highest point.",
  "exclusiveMinimum": 0,
  "title": "Height",
  "type": "number"
}
```

`"exclusiveMinimum": 0` comes from `gt=0` in the Python declaration, and `"type": "number"`
from the `float64` annotation.

To generate JSON Schema for a whole theme, select it by tag. To get one document for every
installed type, leave out the options. That document is an `anyOf` over the installed
types, with shared definitions under `$defs`.

```bash
uv run overture-schema json-schema --tag overture:theme=transportation > transportation.schema.json
uv run overture-schema json-schema > overture.schema.json
```

To query the JSON Schema from the command line, see
[Explore the JSON Schema with jq](explore-json-schema-with-jq.md).

### JSON Schema in Python

To generate JSON Schema from Python, call `json_schema()`:

```python
from overture.schema.system.json_schema import json_schema
from overture.schema.buildings import Building
from overture.schema.places import Place

schema = json_schema(Building)
schema["title"]  # 'building'
sorted(schema)  # ['$defs', 'additionalProperties', 'description',
#  'properties', 'required', 'title', 'type']
```

To get one JSON Schema that accepts more than one feature type, pass a union.
`Building | Place` means "a building or a place":

```python
schema = json_schema(Building | Place)
sorted(schema)  # ['$defs', '$schema', 'anyOf']
schema["anyOf"]  # [{'$ref': '#/$defs/Building'}, {'$ref': '#/$defs/Place'}]
```

The result uses the JSON Schema keyword `anyOf`: a document is valid if it matches any one
of the listed schemas. Use a union when a single file can contain more than one feature
type. `overture-schema json-schema` with no options builds a combined schema like this
for every installed type.

Use this rather than Pydantic's `model_json_schema()`. The Overture generator treats
`T | None = None` as "omit when unset" instead of Pydantic's "nullable with a null
default", which is what the data actually means.

To generate client code in another language from the JSON Schema, see
[Client code in other languages](generating-other-formats.md#client-code-in-other-languages).

## Generate browsable reference docs

For sustained exploration, generate the full markdown reference and read it in your
editor. This needs the `overture-codegen` command, from `overture-schema-codegen`. If
you installed from PyPI, add it first with `uv add overture-schema-codegen`, or with
`pip install overture-schema-codegen` if you use `pip`.

```bash
uv run overture-codegen generate --format markdown --output-dir ./schema-docs
```

You get one page per feature type, per enum, and per named type, with field tables,
prose constraint descriptions, cross-page links, and validated examples:

```
schema-docs/overture/schema/buildings/building.md
schema-docs/overture/schema/buildings/building_part.md
schema-docs/overture/schema/buildings/types/building_class.md
schema-docs/overture/schema/buildings/types/roof_shape.md
schema-docs/overture/schema/common/names.md
schema-docs/overture/schema/common/sources.md
schema-docs/system/numeric.md
...
```

To generate docs for only some feature types, narrow the set by tag with `--tag`,
`--filter`, and `--exclude`, the same options `overture-schema` uses. For example, to
generate docs for the buildings theme only:

```bash
uv run overture-codegen generate --format markdown \
  --tag overture:theme=buildings --output-dir ./schema-docs
```

The output still includes the shared types from `common` and `system`, because the
feature pages link to them.

The output is Docusaurus-flavored, with frontmatter and `_category_.json` files, but it's
plain markdown underneath and reads fine in any editor or static site generator.

## Next steps

- [Working with features in Python](working-with-features.md)
- [Validating data](validating-data.md)
- [Generating other formats](generating-other-formats.md)
- [Explore the JSON Schema with jq](explore-json-schema-with-jq.md)
- [Glossary](glossary.md)
