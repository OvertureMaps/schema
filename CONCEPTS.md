# Concepts

Background on why the Overture schema looks the way it does. **None of this is needed to
get work done** — [SCHEMA_GUIDE.md](SCHEMA_GUIDE.md) is the path through the examples,
and it stands on its own. Read a section here when you hit something whose *why* you want.

Not to be confused with [GLOSSARY.md](GLOSSARY.md), which defines the same vocabulary in a
sentence or two each. If you want to know what *envelope* or *workspace* or *tag* means,
the glossary is faster. This page is for why they exist.

| Question | Section |
|---|---|
| Why have a schema at all? | [Beyond raw data](#beyond-raw-data) |
| Why Pydantic instead of JSON Schema? | [Why Pydantic](#why-pydantic-rather-than-json-schema) |
| Why is the schema split into a dozen packages? | [Many packages](#why-the-schema-is-many-packages) |
| What is an "envelope"? Why do Overture fields sit under `properties`? | [The GeoJSON envelope](#the-geojson-envelope) |
| Why does `type` appear three times in one file? | [Three keys named `type`](#three-keys-named-type) |
| If the schema is Pydantic now, why does it still look like GeoJSON? | [Why there's an envelope at all](#why-theres-an-envelope-at-all) |
| Why can a model be named two ways? | [Two names per model](#two-names-per-model) |
| What decides whether a field is required? | [What makes a field required](#what-makes-a-field-required) |
| What are those `overture:theme=` tags? | [How tags work](#how-tags-work) |
| What is the example file the guide validates? | [The example file](#what-the-example-file-actually-is) |
| Why are the examples YAML? | [Why examples are YAML](#why-examples-are-yaml) |
| Why isn't the generated PySpark code in git? | [Generated code](#why-generated-code-is-gitignored) |

---

## Why this exists

This project provides type-safe Python models for validating and working with
[Overture](https://overturemaps.org/) data. Use these schemas to:

- Validate Overture data
- Build data processing pipelines with type safety
- Extend schemas with custom fields and validation rules

## Beyond raw data

This project addresses a fundamental challenge in data consumption: **bridging the
semantic gap between raw data and human understanding** while enabling
machine-actionable workflows.


Take a column like `pop_2020`. Is it total population? Population density per square
kilometer? Working-age population? Without a schema, you're left sampling values and
guessing from column names.

Compare this to OpenStreetMap's approach: features use well-known key/value pairs like
`building=residential` or `addr:housenumber=42` that have semantic meaning and can be
looked up on the OSM wiki. This creates a step toward a schema - shared vocabulary with
documented semantics used across a vast dataset. However, OSM tags remain free-form:
multiple valid ways to express the same concept, no built-in validation, and complex
downstream validation because of undocumented keys that might have meaning to someone,
somewhere. A schema provides the structured alternative: explicit types, clear
validation rules, and semantic meaning that both humans and systems can rely on.

Data files containing only column names and values aren't fully documented. External
metadata files typically focus on how data was collected and encoded, not on semantic
meaning or validation rules. Data consumers struggle to understand what datasets contain
and which columns they need for their goals.

## Why Pydantic rather than JSON Schema

We initially chose JSON Schema because it aligned with our mental model and promised to
solve our problems as we understood them. But JSON Schema surfaced several pain points:

- **Authoring difficulty**: Hard to write correctly, difficult to verify, limited IDE
  support, no refactoring capabilities
- **Tooling gaps**: Generic tools can't tailor output for specific applications like
  ours
- **Development friction**: Schema changes required manual coordination across multiple
  artifacts

Pydantic addresses these systematically: author in Python with full IDE support,
generate tailored documentation, and automatically produce the specific artifacts each
workflow needs. Pydantic can also produce JSON Schema, so any application that requires
it can use it while we gain all the Python benefits during authoring.

## The result

Instead of spending time deciphering what columns mean and whether data matches
expectations, users can focus on their actual goals: analysis, visualization,
integration. Quality improves because validation happens automatically rather than
through manual inspection.

The fundamental approach - human-readable authoring that generates machine-actionable
outputs - has broader applications beyond Overture and geospatial data. We hope others
will adapt these patterns for linking with Overture data or modeling their own domains
entirely.

---

## Why the schema is many packages

> **Why split the schema into so many packages?** Because *what you install determines what
> exists at runtime*. The models register themselves through Python entry points, so
> installing only the buildings theme means the CLI only knows about buildings. That's
> the extension mechanism — see [Using the packages from your own project](SCHEMA_GUIDE.md#7-using-the-packages-from-your-own-project) and
> [Register your own feature types](AUTHORING.md#register-your-own-feature-types). If you just want everything, that's fine too.

### What "workspace" means

A **uv workspace** is one repository containing several packages that are developed
together, sharing **one lockfile** and **one virtual environment**. If you've used Cargo
workspaces, npm workspaces, or a monorepo, it's the same idea.

The root `pyproject.toml` declares it:

```toml
[project]
name = "overture-schema-workspace"     # ← a container, not something you install
version = "0.0.0"

[tool.uv.workspace]
members = ["packages/*"]               # ← every directory under packages/ is a member
```

Two things follow from this:

**1. You never install or import `overture-schema-workspace`.** It's scaffolding. It
exists so `uv` knows which directories are members. There is no `import
overture_schema_workspace`.

**2. The packages depend on each other *locally*, not through PyPI.** Look at
`packages/overture-schema-cli/pyproject.toml`:

```toml
[tool.uv.sources]
overture-schema-common = { workspace = true }
overture-schema-system = { workspace = true }
```

`workspace = true` means "use the copy in this repo." This is why none of this needs to
be published to PyPI for you to work with it — the packages find each other.

---

## The GeoJSON envelope

An **envelope** is an outer wrapper that carries a payload plus a little standard
information about it. The term is borrowed from mail: the address and stamp go on the
outside and are the same on every envelope; the letter inside is whatever you wrote.

GeoJSON works exactly that way. Every GeoJSON Feature has the same four outer keys, fixed
by RFC 7946 — that's the envelope. Everything specific to *your* data goes in one of them,
`properties` — that's the payload.

```json
{
  "type": "Feature",                          <- envelope: what kind of object this is
  "id": "overture:buildings:building:1234",   <- envelope: identity
  "geometry": { "type": "Polygon", ... },     <- envelope: where it is
  "properties": {                             <- envelope: the pocket for everything else
      "theme": "buildings",                       payload: Overture's fields
      "type": "building",
      "height": 21.34,
      "num_floors": 4,
      "class": "parking"
  }
}
```

Split them apart for yourself:

```python
import json, yaml
from overture.schema.buildings import Building

b = Building.model_validate_json(
    json.dumps(yaml.safe_load(open("examples/buildings/building-polygon.yaml"))))
gj = b.model_dump(mode="json", by_alias=True, exclude_none=True)

print("envelope keys:", sorted(gj))
print("payload keys :", sorted(gj["properties"]))
```

```
envelope keys: ['geometry', 'id', 'properties', 'type']
payload keys : ['class', 'ext_bar', 'ext_foo', 'height', 'is_underground', 'level',
                'num_floors', 'num_floors_underground', 'sources', 'subtype',
                'theme', 'type', 'version']
```

Four keys outside, thirteen inside. **A GeoJSON Feature for a road, a lake, or a mailbox
has the same four outer keys** — that's what makes it universally readable. Only the
payload differs.

So when this guide says "the envelope owns `id` and `geometry`," it means those two are
outer keys, placed there by GeoJSON's rules rather than by Overture's. And "the fields are
nested under the envelope" means the Overture fields sit inside `properties` rather than
at the top.

One consequence worth carrying forward: **the envelope only exists in the GeoJSON
rendering.** In the Pydantic model, and in Parquet, there is no envelope — `id`,
`geometry`, and `height` are all just fields side by side.

### Three keys named `type`

A **key** is a field name — the part left of the colon. This file uses the key `type`
three times, at three nesting levels, meaning three unrelated things:

| Where | Value | Comes from | Means |
|---|---|---|---|
| top level | `Feature` | GeoJSON spec | "this object is a GeoJSON Feature" |
| inside `geometry` | `Polygon` | GeoJSON spec | "this shape is a polygon" |
| inside `properties` | `building` | Overture | "this feature is a building" |

List them yourself:

```python
import yaml
d = yaml.safe_load(open('examples/buildings/building-polygon.yaml'))
print('type            =', d['type'])
print('geometry.type   =', d['geometry']['type'])
print('properties.type =', d['properties']['type'])
```

```
type            = Feature
geometry.type   = Polygon
properties.type = building
```

Only the third is Overture's. The first two belong to GeoJSON, the envelope Overture data
is wrapped in when written as JSON. Whenever this guide says "the feature's type" it means
`properties.type` — the one holding `building`, `place`, or `segment`.

That layering is the single most confusing thing about this data, and section 3 is largely
about it.

**"Validating" means:** the CLI parses the file, reads `theme: buildings` and
`type: building` to decide *which model* to check against, then checks every field
against that model — types, numeric bounds, enum membership, required fields, and
cross-field rules.

You can watch it pick the model. Delete the `theme:` line and it no longer knows:

```
⚠ Ambiguous: Data matches multiple types equally. Consider:
  • Specifying --tag or --type to narrow validation
  • Adding discriminator fields to clarify intent
```

### Why there's an envelope at all

If the schema is now Pydantic, why does any of this still look like GeoJSON? Because those
two things answer different questions, and only one of them changed.

| | What it is | Did it change? |
|---|---|---|
| **Pydantic** | How the schema is *authored and enforced*, in Python | **Yes** — it replaced hand-written JSON Schema YAML |
| **GeoJSON** | One way a feature can be *written out as JSON*, per RFC 7946 | **No** — it's an interchange format, not an authoring choice |

Pydantic replaced JSON Schema as the authoring language. It has nothing to say about how
data is serialized, so GeoJSON was never in scope to replace.

**But GeoJSON is not how Overture ships bulk data — Parquet is.** The release bucket is
Hive-partitioned Parquet:

```
s3a://overturemaps-us-west-2/release/2026-07-22.0/theme=buildings/type=building/
```

That is a columnar table: `id`, `geometry`, `height`, and the rest are *columns*, flat, no
envelope. It's what `overture-validate` reads, what DuckDB attaches to, and what you'd
query for anything at scale.

So why does GeoJSON appear at all? Because **JSON Schema describes JSON documents**, and
when a geospatial feature is written as a single JSON document, GeoJSON is the format
every GIS tool already reads. Parquet has no JSON representation to describe — it has a
columnar schema instead, which is exactly what
[section 6](SCHEMA_GUIDE.md#6-converting-the-schema-to-other-formats) generates as a Spark `StructType`.

The honest summary is that there are two serializations and neither is subordinate:

| Serialization | Shape | Pydantic mode | Where you meet it |
|---|---|---|---|
| **Parquet** | flat / columnar | `python` | the release bucket, Spark, DuckDB — all bulk data |
| **GeoJSON** | nested envelope | `json` | single features, extracts, examples in this repo, web tooling |

The model supports both deliberately. The JSON Schema you're reading in this subsection
describes the second one, which is the only reason an envelope shows up here at all.

### Interchange format vs storage format

An **interchange format** is one whose job is handing data to a program you didn't write.
It's optimized for being *understood by anything*, not for being stored efficiently. A
**storage format** is the opposite: optimized for holding a lot of data and querying it
fast, at the cost of needing specific software to read it at all.

| | GeoJSON | Parquet |
|---|---|---|
| Optimized for | being read by anything | storing and scanning millions of rows |
| Text or binary | plain text | binary, columnar, compressed |
| Read it with | any JSON parser | a Parquet library |
| Self-describing | yes — the file says what it is | schema in the footer, not human-readable |
| Good at | one feature, an extract, a web map | a whole theme, a whole planet |

The cost of being universally readable is that GeoJSON repeats every field name on every
feature:

```python
import json, yaml
from overture.schema.buildings import Building

b = Building.model_validate_json(
    json.dumps(yaml.safe_load(open("examples/buildings/building-polygon.yaml"))))
gj   = b.model_dump(mode="json",   by_alias=True, exclude_none=True)
flat = b.model_dump(mode="python", by_alias=True, exclude_none=True)
flat["geometry"] = str(flat["geometry"])

n = 10_000
doc  = json.dumps({"type": "FeatureCollection", "features": [gj] * n})
cols = list(flat)
tbl  = json.dumps({"columns": cols, "rows": [[flat[k] for k in cols]] * n})
print(f"{n:,} features as GeoJSON      : {len(doc):>10,} bytes")
print(f"{n:,} features, names stored once: {len(tbl):>10,} bytes")
```

```
10,000 features as GeoJSON      :  7,040,043 bytes
10,000 features, names stored once:  4,520,199 bytes
```

A 1.56x penalty before compression even enters the picture, and that comparison is still
generous to GeoJSON — real Parquet also compresses each column and lets a reader skip
columns it doesn't need. Multiply by a planet's worth of buildings and the reason bulk
data isn't shipped as GeoJSON is obvious.

"Interchange" is a role, not a ranking. GeoJSON is the right tool for handing one feature
to a web map; Parquet is the right tool for handing a continent to Spark.

### Is Pydantic wrapped around GeoJSON?

Short answer: **no.** But the question has three reasonable readings, and one of them is a
qualified yes, so it's worth taking them separately.

**"Is the model built on top of a GeoJSON structure?"** No. A model is a flat list of
fields, declared one at a time in Python. You can build one and use it without JSON ever
entering the picture:

```python
from overture.schema.buildings import Building
from overture.schema.system.geometric import Geometry

b = Building(
    id="my-building-1",
    geometry=Geometry.from_wkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"),
    theme="buildings",
    type="building",
    version=1,
    height=12.5,
)
print(b.id, b.height)
print(sorted(b.model_dump(mode="python", by_alias=True, exclude_none=True)))
```

```
my-building-1 12.5
['geometry', 'height', 'id', 'level', 'theme', 'type', 'version']
```

No GeoJSON was parsed, produced, or consulted. If GeoJSON were the substrate, that
wouldn't be possible.

**"Is there GeoJSON code inside the Pydantic classes?"** Yes — in exactly one of them.
Counting mentions across everything `Building` inherits from:

```
Building             (building  )  0
OvertureFeature      (feature   )  0
Identified           (id        )  0
Feature              (feature   ) 17     <- the base class in overture-schema-system
Named                (names     )  0
Stacked              (level     )  0
Appearance           (_common   )  0
```

All of it lives in `Feature`, in one serializer and one validator — the code that reads
GeoJSON in and writes GeoJSON out. Zero mentions in the six classes that actually define
what a building *is*. GeoJSON is an I/O concern parked at the base of the hierarchy, not a
structure the schema is built on.

**"Is GeoJSON what's really being validated?"** No. What gets validated is the model. A
GeoJSON document is one accepted *input shape* — a flat dict is the other, and both end up
as the same Python object.

An analogy: a word processor's document isn't "wrapped around `.docx`." It has a document
model, and it can read and write `.docx`. Deleting that import/export code would not
change what a document is. Same here — delete the ten lines below and Overture models
still work; they just stop speaking GeoJSON.


The entire GeoJSON transformation is those ten lines, in `Feature`
(`packages/overture-schema-system/src/overture/schema/system/feature.py`):

```python
@model_serializer(mode="wrap")
def __serialize_with_geo_json_support__(self, serializer, info):
    data = serializer(self)  # <- the flat dict, produced first

    if info.mode == "json":  # <- only in JSON mode
        return {
            "type": "Feature",
            **({"id": data.pop("id")} if "id" in data else {}),
            **({"bbox": data.pop("bbox")} if "bbox" in data else {}),
            "geometry": data.pop("geometry"),
            "properties": data,  # <- everything else goes here
        }

    return data  # <- Python mode: flat, untouched
```

Read the first line: Pydantic produces the **flat** dictionary, and only then does this
function move `id`, `bbox`, and `geometry` to the top and sweep the remainder into
`properties`. In `python` mode the flat dict is returned unchanged and none of this runs.

So the layering is:

```
            Pydantic model  (flat — the actual schema)
                   |
        +----------+----------+
        |                     |
   python mode            json mode
        |                     |
   flat dict            GeoJSON envelope
   -> Parquet           -> .geojson
```

GeoJSON is a costume the model puts on for one specific audience. It isn't the body.

**The Pydantic model itself has no envelope.** In Python it's completely flat:

```python
from overture.schema.buildings import Building
print("id in model_fields       :", "id" in Building.model_fields)
print("geometry in model_fields :", "geometry" in Building.model_fields)
print("a 'properties' field?    :", "properties" in Building.model_fields)
```

```
id in model_fields       : True
geometry in model_fields : True
a 'properties' field?    : False
```

There is no `properties` field on `Building`, and `id` and `geometry` sit alongside
`height` and `num_floors` like any other field. The envelope is **not part of the model**.
It appears only when serializing to JSON, because that is what GeoJSON requires.

You can watch the same object take both shapes:

```python
import json, yaml
from overture.schema.buildings import Building

b = Building.model_validate_json(
    json.dumps(yaml.safe_load(open("examples/buildings/building-polygon.yaml"))))

print("python mode:", sorted(b.model_dump(mode="python", by_alias=True, exclude_none=True))[:8])
print("json mode  :", sorted(b.model_dump(mode="json",   by_alias=True, exclude_none=True)))
```

```
python mode: ['class', 'ext_bar', 'ext_foo', 'geometry', 'height', 'id', 'is_underground', 'level']
json mode  : ['geometry', 'id', 'properties', 'type']
```

One model, two renderings — and the flat one is the shape of the data you'd actually
download. Neither is more "real"; the model is what's real, and both are projections of
it.

**So which answer to "what's required" is correct?** The model's:

```
['geometry', 'id', 'theme', 'type', 'version']
```

The JSON Schema's two `required` arrays are that same list, split across the envelope
because that's where those fields land *in that particular output format*. Nobody decided
`geometry` belongs somewhere different from `theme`; GeoJSON did, in 2016.

This distinction is the single most important thing in this guide, and it returns in force
in [section 3](SCHEMA_GUIDE.md#3-writing-code-against-the-models) — where using the wrong mode for your
data shape is the most common way to get a confusing `ValidationError`.

---

## Two names per model

Because the registry has to stay correct when packages it has never heard of register
their own models.

The **canonical key is the entry-point string** — `overture.schema.buildings:Building`.
It includes the module path, so it is globally unique: no two packages can collide.

The **short name is a derived alias**. It is just the class name after the colon,
snake-cased:

```python
from overture.schema.system.discovery.entry_point import entry_point_class_alias

entry_point_class_alias("overture.schema.divisions:DivisionArea")  # 'division_area'
entry_point_class_alias("overture.schema.places:Place")  # 'place'
```

Short names are *not* guaranteed unique. Anyone can
[register their own feature types](AUTHORING.md#register-your-own-feature-types), and nothing
stops a third party from shipping its own `Place`. So the short name can't be the
identity — it's a convenience, because
`validate_model(df, "overture.schema.buildings:Building")` is miserable to type.

**The nice part is how it degrades.** The alias is offered only while it stays
unambiguous. `model_names()` counts aliases and includes only those appearing once, and
the resolver tries an exact key match first, then the alias:

```python
from overture.schema.system.discovery.entry_point import resolve_entry_point_key

registry = {"overture.schema.places:Place": ..., "acme.parks:Place": ...}

resolve_entry_point_key("place", registry)
# ValueError: Entry-point alias 'place' is ambiguous.
#             Specify one of: acme.parks:Place, overture.schema.places:Place

resolve_entry_point_key(
    "acme.parks:Place", registry
)  # 'acme.parks:Place' — always works
```

Install a package that collides and `place` simply stops being accepted, with an error
naming both candidates — rather than silently validating against the wrong model. The
fully-qualified key never stops working.

Two functions expose the two views:

| Function | Returns | Use when |
|---|---|---|
| `model_keys()` | the 15 canonical entry-point keys | you want the authoritative list |
| `model_names()` | all 30 accepted names | you want everything `validate_model` will take |

> **Skipping this step does not produce an error message.** It produces an empty
> registry. If `validate_model(df, "building")` raises a `KeyError`, or `model_names()`
> is empty, this is why.

---

## What makes a field required

Nobody maintains a list of required fields. **It's derived** — in Pydantic, a field with
no default is required, and a field with a default is optional:

```python
from overture.schema.buildings import Building
from pydantic_core import PydanticUndefined

for n in ["version", "theme", "height", "num_floors"]:
    f = Building.model_fields[n]
    d = "no default" if f.default is PydanticUndefined else f"default={f.default!r}"
    print(f"{n:12} {d:16} -> {'REQUIRED' if f.is_required() else 'optional'}")
```
```
version      no default       -> REQUIRED
theme        no default       -> REQUIRED
height       default=None     -> optional
num_floors   default=None     -> optional
```

So "who decided" becomes "where is the field declared." For a building, five fields are
required and four of them come from a shared base class rather than from buildings at all:

```python
from overture.schema.buildings import Building

for n, f in Building.model_fields.items():
    if not f.is_required():
        continue
    for cls in Building.__mro__:
        if n in getattr(cls, "__annotations__", {}):
            print(f"{n:10} -> {cls.__name__}")
            break
```
```
id         -> OvertureFeature
geometry   -> Building
theme      -> OvertureFeature
type       -> OvertureFeature
version    -> OvertureFeature
```

`id`, `theme`, `type`, and `version` are required of *every* Overture feature, declared
once in `OvertureFeature`:

```python
id: Id = Field(description="A feature ID. ...")
theme: ThemeT
type: TypeT
# Superclass `Feature` provides `geometry` and `bbox`.
version: FeatureVersion
```

None carries `= None`, so all four are mandatory. `Building` adds only `geometry`,
narrowing the inherited one to the polygon types a building may have.

In the generated JSON Schema those same five get split across the GeoJSON envelope — `id`
and `geometry` at the top, `theme`, `type`, and `version` inside `properties` — which is
why that document appears to have two answers to one question. It doesn't; it has one
answer written in the shape GeoJSON demands.

**The human answer:** the Overture Schema Working Group decides, and changes go through
the process in [CONTRIBUTING.md](CONTRIBUTING.md) — a PR plus a changelog fragment. Making
a field required is a breaking change, so it targets the `vnext` branch and waits for a
major release; making one optional is not, and can go to `main`.

---

## How tags work

Every feature type carries a handful of **tags**, and `overture-schema list-types` prints
them after the type name:

```
building           feature  overture  overture:theme=buildings
```

Three tags there. `feature` says this is a map feature rather than some other kind of
model. `overture` says Overture defined it. `overture:theme=buildings` says which theme it
belongs to.

**Why a tag rather than a field called `theme`?** Because the tooling has to work on
feature types it has never heard of. A field named `theme` would only mean something to
code that already knows Overture has themes; the CLI would have to hardcode that. A tag is
just a label the type declares about itself, and the CLI's job is only to match labels —
so `--tag overture:theme=buildings` and `--tag acme:product=parks` go through exactly the
same code path.

The `namespace:key=value` shape exists so that two organizations can both tag their types
without colliding. Everything Overture defines is namespaced under `overture:`; if you
register your own feature types, you pick your own namespace and your tags sit alongside
Overture's rather than competing with them. That is the whole extension mechanism — see
[Register your own feature types](AUTHORING.md#register-your-own-feature-types).

The bare tags (`feature`, `overture`) have no namespace because they are not claims about
a vendor's taxonomy — they are the two facts every Overture feature type shares.

---

## What the example file actually is

The guide validates `examples/buildings/building-polygon.yaml` as its first real command.
`examples/buildings/building-polygon.yaml` is a file **in the repo you just cloned**. It
is not data you downloaded. The `examples/` tree is the project's own corpus of
hand-written sample features, used as test fixtures and pulled into the documentation
site. This one describes a single building — a parking structure in Washington DC:

```yaml
id: overture:buildings:building:1234
type: Feature                      # ← GeoJSON envelope
geometry:
  type: Polygon
  coordinates: [[ [-77.036873, 38.897804], ... ]]
properties:
  ext_foo: I am a customer user property.   # ← custom, non-Overture
  theme: buildings                 # ← which theme
  type: building                   # ← which feature type
  version: 1
  height: 21.34
  num_floors: 4
  subtype: transportation
  class: parking
  sources:
  - property: ""
    dataset: microsoftMLBuildings
```

### See it actually catch something

A success message proves the command ran, not that it's checking anything. Copy the file
and break it:

```bash
cp examples/buildings/building-polygon.yaml /tmp/broken.yaml
```

Change `class: parking` to `class: skyscraper`:

```
class "skyscraper" ← Input should be 'agricultural', 'allotment_house',
                     'apartments', 'barn', 'beach_hut', ...
```

Change `height: 21.34` to `height: -5`:

```
height -5 ← Input should be greater than 0
```

Change `num_floors: 4` to `num_floors: 4.7`:

```
num_floors 4.7 ← Input should be a valid integer, got a number with a
                 fractional part
```

Enum membership, numeric bounds, integer-ness — each from the model definition, none of
it written by hand for this file.

> **What it does not catch:** free-form string fields accept any string. The real
> `building-polygon.yaml` in the repo has a stray trailing comma —
> `dataset: microsoftMLBuildings,` — which YAML reads as part of the value. It parses to
> the string `'microsoftMLBuildings,'` and validates clean, because `dataset` has no
> constraint beyond "is a string." Validation enforces the schema, not your typing.

---

## Why examples are YAML

**No — real Overture data is GeoJSON or Parquet.** YAML here is purely an authoring
convenience for the example files: it allows comments (`# Custom user properties.`) and
is easier to hand-edit than JSON.

The CLI accepts **JSON, YAML, and GeoJSON**, and YAML is a superset of JSON, so the
format is irrelevant to the validation. Convert the same file to JSON and you get the
same result:

```bash
uv run python -c "
import json, yaml
json.dump(yaml.safe_load(open('examples/buildings/building-polygon.yaml')),
          open('/tmp/same-building.json','w'), indent=2)"

uv run overture-schema validate /tmp/same-building.json
```
```
✓ Successfully validated /tmp/same-building.json
```

Same bytes of meaning, different serialization, identical outcome. Pick whichever is
convenient — you'll mostly hand JSON or GeoJSON to this command in real use.

---

## Why generated code is gitignored

Not because it's optional, and not because it's for a subset of users. **It's build
output.** The commit that introduced the package says so directly:

> The generated trees under `expressions/generated/` and `tests/generated/` are
> regenerable output of `make generate-pyspark` and are not tracked in git; `make check`
> and `make test-all` regenerate before running.

Three reasons that's the right call:

**One source of truth.** The Pydantic models define the schema; these expressions are a
derivative of them. Committing the derivative creates a second copy that can silently
drift — change a constraint, forget to regenerate, and the committed expressions keep
enforcing the old rule. Deleting them from git makes that failure impossible.

**Scale.** A full generation is **32 files and roughly 23,000 lines**:

```
15 expression modules   (one per feature type)
17 test modules         (conformance tests, split per union arm)
```

Every schema change would produce a mechanical diff of that size, burying the actual
change and guaranteeing merge conflicts.

**The build regenerates regardless.** `make check` and `make test-all` both depend on
`generate-pyspark`, which begins with `clean-pyspark` (`rm -rf`). The tree is rebuilt
from the current models every time, so a committed copy would never be read.

It's the same reasoning that keeps `dist/`, `*.o`, and `node_modules/` out of git.

### "Gitignored" does not mean "not shipped"

This is the part worth being clear about, since it sounds like these files are somehow
optional for users. **They are not.** Published wheels contain them.

`.github/workflows/publish-python-packages.yaml` runs `make generate-pyspark` before
`uv build`, then refuses to publish a wheel that lacks them:

```yaml
- name: Generate PySpark expressions before build
  if: matrix.package == 'overture-schema-pyspark'
  run: make generate-pyspark
```

```bash
if [ "$PACKAGE" = "overture-schema-pyspark" ] && \
   ! unzip -l "$wheel" | grep -q 'expressions/generated/.*\.py'; then
  echo "    Wheel [$wheel] has no generated expressions -- codegen did not run. Aborting!"
  exit 1
fi
```

So the only people who ever run `make generate-pyspark` are people working **from a git
clone** — because a clone is the one place these files don't already exist. Install from
a package index and they arrive with the package, like any other module.


---
