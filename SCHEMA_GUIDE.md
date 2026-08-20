# Overture Schema Guide

This is a practical guide to installing the Overture schema packages, exploring the models,
writing code against them, validating data, and generating artifacts from the schema.

Three other pages cover material this guide points to rather than repeats:
[CONCEPTS.md](CONCEPTS.md) for why the schema is built this way,
[TROUBLESHOOTING.md](TROUBLESHOOTING.md) for errors and gotchas, and
[AUTHORING.md](AUTHORING.md) for writing schema models. Reference for a single package
lives in that package's `README.md` under `packages/`.

*Note: none of these packages are on PyPI yet. Everything below installs from a local
clone. Any `pip install overture-schema` you find in a README is aspirational — it will
not work today.*

## Contents

1. [Install](#1-install)
2. [Exploring the models](#2-exploring-the-models)
3. [Writing code against the models](#3-writing-code-against-the-models)
4. [The three CLIs](#4-the-three-clis)
5. [Validating data](#5-validating-data)
6. [Converting the schema to other formats](#6-converting-the-schema-to-other-formats)
7. [Using the packages from your own project](#7-using-the-packages-from-your-own-project)
8. [Building tools on the models](#8-building-tools-on-the-models)

### Other pages

| Page | What's on it |
|---|---|
| [AUTHORING.md](AUTHORING.md) | Registering your own feature types, authoring new schema models, building an SDK or CLI, templates |
| [CONCEPTS.md](CONCEPTS.md) | Why Pydantic, why many packages, the GeoJSON envelope, and other *why* questions |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Symptom-indexed fixes, and the gotchas that cost people time |
| [GLOSSARY.md](GLOSSARY.md) | Data-model and toolchain vocabulary |

---

## 1. Install

### 1.1 First, what you're installing

**The schema is not one Python package. It's many Python packages.**

Open `packages/` and you'll see:

```
packages/
├── overture-schema                 ← a metapackage: depends on the others, ships no code
├── overture-schema-system          ← foundations: numeric types, geometry, discovery
├── overture-schema-common          ← Overture conventions: OvertureFeature, names, sources
├── overture-schema-cli             ← the `overture-schema` command
├── overture-schema-validation      ← validate() / validate_json()
├── overture-schema-codegen         ← the `overture-codegen` command
├── overture-schema-pyspark         ← the `overture-validate` command
└── overture-schema-theme-*         ← six of these: buildings, places, transportation, …
```

Each of those directories has its own `pyproject.toml` and its own version number.

They are separate packages so that **what you install decides what exists at runtime** —
install only the buildings theme and the tooling only knows about buildings. For why that
was worth the complexity, see
[Why the schema is many packages](CONCEPTS.md#why-the-schema-is-many-packages).

#### What you end up with

One command installs all the packages into **a single shared virtual environment at the repo root**:

```
schema/
├── .venv/                    ← created by uv; all packages live here
│   └── bin/
│       ├── overture-schema     ← the three CLIs land here
│       ├── overture-codegen
│       └── overture-validate
├── packages/
└── pyproject.toml
```


#### The packages form four layers

The packages depend on each other in one direction only — each layer below uses the one
above it, and never the reverse. That ordering is what lets the tooling work on feature
types nobody had written when the tooling was built.

| Layer | Package | Gives you |
|---|---|---|
| Foundation | `system` | `float32`/`uint8`/…, `Geometry`, `BBox`, `CountryCodeAlpha2`, constraint annotations, `Feature` base class, entry-point discovery |
| Overture conventions | `common` | `OvertureFeature` (id/theme/type/version/geometry/sources), `@scoped`, `Names`, `Sources`, cartography hints |
| Feature types | `theme-*` | `Building`, `Place`, `Segment`, `Address`, … plus their enums |
| Tooling | `cli`, `codegen`, `pyspark`, `validation` | commands and functions that consume the above generically |

The tooling layer never hardcodes feature types. It discovers them. That's why your own models can slot in.


### 1.2 Prerequisites

- **Python 3.10 or newer.** You don't need to install this yourself — `uv` will fetch a
  suitable Python if your system one is too old.
- **[`uv`](https://docs.astral.sh/uv/getting-started/installation/).**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

You do **not** need Java, Spark, or Homebrew for anything in sections 1 through 8 of this
guide except the PySpark parts. If you already have a Homebrew Spark installed, it may actively break things — see
[`FileNotFoundError` on `spark-submit`](TROUBLESHOOTING.md#filenotfounderror-on-spark-submit).


### 1.3 Install

```bash
git clone https://github.com/OvertureMaps/schema.git
cd schema
uv sync --all-packages
```

That's it. `uv sync --all-packages` creates `.venv/` and installs
all thirteen workspace members into it.

**This is the whole install for most people.** You can now validate data, explore models,
generate JSON Schema, and generate documentation.

**What about `make install`?** It works too, and nothing about it is risky. It's exactly
`uv sync --all-packages --all-extras` plus the PySpark generation step described in
[Do you need PySpark?](#14-do-you-need-pyspark) — so it just does more than most people
need. (No package in the workspace defines extras today, so `--all-extras` changes
nothing.) Use it if you'd rather run one command and have everything.


Run these commands. All should succeed:

```bash
uv run overture-schema --version
```

```
overture-schema, version 1.17.1
```

```bash
uv run overture-schema list-types
```

```
address            feature  overture  overture:theme=addresses
bathymetry         feature  overture  overture:theme=base
building           feature  overture  overture:theme=buildings
building_part      feature  overture  overture:theme=buildings
connector          feature  overture  overture:theme=transportation
division           feature  overture  overture:theme=divisions
division_area      feature  overture  overture:theme=divisions
division_boundary  feature  overture  overture:theme=divisions
infrastructure     feature  overture  overture:theme=base
land               feature  overture  overture:theme=base
land_cover         feature  overture  overture:theme=base
land_use           feature  overture  overture:theme=base
place              feature  overture  overture:theme=places
segment            feature  overture  overture:theme=transportation
water              feature  overture  overture:theme=base
```

```bash
uv run overture-schema validate examples/buildings/building-polygon.yaml
```
```
✓ Successfully validated examples/buildings/building-polygon.yaml
```

That file is a sample building that ships with the repo. For what's inside it, why it's
YAML, and proof that validation is really checking something, see
[the example file](CONCEPTS.md#what-the-example-file-actually-is).


### 1.4 Do you need PySpark?

Probably not. Answer honestly:

| I want to… | Need PySpark? |
|---|---|
| Validate files, explore models, write Python against them | **No** |
| Generate JSON Schema or markdown docs | **No** |
| Generate an SDK in another language | **No** |
| Validate millions of rows of Parquet, or data in S3 | **Yes** |
| Get a Spark `StructType` for a feature type | **Yes** |
| Run the full test suite (`make check`) | **Yes** |

**If no:** you're done. Go to section 2.

**If yes:** there's one more step, because the PySpark validation expressions are
*generated code that is not committed to git*. They're in `.gitignore`. `uv sync` alone
cannot produce them.

```bash
make generate-pyspark
```

Or `make install`, which is just `uv sync --all-packages --all-extras` followed by
`make generate-pyspark`. The command prints nothing on success. If `model_names()`
later comes back empty, see
[that entry in TROUBLESHOOTING.md](TROUBLESHOOTING.md#model_names-returns--or-keyerror-on-a-feature-type).

---

## 2. Exploring the models

You can't write code against a model you haven't looked at. This section is about finding
out what feature types exist, what fields they carry, and what values those fields
accept — before writing a line of code against them.

**Two things can answer your questions, and it's worth keeping them straight:**

| | What it is | Ask it with |
|---|---|---|
| **The model** | The Pydantic classes themselves. When you validate a file or a DataFrame, this is the code that accepts or rejects it. | Python: `Building.model_fields` |
| **The generated JSON Schema** | A description of the model, written out as a JSON document | `overture-schema json-schema` |

They always agree, because the second is generated from the first.

Ask the **model** when you want to understand the schema — it answers in flat Python, and
it is the thing that actually runs. Ask the **JSON Schema** when you need the rules in a
form another program can read: a validator in another language, a code generator, or a
tool that has no idea Python exists. Section 2.4 does the first, 2.5 the second.

### 2.1 Running Python against the models

Everything up to now has been shell commands. From here the guide switches to Python, so
first: how do you actually run it?

**The models are installed in the project's `.venv`, not in whatever `python` your shell
finds.** Starting Python the usual way fails:

```bash
python
```
```
>>> from overture.schema.buildings import Building
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ModuleNotFoundError: No module named 'overture'
```

`ModuleNotFoundError: No module named 'overture'` always means this: right code, wrong
interpreter. Compare the two:

```bash
python -c "import sys; print(sys.executable)"
uv run python -c "import sys; print(sys.executable)"
```

```
/Users/you/.pyenv/versions/3.10.15/bin/python
/path/to/schema/.venv/bin/python3
```

The first is your system or `pyenv` Python, which has never heard of these packages. The
second is the project's environment, where `uv sync` installed them. Nothing is broken —
they're simply two different Pythons.

Prefix with `uv run` and it works — that runs Python inside the project's environment:

```bash
uv run python -c "from overture.schema.buildings import Building; print(Building.__name__)"
```
```
Building
```

Three ways to run the Python in this guide, all from the repo root:

**A one-liner**, for a quick look:

```bash
uv run python -c "from overture.schema.buildings import Building; print(len(Building.model_fields))"
```

**An interactive session**, best for exploring — you can poke at a model, tab-complete,
and try things:

```bash
uv run python
```

```
Python 3.10.18
>>> from overture.schema.buildings import Building
>>> len(Building.model_fields)
26
```


**A script file**, once you're writing more than a couple of lines. Save this as
`explore.py` in the repo root:

```python
from overture.schema.buildings import Building

print(f"{len(Building.model_fields)} fields")

for name, field in Building.model_fields.items():
    if field.is_required():
        print(f"  required: {name}")
```

and run it:

```bash
uv run python explore.py
```

```
26 fields
  required: id
  required: geometry
  required: theme
  required: type
  required: version
```

Every Python block from here on is code to run one of these three ways. An interactive session is the best fit for section 2 —
you're looking things up, not building anything yet.

> You can also activate the environment once (`source .venv/bin/activate`) and then use
> plain `python`. This guide uses `uv run` throughout because it always works, needs no
> setup, and cannot be left half-done.

### 2.2 Where the models live

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

### 2.3 From the CLI: what types exist?

```bash
uv run overture-schema list-types
```

```
address            feature  overture  overture:theme=addresses
bathymetry         feature  overture  overture:theme=base
building           feature  overture  overture:theme=buildings
building_part      feature  overture  overture:theme=buildings
connector          feature  overture  overture:theme=transportation
division           feature  overture  overture:theme=divisions
division_area      feature  overture  overture:theme=divisions
division_boundary  feature  overture  overture:theme=divisions
infrastructure     feature  overture  overture:theme=base
land               feature  overture  overture:theme=base
land_cover         feature  overture  overture:theme=base
land_use           feature  overture  overture:theme=base
place              feature  overture  overture:theme=places
segment            feature  overture  overture:theme=transportation
water              feature  overture  overture:theme=base
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

Those trailing words — `feature`, `overture`, `overture:theme=addresses` — are **tags**.
Every feature type carries a few, and they are how you select a subset of types without
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

Tags are also the mechanism your own feature types use to join the set — see
[How tags work](CONCEPTS.md#how-tags-work).

### 2.4 Ask the model itself (Python)

This is the primary source. `Building` is an ordinary Python class, and Pydantic gives
every model a `model_fields` dict describing each field — its type, whether it's required,
its documentation, and its constraints. Nothing is generated or rendered here; this *is*
the schema.

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

Twenty-six fields, five of them required. Note the shape of that list: `id` and `geometry`
sit alongside `height` and `num_floors`, all at the same level. **A model is flat.**

That is worth pinning down now, because the data often isn't. If you've seen an Overture
building as GeoJSON, most of its fields were tucked inside a `properties` object, with
only `id`, `geometry`, and `type` outside it. That outer wrapper is called the
**envelope** — the fixed set of keys GeoJSON puts around every feature, the same for a
building as for a lake. The model has no envelope; it appears only when a model is written
out as GeoJSON. [Section 2.5](#25-ask-the-generated-json-schema) meets it again, and
[the GeoJSON envelope](CONCEPTS.md#the-geojson-envelope) explains where it comes from.

#### Every field at a glance

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

Some of those types look stranger than they are.
`typing.Optional[overture.schema.system.numeric.float64]` is just **"a float, or nothing"**
— `Optional[X]` means the field may be absent, and `float64` is an ordinary Python `float`
that the schema has given a narrower name:

```python
from overture.schema.system.numeric import float64

float64.__supertype__  # <class 'float'>
```

The schema declares `float64`, `int32`, `uint8` and friends so a field can say how wide it
is on the wire — which Parquet column type it becomes, what range it accepts — while
staying a plain number in Python. Same story for `Id` and `FeatureVersion`: named types
wrapping `str` and `int`. Only `Literal['building']` is different: it means the field must
be exactly that one string.

#### One field in detail

Each entry carries the documentation and constraints from the model declaration:

```python
f = Building.model_fields["height"]
print(f.description)  # 'Height of the building or part in meters.\n\n...'
print(f.metadata)  # [Gt(gt=0)]
print(f.alias)  # None
print(Building.model_fields["class_"].alias)  # 'class'
```

Note `class_` and its alias `class`. `class` is a Python keyword, so the field is named
`class_` on the model and `class` in the data — a mismatch that bites when serializing.
See [Gotchas](TROUBLESHOOTING.md#model-gotchas).

The next section reads exactly this information back out of the generated JSON Schema,
where it goes by different names: `f.description` becomes `description`, the `[Gt(gt=0)]`
in `f.metadata` becomes `exclusiveMinimum: 0`, and `f.is_required()` becomes membership in
a list called `required`. Same facts, second rendering.

### 2.5 Ask the generated JSON Schema

**Why bother, when 2.4 already answered these questions in Python?** Because the JSON
Schema is the version other programs can read. It's a plain JSON document, so a validator
written in Go, a code generator that emits TypeScript, or a form builder that has never
heard of Pydantic can all consume it. Reach for it when you're feeding a tool rather than
answering a question — and when you want to see the rules in the *GeoJSON* shape, since
that's what it describes.

Dump it for one type. Save it once rather than re-running the command for every question:

```bash
uv run overture-schema json-schema --type building > building.schema.json
```

That file is a few thousand lines, so the queries below use **`jq`** — a small
command-line tool for querying JSON. You give it a path like `.properties.height` and it
prints what's there. Install it with `brew install jq` or `apt install jq`. Anything here
you'd rather do in Python, you can: `json.load()` and the same paths as dictionary keys.

#### Finding a field

Overture's fields are three levels down, and the reason is the GeoJSON envelope: the
document describes a GeoJSON feature, so `id` and `geometry` sit at the top and everything
else is inside `properties`.

```bash
jq '.properties.properties.properties | keys' building.schema.json
```
```json
["class","facade_color","facade_material","has_parts","height","is_underground",
 "level","min_floor","min_height","names","num_floors","num_floors_underground",
 "roof_color","roof_direction","roof_height","roof_material","roof_orientation",
 "roof_shape","sources","subtype","theme","type","version"]
```

Three `properties` in a row, meaning something different each time:

| Path | Means |
|---|---|
| `.properties` | "the fields of this document" — a JSON Schema keyword |
| `.properties.properties` | the GeoJSON field actually *named* `properties` |
| `.properties.properties.properties` | "the fields inside that one" — the keyword again |

`id`, `geometry`, and `bbox` are missing from that list because they're on the envelope,
at `.properties.id` and so on — exactly where they sit in the data.

**Don't count levels — let `jq` find the path for you.** This works for any field:

```bash
jq -c 'paths | select(.[-1]=="height")' building.schema.json
```
```json
["properties","properties","properties","height"]
```

Worth knowing because a wrong path returns `null` rather than an error — `jq` treats "no
such key" as an answer, so a `null` usually means you stopped a level too high, not that
the field is missing.

#### Looking up one field's rules

```bash
jq '.properties.properties.properties.height' building.schema.json
```
```json
{
  "description": "Height of the building or part in meters.\n\nThis is the distance from the lowest point to the highest point.",
  "exclusiveMinimum": 0,
  "title": "Height",
  "type": "number"
}
```

**That object is not a value of `height` — in the data, `height` is just a number like
`21.34`.** It's the *rules* for `height`: must be a number, must be greater than zero.
Every field gets an object like this even when the field is a bare number, because
there's nowhere else to hang a description and a constraint.

Nobody wrote that JSON. Each line is rendered from the field's Python declaration in
`overture/schema/buildings/_common.py`:

| Schema keyword | Comes from |
|---|---|
| `"type": "number"` | the `float64` annotation |
| `"exclusiveMinimum": 0` | `gt=0` — greater than, not greater-or-equal |
| `"description"` | the `description=` argument |
| `"title": "Height"` | generated by Pydantic from the field name |

That is why the JSON Schema, the validation errors, the PySpark checks, and the generated
docs can't drift apart: they're all renderings of the same declaration.
[Section 6](#6-converting-the-schema-to-other-formats) produces the rest of them.

#### Listing the valid values for a field

Enums and shared structures sit at the top level under `$defs`, not inline:

```bash
jq -r '.["$defs"] | keys[]' building.schema.json
```
```
BuildingClass BuildingSubtype FacadeMaterial NameRule NameVariant Names
PerspectiveMode Perspectives RoofMaterial RoofOrientation RoofShape Side SourceItem
```

So the full list of values a field accepts, without reading any Python:

```bash
jq -r '.["$defs"].BuildingClass.enum[]' building.schema.json | head
```
```
agricultural
allotment_house
apartments
barn
beach_hut
boathouse
bridge_structure
bungalow
```

#### Which fields are required

The envelope splits this across **two** lists, one per level:

```bash
jq '.required' building.schema.json
jq '.properties.properties.required' building.schema.json
```
```json
["type","id","geometry","properties"]
["theme","type","version"]
```

Read together they are the same five fields 2.4 gave you — `id` and `geometry` on the
envelope, `theme`, `type`, and `version` inside `properties`. Reading only the second list
and calling it "the required fields of a building" undercounts by exactly the fields the
envelope owns.

`required` is always relative to the object it sits in; nested structures like `Names` and
`SourceItem` carry their own. **For this particular question the model is the easier
place to ask**, since it has no envelope to split the answer across:

```python
from overture.schema.buildings import Building

print(sorted(n for n, f in Building.model_fields.items() if f.is_required()))
```
```
['geometry', 'id', 'theme', 'type', 'version']
```

Nobody maintains that list by hand — it falls out of whether a field has a default. For
how that works, and who decides, see
[What makes a field required](CONCEPTS.md#what-makes-a-field-required).

#### What a subschema doesn't tell you

The object you get back for `height` is the complete machine-checkable contract for
`height` — but only for `height`, and only in isolation. Three things it does *not* say:

- **Whether the field may be omitted.** That lives in a sibling `required` array. A
  subschema describes the value *if present*.
- **That the number is in meters.** "in meters" is in `description` — prose for humans.
  Nothing rejects a value recorded in feet.
- **Anything about other fields.** The schema *can* express cross-field rules — that's
  what `@require_any_of` and `@forbid_if` in `overture-schema-system` are for — but no
  such rule ties `height` to `min_height`, so a building with a floor above its roof
  validates clean:

```python
import json, yaml
from overture.schema.buildings import Building

d = yaml.safe_load(open("examples/buildings/building-polygon.yaml"))
d["properties"]["height"] = 5
d["properties"]["min_height"] = 100      # a floor above the roof
print("accepted:", Building.model_validate_json(json.dumps(d)).height)
```

```
accepted: 5.0
```

Validation enforces the schema, not correctness.

#### jq or Python?

Use `jq` when you want the schema exactly as it ships, or when you're feeding it to
another tool — [generating an SDK](#81-generate-an-sdk-from-json-schema-any-language), for
instance. Use Python when you want to understand the model: `Building.model_fields` gives
you the same facts flat, with no envelope to walk, and a wrong field name raises instead
of quietly returning `null`.

### 2.6 From Python: enumerate everything that's installed

```python
from overture.schema.system.discovery import discover_models

for key, model in sorted(discover_models().items(), key=lambda kv: kv[0].name):
    print(f"{key.name:20} {key.entry_point:45} {sorted(key.tags)}")
```

```
address              overture.schema.addresses:Address             ['feature', 'overture:theme=addresses']
building             overture.schema.buildings:Building            ['feature', 'overture:theme=buildings']
segment              overture.schema.transportation:Segment        ['feature', 'overture:theme=transportation']
...
```

A `ModelKey` carries `.name`, `.entry_point` (`"module:Class"`), and `.tags`
(a `frozenset[str]`). Filter the same way the CLI does:

```python
from overture.schema.system.discovery import TagSelector, discover_models, filter_models

models = discover_models()

buildings = filter_models(
    models, TagSelector(include_any=("overture:theme=buildings",))
)
```

`TagSelector` takes `include_any` (OR scope), `require_all` (AND narrowing), and
`exclude_any` (OR-NOT). An empty selector returns the input unchanged.

### 2.7 Reading enum member documentation

Enum members carry per-value docstrings, but `member.__doc__` falls back to the *class*
docstring when a member has none — so reading `__doc__` directly gives you misleading
results:

```python
from overture.schema.buildings import RoofShape

[(m.value, m.__doc__.strip()[:30]) for m in list(RoofShape)[:2]]
# [('dome', 'The shape of the roof.'), ('flat', 'The shape of the roof.')]
#   ^ that's the class docstring repeated, not per-member documentation
```

Use the codegen extractor, which does the fallback detection for you:

```python
from overture.schema.codegen.extraction.enum_extraction import extract_enum
from overture.schema.common.scoping.travel_mode import TravelMode

spec = extract_enum(TravelMode)
for m in spec.members[:4]:
    print(f"{m.value:14} {m.description or '—'}")
```

```
vehicle        —
motor_vehicle  Includes car, truck and motorcycle
car            —
truck          —
```

`description` is `None` when the member has no documentation of its own.

### 2.8 Generate browsable reference docs

For sustained exploration, generate the full markdown reference and read it in your
editor:

```bash
uv run overture-codegen generate --format markdown --output-dir ./schema-docs
```

You get one page per feature type, per enum, and per named type, with field tables,
prose constraint descriptions, cross-page links, and validated examples:

```
schema-docs/buildings/building.md
schema-docs/buildings/building_part.md
schema-docs/buildings/types/building_class.md
schema-docs/buildings/types/roof_shape.md
schema-docs/common/names.md
schema-docs/common/sources.md
schema-docs/system/numeric.md
...
```

Scope it to one theme with the same tag options:

```bash
uv run overture-codegen generate --format markdown \
  --tag overture:theme=buildings --output-dir ./schema-docs
```

(Supplementary types from `common/` and `system/` are pulled in regardless, since the
feature pages link to them.)

---

## 3. Writing code against the models

Section 2 was about finding out what exists. This section is about using it: loading
real data into models, reading and changing it, and writing it back out.

### 3.1 A complete example, start to finish

Before any of the details, here is the whole job in one piece: load a feature, read it,
change it, write it back out, and confirm it still validates. Everything else in this
section is an explanation of a line in this snippet.

```python
import json, yaml
from overture.schema.buildings import Building

# 1. LOAD — the file is GeoJSON, so go through JSON mode
doc = yaml.safe_load(open("examples/buildings/building-polygon.yaml"))
b = Building.model_validate_json(json.dumps(doc))
print("1. loaded :", b.id)

# 2. READ — plain Python attributes; enums come back as enum members
print("2. read   :", b.height, "m,", b.num_floors, "floors, class", b.class_.value)

# 3. MODIFY — ordinary assignment
b.height = 25.0
b.num_floors = 5
print("3. changed:", b.height, "m,", b.num_floors, "floors")

# 4. WRITE — by_alias=True so `class_` is written as `class`
out = b.model_dump(mode="json", by_alias=True, exclude_none=True)
print("4. wrote  :", json.dumps(out)[:70], "...")

# 5. CONFIRM — the output is valid input
again = Building.model_validate_json(json.dumps(out))
print("5. re-read:", again.height, "m — round-trip holds")
```

```
1. loaded : overture:buildings:building:1234
2. read   : 21.34 m, 4 floors, class parking
3. changed: 25.0 m, 5 floors
4. wrote  : {"type": "Feature", "id": "overture:buildings:building:1234", "geometr ...
5. re-read: 25.0 m — round-trip holds
```

That is the shape of nearly every job: **validate in, work with plain Python objects,
serialize out.** In between, `b` is an ordinary object — attributes, assignment, no
special API.

Three lines in there are load-bearing, and each gets a subsection below:

| Line | Why it's written that way | Where |
|---|---|---|
| `model_validate_json(json.dumps(doc))` | the file is GeoJSON, which needs JSON mode | [3.2](#32-the-one-thing-to-understand-two-representations) |
| `b.class_.value` | the field is `class_` in Python, `class` in the data | [3.3](#33-reading-fields) |
| `by_alias=True, exclude_none=True` | without them the output won't re-validate | [3.4](#34-writing-data-back-out) |

If the snippet above ran, you already know enough to be useful. Read on when one of those
lines bites you, or read straight through if you'd rather know why now.

### 3.2 The one thing to understand: two representations

Overture publishes data in one shape — flat and tabular, the column layout of the
Parquet release. The models also read and write GeoJSON, so the schema works with tools
that expect features rather than rows, and because that is the representation the
generated [JSON Schema](#61-json-schema) describes. **Which one you get depends on the
Pydantic mode you use, not on the data you pass.**

| Shape | Looks like | Pydantic mode | Validate with | Dump with |
|---|---|---|---|---|
| **GeoJSON** | `id`/`geometry` at top level, everything else under `properties` | `json` | `model_validate_json()` | `model_dump(mode="json")`, `model_dump_json()` |
| **Flat / tabular** (Parquet-style) | every field at the top level | `python` | `model_validate()` | `model_dump(mode="python")` |

This trips people up constantly. Passing a GeoJSON *dict* to `model_validate()` fails,
because `model_validate` is Python mode and Python mode expects the flat shape:

```python
import json, yaml
from overture.schema.buildings import Building

doc = yaml.safe_load(open("examples/buildings/building-polygon.yaml"))  # GeoJSON-shaped

Building.model_validate(doc)
# ValidationError: 3 validation errors for building
#   theme     Field required
#   type      Input should be 'building'   [got 'Feature']
#   version   Field required
```

The `type: Feature` in the error message is the tell: it read the GeoJSON envelope's
`type` as the feature's `type` field.

The fix — round-trip through JSON so you're in JSON mode:

```python
building = Building.model_validate_json(json.dumps(doc))  # works
```

Or, if you're already reading from a file or an HTTP response, skip the parse entirely:

```python
building = Building.model_validate_json(open("building.geojson").read())
```

#### Can't I just tell `model_validate` to use JSON mode?

No. It's the obvious thing to try, and neither knob does it:

```python
Building.model_validate(doc, context={"mode": "json"})  # still ValidationError
Building.model_validate(doc, strict=False)  # still ValidationError
```

The mode isn't a setting you pass — in Pydantic it's determined by *which method you
call*. `model_validate` is Python mode; `model_validate_json` is JSON mode. The base
`Feature` class keys off exactly that:

```python
@model_validator(mode="wrap")
def __validate_with_geo_json_support__(cls, data, handler, info):
    if info.mode == "json":  # <- set by the method, not by an argument
        ...  #    unpack the GeoJSON envelope
```

So if you have a GeoJSON **dict** in hand, `json.dumps` it and use
`model_validate_json`. The round-trip is slightly wasteful but it is the supported path:

```python
Building.model_validate_json(json.dumps(doc))
```

Better still, avoid making the dict at all. If the GeoJSON came from a file or an HTTP
response, hand the raw text straight to `model_validate_json` and skip `json.loads`
entirely. The one case where you genuinely can't is YAML — there's no YAML mode, so
`yaml.safe_load` → `json.dumps` → `model_validate_json` is the route, as in the example
above.

#### Reading the error

The three errors from a mode mismatch are always the same shape, and worth recognising on
sight:

```
theme     Field required
type      Input should be 'building'  [input_value='Feature']
version   Field required
```

`theme` and `version` are "missing" because they're really down inside `properties`, where
Python mode isn't looking. And `type` came back as `'Feature'` — the envelope's type,
which is the giveaway. **If you ever see `input_value='Feature'` in a validation error,
you passed GeoJSON to a Python-mode call.**

For flat data — a Parquet row, a DuckDB result, a dict of columns — `model_validate` is
the right call:

```python
row = {
    "id": "...",
    "theme": "buildings",
    "type": "building",
    "version": 1,
    "geometry": ...,
    "height": 21.34,
    "class": "parking",
}
building = Building.model_validate(row)
```

### 3.3 Reading fields

Model attributes are plain Python. Enums come back as enum members, geometry as a
`Geometry` wrapper around Shapely:

```python
building.height  # 21.34
building.class_  # <BuildingClass.PARKING: 'parking'>
building.class_.value  # 'parking'
building.num_floors  # 4
type(building.geometry)  # <class 'overture.schema.system.geometric.geom.Geometry'>
```

### 3.4 Writing data back out

Some fields are Python keywords, so the model attribute differs from the wire name
(`class_` on the model, `class` in the data). **`model_dump()` uses attribute names by
default**, which produces output that will not validate back:

```python
d = building.model_dump(mode="json")
sorted(d["properties"])
# ['class_', 'ext_bar', 'height', ...]      ← 'class_' is wrong for the wire

Building.model_validate(building.model_dump(mode="python"))
# ValidationError: invalid extra field name: class_
```

With `by_alias=True` both round-trips work:

```python
geojson = building.model_dump(mode="json", by_alias=True, exclude_none=True)
sorted(geojson["properties"])
# ['class', 'ext_bar', 'height', 'is_underground', 'level', 'num_floors', ...]

Building.model_validate_json(json.dumps(geojson))  # OK
Building.model_validate(
    building.model_dump(mode="python", by_alias=True, exclude_none=True)
)  # OK
```

Same for `model_dump_json()`:

```python
'"class":' in building.model_dump_json()  # False  ← emits "class_"
'"class":' in building.model_dump_json(by_alias=True)  # True
```

**Rule of thumb: `by_alias=True` on every dump, unless you specifically want Python
attribute names.** `exclude_none=True` is usually what you want too — otherwise you get
every unset optional field as an explicit `null`.

### 3.5 Working with `Segment` and other unions

`Segment` is a discriminated union type alias over `RoadSegment`, `RailSegment`, and
`WaterSegment` — not a model class. It has no `model_validate`:

```python
from overture.schema.transportation import Segment

type(Segment)  # <class 'typing._AnnotatedAlias'>
Segment.model_validate({...})
# AttributeError: model_validate
```

Wrap it in a `TypeAdapter`:

```python
from pydantic import TypeAdapter
from overture.schema.transportation import Segment

segments = TypeAdapter(Segment)

seg = segments.validate_json(raw_geojson_string)  # JSON mode  → GeoJSON
seg = segments.validate_python(flat_row)  # Python mode → flat
type(seg).__name__  # 'RoadSegment'
```

Build the `TypeAdapter` once and reuse it; construction is the expensive part.

The concrete arms *are* ordinary classes if you know which one you want:

```python
from overture.schema.transportation import RoadSegment
```

### 3.6 Validating without knowing the type

`overture-schema-validation` checks a record against every installed model and returns
whichever matched:

```python
from overture.schema.validation import validate, validate_json

feature = validate_json(geojson_string)  # JSON mode  → GeoJSON shape
type(feature).__name__  # 'Building'

feature = validate(flat_dict)  # Python mode → flat shape
```

Both raise `pydantic.ValidationError` when nothing matches. The same mode rule from
[The one thing to understand first](#32-the-one-thing-to-understand-two-representations) applies: `validate()` is
Python mode and wants flat data, `validate_json()` is JSON mode and wants GeoJSON.

Which models participate is resolved at runtime by entry-point discovery — install more
theme packages and these functions accept more.

### 3.7 Generating JSON Schema in code

```python
from overture.schema.system.json_schema import json_schema
from overture.schema.buildings import Building
from overture.schema.places import Place

schema = json_schema(Building)
schema["title"]  # 'building'
sorted(schema)  # ['$defs', 'additionalProperties', 'description',
#  'properties', 'required', 'title', 'type']

union = json_schema(Building | Place)  # unions work too → anyOf
```

Use this rather than Pydantic's `model_json_schema()`. The Overture generator treats
`T | None = None` as "omit when unset" instead of Pydantic's "nullable with a null
default", which is what the data actually means.

---

## 4. The three CLIs

Installing the workspace gives you three commands, from three different packages.

| Command | Purpose | Full reference |
|---|---|---|
| `overture-schema` | Validate files, emit JSON Schema, list types | [`packages/overture-schema-cli/`](packages/overture-schema-cli/) |
| `overture-codegen` | Generate markdown docs and PySpark expressions | [`overture-schema-codegen/README.md`](packages/overture-schema-codegen/README.md) |
| `overture-validate` | Validate Parquet/S3 data at scale with Spark | [`overture-schema-pyspark/README.md`](packages/overture-schema-pyspark/README.md) |

Prefix each with `uv run` inside the repo, or activate the venv.

**This section shows what each command is for and one working invocation of each.** The
complete option lists live in the package READMEs linked above, which are versioned with
the packages they document.

### 4.1 `overture-schema`

```
Usage: overture-schema [OPTIONS] COMMAND [ARGS]...

Commands:
  json-schema  Generate JSON schema for Overture Maps types.
  list-types   List all available types.
  validate     Validate Overture Maps data against schemas.
```

All three subcommands take the shared `--tag` / `--filter` / `--exclude` options from
[From the CLI: what types exist?](#23-from-the-cli-what-types-exist). `validate` and `json-schema` also take
`--type NAME` to target one type directly.

```bash
# What types do I have?
overture-schema list-types
overture-schema list-types --group-by overture:theme

# Validate
overture-schema validate data.geojson
overture-schema validate - < data.geojson
overture-schema validate --type building data.json
overture-schema validate --tag overture:theme=buildings data.json
overture-schema validate --show-field id data.json

# JSON Schema
overture-schema json-schema > all-types.json
overture-schema json-schema --type building > building.json
overture-schema json-schema --tag overture:theme=buildings > buildings.json
```

Exit codes: `0` on success, `1` on validation failure — so it drops into CI directly.

#### Local files or remote?

It depends which CLI, and the two answer differently.

| Command | Remote paths | How |
|---|---|---|
| `overture-schema validate` | **no** | pipe through stdin with `-` |
| `overture-validate` (PySpark) | **yes** | `s3a://` natively, anonymous credentials preconfigured |

`overture-schema validate` takes a filesystem path only. Hand it a URL and it fails —
note that it even mangles the `//`, because the argument is parsed as a path:

```bash
overture-schema validate https://raw.githubusercontent.com/OvertureMaps/schema/main/examples/buildings/building-polygon.yaml
```

```
Error: 'https:/raw.githubusercontent.com/.../building-polygon.yaml' is not a file.
```

The fix is the `-` argument, which reads stdin. Anything that can fetch bytes can feed it:

```bash
curl -sSf https://raw.githubusercontent.com/OvertureMaps/schema/main/examples/buildings/building-polygon.yaml \
  | overture-schema validate -
```

```
✓ Successfully validated <stdin>
```

That works for anything on stdin — `aws s3 cp ... -`, a database query, a generator
script, another program's output. The only thing you lose is the filename in the output,
which becomes `<stdin>`.

`overture-validate` is the opposite: it's built for remote data. `s3a://` paths are
detected automatically and configured with anonymous credentials, so the public Overture
release bucket needs no setup:

```bash
overture-validate segment s3a://overturemaps-us-west-2/release/2026-07-22.0
```

> **Don't hardcode a release version.** The bucket keeps only the current release, so any
> version written into a script or a doc stops working at the next publish. Ask the bucket
> instead:
>
> ```bash
> curl -sS "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/?list-type=2&prefix=release/&delimiter=/" \
>   | tr '<' '\n' | grep -oE 'Prefix>release/[^/]+' | sed 's|Prefix>release/||' | sort -r | head -1
> ```
>
> ```
> 2026-07-22.0
> ```
>
> Then use it:
>
> ```bash
> RELEASE=$(curl -sS "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/?list-type=2&prefix=release/&delimiter=/" \
>   | tr '<' '\n' | grep -oE 'Prefix>release/[^/]+' | sed 's|Prefix>release/||' | sort -r | head -1)
> overture-validate segment "s3a://overturemaps-us-west-2/release/$RELEASE"
> ```
>
> The version shown in the examples here was current when this was written; treat it as a
> placeholder, not a fact.


That difference is not arbitrary. `overture-schema validate` is for a file you're looking
at — an example, a fixture, one feature you're debugging. `overture-validate` is for a
release: millions of rows, read in parallel by Spark, where "download it first" isn't an
option.

### 4.2 `overture-codegen`

Two commands: `generate` writes code or docs from the discovered models, `list` shows
what it discovered. `generate` takes `--format markdown` or `--format pyspark`, the
same `--tag`/`--filter`/`--exclude` options as `overture-schema`, and an `--output-dir`.

```bash
# Markdown reference docs
overture-codegen generate --format markdown --output-dir ./schema-docs
overture-codegen generate --format markdown --tag overture:theme=places --output-dir ./out

# PySpark validation expressions (this is what `make generate-pyspark` runs)
overture-codegen generate --format pyspark \
  --output-dir packages/overture-schema-pyspark/src/overture/schema/pyspark/expressions/generated \
  --test-output-dir packages/overture-schema-pyspark/tests/generated
```

### 4.3 `overture-validate`

Validates real data volumes with Spark. Requires the generated expression tree, so run
`make install` or `make generate-pyspark` first.

Takes a feature type and a path:

```bash
overture-validate building local.parquet
overture-validate segment s3a://overturemaps-us-west-2/release/2026-07-22.0
overture-validate place data.parquet --count-only
overture-validate segment data.parquet --suppress version:bounds -o violations.parquet
```

It handles S3A and anonymous credentials for the public Overture bucket automatically,
and expands a release root into the Hive partition path for you. The flags shown above
are the common ones; for the full list — output paths, error-row limits, Spark config,
schema-mismatch and check suppression — see
[`packages/overture-schema-pyspark/README.md`](packages/overture-schema-pyspark/README.md).

---

## 5. Validating data

Three tiers, pick by data size.

### 5.1 One file, or a handful — the CLI

Accepts JSON, YAML, and GeoJSON. A single feature, a JSON array of features, or a
`FeatureCollection` all work:

```bash
overture-schema validate examples/buildings/building-polygon.yaml
```

```
✓ Successfully validated examples/buildings/building-polygon.yaml
```

Failures come back as a rendered table showing the offending value in context:

```bash
overture-schema validate --show-field id counterexamples/buildings/negative-height.json
```

```
 ─ Validation Failed id=foo ────────────────────────────────────────────────────
       ...
        id "foo"
   version     0
    height -1.23 ← Input should be greater than 0
 ──────────────────────────────────────────────────────────────────────────────
```

For a collection, errors are indexed and labeled by the model that best fit:

```
 ─ [1] (Building) ──────────────────────────────────────────────────────────────
       ...
   version     0
    height -1.23 ← Input should be greater than 0
 ──────────────────────────────────────────────────────────────────────────────
```

Narrow the candidate set to sharpen the error messages — with `--type building` the CLI
stops guessing which model you meant:

```bash
overture-schema validate --type building data.json
```

Every check comes from the model definition — nothing is hand-written per file. Copy an
example, edit a field, and you can watch each kind fire:

| Edit | What validation says |
|---|---|
| `class: parking` → `class: skyscraper` | `Input should be 'agricultural', 'allotment_house', ...` |
| `num_floors: 4` → `num_floors: 4.7` | `Input should be a valid integer, got a number with a fractional part` |
| delete the `theme:` line | `Ambiguous: Data matches multiple types equally` |

What it does **not** catch: free-form string fields accept any string, and nothing checks
fields against each other. Validation enforces the schema, not correctness.

### 5.2 In a Python pipeline

```python
from pydantic import ValidationError
from overture.schema.validation import validate_json

ok, bad = 0, []
for line in open("features.ndjson"):
    try:
        validate_json(line)
        ok += 1
    except ValidationError as e:
        bad.append((line[:60], e.errors()))

print(f"{ok} valid, {len(bad)} invalid")
```

`e.errors()` gives you structured dicts with `loc`, `msg`, `type`, and `input` — the
right thing to log or turn into a report. Package reference:
[`packages/overture-schema-validation/README.md`](packages/overture-schema-validation/README.md).

If you know the type, validate against it directly for better errors and speed:

```python
from overture.schema.buildings import Building

Building.model_validate_json(line)
```

### 5.3 At scale — PySpark

```python
from pyspark.sql import SparkSession
from overture.schema.pyspark import validate_model, explain_errors

spark = SparkSession.builder.getOrCreate()
df = spark.read.parquet("s3a://.../theme=buildings/type=building/")

result = validate_model(df, "building")
result.evaluated.cache()

total = result.evaluated.count()
errors = result.error_rows().count()
print(f"{errors} / {total} rows with errors")

if errors:
    violations = explain_errors(result.evaluated, result.checks)
    violations.select("id", "field", "check", "message").show(truncate=False)
```

`validate_model` accepts either the short name (`"building"`) or the full entry-point key
(`"overture.schema.buildings:Building"`). It looks up the feature type in the registry,
compares the DataFrame schema against the expected one, and evaluates every check in a
single pass — no per-row Python, so it scales.

| Function | Returns | Purpose |
|---|---|---|
| `validate_model(df, type)` | `ValidationResult` | Registry lookup, schema comparison, check evaluation |
| `result.error_rows()` | `DataFrame` | Rows with at least one violation |
| `explain_errors(evaluated, checks)` | `DataFrame` | One row per violation: `field`, `check`, `message` |
| `model_names()` | `list[str]` | Available type names |

Tuning, partition handling, and the rest of the PySpark API are documented in
[`packages/overture-schema-pyspark/README.md`](packages/overture-schema-pyspark/README.md).
If `model_names()` comes back empty, see
[Troubleshooting](TROUBLESHOOTING.md#model_names-returns--or-keyerror-on-a-feature-type).

### 5.4 Validating the schema itself

If you're changing the models rather than the data:

```bash
make check
make test
make update-baselines
```

The theme packages carry golden-file baseline tests of their generated JSON Schema, so
unintended schema drift fails CI. After an intentional change, run `make
update-baselines` and inspect the `git diff` on the regenerated golden files before
committing.

---

## 6. Converting the schema to other formats

Three built-in targets, plus everything reachable through JSON Schema.

| Target | Command | Output |
|---|---|---|
| JSON Schema | `overture-schema json-schema` | A JSON Schema document on stdout |
| Markdown | `overture-codegen generate --format markdown` | Docusaurus-ready reference pages |
| PySpark | `overture-codegen generate --format pyspark` | Python modules of `Check` builders + `StructType` |
| Spark `StructType` | (Python, via the pyspark registry) | A live Spark schema object |

### 6.1 JSON Schema

The interop format — this is your bridge to every other ecosystem.

```bash
# One type
overture-schema json-schema --type building > building.schema.json

# One theme
overture-schema json-schema --tag overture:theme=transportation > transportation.schema.json

# Everything (an `anyOf` over all installed types)
overture-schema json-schema > overture.schema.json
```

A single type produces a self-contained document with its dependencies inlined under
`$defs`:

```
$ jq 'keys' building.schema.json
["$defs", "additionalProperties", "description", "properties", "required", "title", "type"]

$ jq '.title, (.["$defs"] | length)' building.schema.json
"building"
13
```

All types produce `{"anyOf": [...], "$defs": {...}}`.

In Python:

```python
from overture.schema.system.json_schema import json_schema
from overture.schema.buildings import Building

schema = json_schema(Building)
```

### 6.2 Markdown

Covered in [Generate browsable reference docs](#28-generate-browsable-reference-docs). Output is Docusaurus-flavored
(frontmatter plus `_category_.json` files), but it's plain markdown underneath and reads
fine in any editor or static site generator.

### 6.3 PySpark expressions and Spark schemas

```bash
overture-codegen generate --format pyspark --output-dir ./ps --test-output-dir ./ps-tests
```

You get one module per feature type, mirroring the Python package layout:

```
ps/overture/schema/buildings/building.py
ps/overture/schema/buildings/building_part.py
ps-tests/overture/schema/buildings/test_building.py
```

Each module is auto-generated (`# Do not edit`) and contains one builder function per
constraint, returning a `Check` with an unevaluated PySpark `Column`:

```python
def _version_bounds_check() -> Check:
    return Check(
        field="version",
        name="bounds",
        expr=check_bounds(F.col("version"), ge=0),
        shape=CheckShape.SCALAR,
        root_field="version",
    )
```

Plus a `MODEL_VALIDATION` constant pairing the checks with the expected `StructType`.

**To get a Spark schema for a feature type** — useful for `spark.read.schema(...)`,
Delta table creation, or comparing against your own tables:

```python
from overture.schema.pyspark._registry import REGISTRY
from overture.schema.pyspark.validate import resolve_entry_point_key

key = resolve_entry_point_key("building", REGISTRY)
struct = REGISTRY[key].schema

type(struct).__name__  # 'StructType'
[(f.name, f.dataType.simpleString()) for f in struct.fields][:5]
```

```
[('id', 'string'),
 ('bbox', 'struct<xmin:double,xmax:double,ymin:double,ymax:double>'),
 ('geometry', 'binary'),
 ('theme', 'string'),
 ('type', 'string')]
```

`REGISTRY` is keyed by the full entry-point string
(`"overture.schema.buildings:Building"`), which is why the `resolve_entry_point_key`
step is there — it accepts the short alias too. `ModelValidation` exposes `.schema`,
`.checks`, and `.geometry_types`.

Since `StructType` has `.json()` and `.jsonValue()`, this is also your route to an
Arrow/Parquet schema.

For the generator's own architecture and programmatic API — the shape extraction layer
these modules are rendered from — see
[`packages/overture-schema-codegen/README.md`](packages/overture-schema-codegen/README.md).
To write a new output format, see [AUTHORING.md](AUTHORING.md#write-a-new-codegen-target).

---

## 7. Using the packages from your own project

Everything above assumes you're working *inside* the schema repo. If instead you're
building your own application that depends on these models, you don't use the workspace
at all — you point `uv` at the package directories on disk.

Depend on the **theme packages you actually need**, not the workspace root:

```toml
# myapp/pyproject.toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "overture-schema-theme-buildings",
    "overture-schema-cli",
]

[tool.uv.sources]
overture-schema-theme-buildings = { path = "/path/to/schema/packages/overture-schema-theme-buildings", editable = true }
overture-schema-cli             = { path = "/path/to/schema/packages/overture-schema-cli",             editable = true }
```

```bash
cd myapp
uv sync
uv run python -c "from overture.schema.buildings import Building; print(Building.__name__)"
```
```
Building
```

`editable = true` means edits in your schema clone take effect immediately in `myapp` —
useful if you're changing both.

### 7.1 The payoff: install set = runtime set

In the `myapp` project above, only the buildings theme is installed. So:

```bash
cd myapp && uv run overture-schema list-types
```
```
building       feature  overture:theme=buildings
building_part  feature  overture:theme=buildings
```

Two types, not fifteen. **The same CLI binary, scoped by what's installed.** Nothing was
configured to make that happen — the models register themselves through entry points, and
the tooling discovers whatever is present.

This is worth internalizing early, because it's the whole extension story: add your own
package that registers models, and your feature types appear in `list-types`, validate
through the same commands, and show up in generated docs, alongside Overture's. See
[Register your own feature types](AUTHORING.md#register-your-own-feature-types).

### 7.2 If you'd rather have everything

`overture-schema` is a metapackage depending on all six themes plus validation and the
CLI:

```toml
[tool.uv.sources]
overture-schema = { path = "/path/to/schema/packages/overture-schema", editable = true }
```

One caveat: `import overture.schema` gives you nothing directly. It's a namespace root
that ships only a `py.typed` marker — no models, no functions. Always import from the
theme packages:

```python
from overture.schema.buildings import Building  # ✓
from overture.schema import Building  # ✗ ImportError
```


---

### 7.3 What changes once these packages are published

Some of this section is scaffolding for the fact that nothing is on a package index yet.
Worth knowing which parts, so you don't over-invest in learning them.

| Part of this section | After publishing |
|---|---|
| What a workspace is, the shared `.venv`, `uv run` | **Stays** — but becomes reading for contributors only |
| `git clone` + `uv sync --all-packages` | **Stays** — contributors only |
| `make generate-pyspark` | **Gone for consumers.** Published wheels ship the generated expressions already. |
| The `SPARK_HOME` fix | **Stays forever.** It's an environment problem, unrelated to packaging. |
| Empty registry, `exclude-newer` warning | Contributors only |
| The `[tool.uv.sources]` path blocks above | **Deleted entirely.** This is the pure workaround. |
| "Install set = runtime set" | **Stays.** That's entry-point discovery, not packaging. |

The whole of this subsection collapses to one line:

```bash
uv add overture-schema-theme-buildings overture-schema-cli
```

or, for everything:

```bash
uv add overture-schema
```

**On the PySpark step specifically:** the release pipeline already handles it.
`.github/workflows/publish-python-packages.yaml` runs `make generate-pyspark` before
`uv build`, and aborts the release if the resulting wheel contains no
`expressions/generated/*.py`. Its own comment explains why:

> the tree must be generated here before the build, or the published wheel ships without
> its `expressions/generated/` modules and `validate_model()` discovers nothing to run

So consumers of a published wheel never run that step.

**Which index?** The publish workflow currently pushes to AWS CodeArtifact (the
`overture-pypi` domain), even though its step names say PyPI. `CONTRIBUTING.md` describes
version bumps reaching public PyPI while interim builds stay internal. Either way the
consumer instruction is a one-line install — only the index URL differs.

Nothing in sections 2 through 7 changes. The behavior you learn there — entry-point
discovery, the two representations, `by_alias`, `TypeAdapter` for `Segment` — is independent
of how the packages get onto your machine.

---

## 8. Building tools on the models

Sections 1–7 use the schema. This one builds *on* it: generating a client library in
another language, or writing your own command-line tool that stays correct as the
installed packages change. Neither requires touching the schema itself — for that, see
[AUTHORING.md](AUTHORING.md).

### 8.1 Generate an SDK from JSON Schema (any language)

Emit JSON Schema, then hand it to a standard generator. Both of these were run against
the output of `overture-schema json-schema --type building` and produced working code.

**Python (datamodel-code-generator):**

```bash
uv run overture-schema json-schema --type building > building.schema.json

uvx --from datamodel-code-generator datamodel-codegen \
  --input building.schema.json \
  --input-file-type jsonschema \
  --output building_models.py
```

Produces standalone Pydantic v2 models with no Overture dependency — useful for a
service that shouldn't take the whole workspace as a dependency:

```python
# generated by datamodel-codegen:
#   filename:  building.schema.json
from pydantic import BaseModel, ConfigDict, Field, confloat, conint, constr
```

**TypeScript (quicktype):**

```bash
npx -y quicktype --src-lang schema --lang typescript \
  -o Building.ts building.schema.json
```

Field descriptions survive as JSDoc:

```typescript
/**
 * Buildings are man-made structures with roofs that exist permanently in one place.
 * ...
 */
export interface Building {
    bbox?: [number, number, number, number, ...number[]];
    /** The building's footprint or roofprint... */
    geometry: Geometry;
```

quicktype also targets Go, Rust, Java, Kotlin, Swift, C#, and others from the same input.
Anything that reads JSON Schema — OpenAPI toolchains, `go-jsonschema`, `schemars`,
`jsonschema2pojo` — works the same way.

The tradeoff: you get types and structural validation, but not the semantic layer.
Cross-field model constraints (`@require_any_of`, `@radio_group`) do translate into JSON
Schema `if`/`then`/`anyOf` constructs, but domain-specific error messages and the
NewType vocabulary flatten out.

### 8.2 Build a CLI on discovery and tags

If you're staying in Python, don't hardcode a type list. Discover, and let the installed
packages decide what exists — same as the built-in CLI. Your tool then automatically
covers new themes and third-party extensions.

```python
import click
from overture.schema.system.discovery import discover_models, filter_models, TagSelector
from overture.schema.cli.tag_options import tag_selection_options, build_selector


@click.command()
@tag_selection_options  # gives you --tag / --filter / --exclude for free
def report(tags, filters, excludes):
    """Report field counts for the selected feature types."""
    models = filter_models(discover_models(), build_selector(tags, filters, excludes))
    for key, model in sorted(models.items(), key=lambda kv: kv[0].name):
        n = len(model.model_fields) if hasattr(model, "model_fields") else "—"
        click.echo(f"{key.name:20} {n}")
```

`overture.schema.cli` also exports `resolve_types`, `create_union_type_from_models`,
`load_input`, `perform_validation`, `handle_validation_error`, and
`handle_generic_error` — so you can reuse the file-loading and error-rendering behavior
rather than reimplementing it.
