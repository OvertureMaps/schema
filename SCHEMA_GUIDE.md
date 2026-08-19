# Overture Schema Guide

A practical guide to installing, exploring, building on, and authoring the Overture Maps
schema packages.

**Audience:** everyone who touches these packages in Python. The guide is in parts, and
you probably want one of them rather than all of them:

| If you want to | Read |
|---|---|
| Understand why the schema is Pydantic at all | Part 0 |
| Validate data, write code against the models, generate artifacts | Part I |
| Register your own feature types, or author new schema models | Part II |
| Look something up | Part III |
| Look up a term | [Glossary](GLOSSARY.md) |

**Status:** none of these packages are on PyPI yet. Everything below installs from a
local clone with `uv`. Any `pip install overture-schema` you find in a README is
aspirational — it will not work today.

**Verification:** every command and code block in this guide was checked against the
schema repo at commit `2a6170c4` on Python 3.10 — 87 Python blocks parsed, every
`overture.*` import resolved against the installed packages, and every runnable snippet
executed. Blocks that are deliberately wrong (marked ✗) or written as `>>>` transcripts
are excluded, as are template fragments with placeholder names.

---

## Table of contents

**Part 0 — [Why Pydantic](#part-0--why-pydantic)**

**Part I — [Using the schema](#part-i--using-the-schema)**

1. [Install](#1-install)
2. [Exploring the models](#2-exploring-the-models)
3. [Writing code against the models](#3-writing-code-against-the-models)
4. [The three CLIs](#4-the-three-clis)
5. [Validating data](#5-validating-data)
6. [Converting the schema to other formats](#6-converting-the-schema-to-other-formats)
7. [Using the packages from your own project](#7-using-the-packages-from-your-own-project)

**Part II — [Extending and authoring the schema](#part-ii--extending-and-authoring-the-schema)**

8. [Building your own SDK or CLI](#8-building-your-own-sdk-or-cli)
9. [Registering models and tagging](#9-registering-models-and-tagging)
10. [Authoring new schema models](#10-authoring-new-schema-models)
11. [Development workflow](#11-development-workflow)

**Part III — [Reference](#part-iii--reference)**

12. [Gotchas](#12-gotchas)
13. [Templates and quick reference](#13-templates-and-quick-reference)

**[Glossary](GLOSSARY.md)** — data-model and toolchain vocabulary, cross-linked back into this guide.

---

# Part 0 — Why Pydantic

### Why this exists

This project provides type-safe Python models for validating and working with [Overture
Maps Foundation](https://overturemaps.org/) data. Overture Maps is an open geospatial
dataset containing buildings, places, addresses, transportation networks, and
administrative boundaries curated from multiple sources.

Use these schemas to:

- Validate Overture Maps data
- Build data processing pipelines with type safety
- Extend schemas with custom fields and validation rules

### Why Pydantic rather than JSON Schema?

This project addresses a fundamental challenge in data consumption: **bridging the
semantic gap between raw data and human understanding** while enabling
machine-actionable workflows.

### Why Schema at All: Beyond Raw Data

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

### Why Pydantic Over JSON Schema: Solving Multiple Problems

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

### The Result: Faster Understanding, Higher Quality

Instead of spending time deciphering what columns mean and whether data matches
expectations, users can focus on their actual goals: analysis, visualization,
integration. Quality improves because validation happens automatically rather than
through manual inspection.

The fundamental approach - human-readable authoring that generates machine-actionable
outputs - has broader applications beyond Overture and geospatial data. We hope others
will adapt these patterns for linking with Overture data or modeling their own domains
entirely.


---

# Part I — Using the schema

## 1. Install

### 1.1 First, what you're installing

**The schema repo is not one Python package. It's thirteen.**

That's the thing that makes this confusing at the start, so it's worth a minute before
you run anything.

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

Each of those directories has its own `pyproject.toml` and its own version number. They
release independently.

#### What "workspace" means

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

Two things follow from this, and they're the ones that trip people up:

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
be published to PyPI for you to work with it — the packages find each other on disk.

#### What you end up with

One command installs all thirteen into **a single shared virtualenv at the repo root**:

```
schema/
├── .venv/                    ← created by uv; all 13 packages live here
│   └── bin/
│       ├── overture-schema     ← the three CLIs land here
│       ├── overture-codegen
│       └── overture-validate
├── packages/
└── pyproject.toml
```

You don't activate it. `uv run <command>` runs `<command>` inside that venv for you.
That's why every command in this guide starts with `uv run`.

> **Why split into thirteen packages at all?** Because *what you install determines what
> exists at runtime*. The models register themselves through Python entry points, so
> installing only the buildings theme means the CLI only knows about buildings. That's
> the extension mechanism — see [Using the packages from your own project](#7-using-the-packages-from-your-own-project) and
> [Building your own SDK or CLI](#8-building-your-own-sdk-or-cli). If you just want everything, that's fine too.

---

**Layering, bottom up:**

| Layer | Package | Gives you |
|---|---|---|
| Foundation | `system` | `float32`/`uint8`/…, `Geometry`, `BBox`, `CountryCodeAlpha2`, constraint annotations, `Feature` base class, entry-point discovery |
| Overture conventions | `common` | `OvertureFeature` (id/theme/type/version/geometry/sources), `@scoped`, `Names`, `Sources`, cartography hints |
| Feature types | `theme-*` | `Building`, `Place`, `Segment`, `Address`, … plus their enums |
| Tooling | `cli`, `codegen`, `pyspark`, `validation` | commands and functions that consume the above generically |

The tooling layer never hardcodes feature types. It discovers them. That's why your own
models can slot in.

---

### 1.2 Prerequisites

- **Python 3.10 or newer.** You don't need to install this yourself — `uv` will fetch a
  suitable Python if your system one is too old.
- **[`uv`](https://docs.astral.sh/uv/getting-started/installation/).**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

You do **not** need Java, Spark, or Homebrew for anything in sections 1 through 8 of this
guide except the PySpark parts. If you already have a Homebrew Spark installed, skip
ahead to [When something goes wrong](#16-when-something-goes-wrong) — it may actively break things.

---

### 1.2a Two zsh gotchas when pasting commands

macOS defaults to **zsh**, and interactive zsh does *not* treat `#` as a comment unless
you turn that on. Paste a line like this and zsh hands `#`, `→`, and `15` to `wc` as
filenames:

```
find ... | wc -l      # → 15
wc: #: open: No such file or directory
wc: →: open: No such file or directory
wc: 15: open: No such file or directory
       0 total
```

A line that *starts* with `#` fails more obviously — `command not found: #`.

This guide keeps `#` comments only as standalone label lines inside multi-command blocks,
never trailing after a command. To paste those blocks whole, enable comments once:

```bash
setopt interactive_comments
```

Add it to `~/.zshrc` to make it permanent. Otherwise, skip the `#` lines when copying —
they are labels, not commands. Scripts and non-interactive shells are unaffected; this is
purely an interactive-zsh behavior.

#### 2. `!` runs a command out of your history

This one is worth understanding because it can do real damage. In an interactive shell,
`!` triggers **history expansion**, and it fires *inside double quotes*. `!r` means "the
most recent command starting with `r`" — the shell splices that command's text into your
line before running it.

So a Python one-liner containing `{value!r}`, pasted into zsh as

```
uv run python -c "... f'default={f.default!r}' ..."
```

becomes something else entirely. What you get depends on your own shell history:

```
SyntaxError: f-string: invalid syntax
    (f.defaultrm -rf schema)
```

That is a past command of yours, pasted into the middle of a Python f-string. Here it only
produced a syntax error — Python never ran and nothing was deleted. But the same mechanism
can land text somewhere the shell *will* execute.

**The fix used throughout this guide:** multi-line Python is passed via a heredoc with a
**quoted** delimiter, not `-c "..."`.

```bash
uv run python <<'PY'
from overture.schema.buildings import Building
print(f"{Building.__name__!r} is safe here")
PY
```

Quoting the delimiter (`<<'""" + D + """'` rather than `<<""" + D + """`) disables every
form of expansion in the body — history, variables, command substitution. The text reaches
Python exactly as written.

Verified rather than assumed:

```
double-quoted -c   ->  !r expanded into a command from history
quoted heredoc     ->  !r left alone
```

Single quotes also block history expansion, but the Python in this guide uses single
quotes internally, so heredocs are the practical choice. If you hit this in your own
one-liners, `{value!r}` can always be written `{repr(value)}` instead — no `!` at all.

---

### 1.3 Install

```bash
git clone https://github.com/OvertureMaps/schema.git
cd schema
uv sync --all-packages
```

That's it. `uv sync --all-packages` reads the lockfile, creates `.venv/`, and installs
all thirteen workspace members into it.

**This is the whole install for most people.** You can now validate data, explore models,
generate JSON Schema, and generate documentation.

**What about `make install`?** It works too, and nothing about it is risky. It's exactly
`uv sync --all-packages --all-extras` plus the PySpark generation step described in
[Do you need PySpark?](#15-do-you-need-pyspark) — so it just does more than most people
need. (No package in the workspace defines extras today, so `--all-extras` changes
nothing.) Use it if you'd rather run one command and have everything.

---

### 1.4 Check it worked

Run these three. All should succeed:

```bash
uv run overture-schema --version
```
```
overture-schema, version 1.17.1
```

> **Seeing a warning banner above that line?** Something like
> `warning: Failed to parse pyproject.toml ... exclude-newer = "1 week"`. The command
> still worked — but your `uv` is too old for this repo, and it is quietly rewriting
> `uv.lock` behind your back. Stop and fix it before going further:
> [uv warns about `exclude-newer`](#uv-warns-about-exclude-newer--and-quietly-rewrites-your-lockfile).
> Every output shown in this guide assumes a correctly configured `uv` and omits that
> banner.

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

If all three worked, you're installed. **Skip to section 2** unless you need PySpark.

#### What did that third command actually validate?

Fair question — it's the first command that does real work, and the filename explains
nothing.

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

#### "Envelope" — the word this guide keeps using

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

```bash
uv run python <<'PY'
import json, yaml
from overture.schema.buildings import Building

b = Building.model_validate_json(
    json.dumps(yaml.safe_load(open("examples/buildings/building-polygon.yaml"))))
gj = b.model_dump(mode="json", by_alias=True, exclude_none=True)

print("envelope keys:", sorted(gj))
print("payload keys :", sorted(gj["properties"]))
PY
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

#### Three keys named `type`

A **key** is a field name — the part left of the colon. This file uses the key `type`
three times, at three nesting levels, meaning three unrelated things:

| Where | Value | Comes from | Means |
|---|---|---|---|
| top level | `Feature` | GeoJSON spec | "this object is a GeoJSON Feature" |
| inside `geometry` | `Polygon` | GeoJSON spec | "this shape is a polygon" |
| inside `properties` | `building` | Overture | "this feature is a building" |

List them yourself:

```bash
uv run python -c "
import yaml
d = yaml.safe_load(open('examples/buildings/building-polygon.yaml'))
print('type            =', d['type'])
print('geometry.type   =', d['geometry']['type'])
print('properties.type =', d['properties']['type'])"
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

#### Why is it YAML? Is Overture data YAML?

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

#### See it actually catch something

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

### 1.5 Do you need PySpark?

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
`make generate-pyspark`.

#### What a successful run looks like

**Nothing.** No progress, no file list, no "done" message — the command returns you
straight to your prompt:

```
$ make generate-pyspark
$
```

That is success. It looks identical to nothing having happened, which is why the next
subsection exists.

#### What the command actually does

`make generate-pyspark` isn't a program — it's a *target* in the repo's `Makefile`, a
named recipe of shell commands. Here it is in full:

```make
generate-pyspark: uv-sync clean-pyspark
	@uv run overture-codegen generate --format pyspark \
		--output-dir $(PYSPARK_EXPRESSIONS) \
		--test-output-dir $(PYSPARK_GENERATED_TESTS)
	@uv run ruff check --fix --quiet $(PYSPARK_EXPRESSIONS) $(PYSPARK_GENERATED_TESTS)
	@uv run ruff format --quiet $(PYSPARK_EXPRESSIONS) $(PYSPARK_GENERATED_TESTS)
```

Reading that:

- **`generate-pyspark:`** is the target name — what you typed after `make`.
- **`uv-sync clean-pyspark`** on the same line are *prerequisites*: other targets that
  must run first, in that order.
- The tab-indented lines below are the *recipe* — the shell commands, run in order.
- The leading **`@`** tells make not to echo the command before running it. Without it,
  make prints each command as it goes. This is why you see no output.
- **`$(PYSPARK_EXPRESSIONS)`** and **`$(PYSPARK_GENERATED_TESTS)`** are variables defined
  higher up in the `Makefile`; they expand to the two output directories.

So typing one command runs five steps:

| # | Step | What it does | Visible? |
|---|---|---|---|
| 1 | `uv-sync` | `uv sync --all-packages --all-extras` — makes sure dependencies are installed | No: the target captures its output and prints it only on failure |
| 2 | `clean-pyspark` | `rm -rf` both output directories, so generation starts from empty | No: nothing to say |
| 3 | `overture-codegen generate --format pyspark` | **The actual work.** Reads the Pydantic models and writes ~23,000 lines of Python: 15 expression modules and 17 test modules | No: prints nothing on success |
| 4 | `ruff check --fix` | Lints the generated code and auto-fixes what it can, e.g. unused imports | No: `--quiet` |
| 5 | `ruff format` | Reformats the generated code to the project's style | No: `--quiet` |

Steps 4 and 5 exist because generated code is still code that has to pass the repo's own
lint and format checks — `make check` runs `ruff` over everything, generated files
included.

Every step is silent by design, which is why a successful run prints nothing at all.

> **On an out-of-date `uv`** you'll instead see the `exclude-newer` banner three times —
> once each for steps 3, 4, and 5, the three visible `uv run` calls — and nothing else. That is still a successful run, but fix
> the `uv` problem before continuing:
> [uv warns about `exclude-newer`](#uv-warns-about-exclude-newer--and-quietly-rewrites-your-lockfile).

#### Confirm it worked

Don't infer it from the output — check the result:

```bash
uv run python -c "from overture.schema.pyspark import model_names; print(model_names())"
```

Before — an empty list, no error, which is why this is easy to miss:

```
[]
```

After — 30 entries, which is 15 feature types each reachable by two names:

```
['address', 'bathymetry', 'building', 'building_part', 'connector', 'division', ...]
```

Or count the files directly:

```bash
find packages/overture-schema-pyspark/src/overture/schema/pyspark/expressions/generated -name '*.py' | wc -l
find packages/overture-schema-pyspark/tests/generated -name '*.py' | wc -l
```

```
      15
      17
```

#### Why two names per model?

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
[register their own feature types](#83-register-your-own-feature-types), and nothing
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

#### Why is generated code in `.gitignore`?

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

#### "Gitignored" does not mean "not shipped"

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

### 1.6 When something goes wrong

**This section is a reference, not a checklist.** Nothing here is setup you need to
perform. Each entry starts with a symptom — read the one matching an error you actually
saw, and skip the rest. If section 1.4 gave you clean output and
[Confirm it worked](#confirm-it-worked) checked out, you can skip the whole section and
go on to section 2.

#### `FileNotFoundError: ... /apache-spark/3.5.3/libexec/./bin/spark-submit`

```
FileNotFoundError: [Errno 2] No such file or directory:
'/opt/homebrew/Cellar/apache-spark/3.5.3/libexec/./bin/spark-submit'
```

**This has nothing to do with the generation step in "Do you need PySpark?".** It's a stale `SPARK_HOME`
environment variable, and it will happen whether or not you ran `make generate-pyspark`.

What's going on: you have a `SPARK_HOME` exported in your shell profile pointing at a
**version-specific Homebrew path**. Homebrew has since upgraded Spark, so that exact
directory no longer exists:

```bash
echo $SPARK_HOME
ls /opt/homebrew/Cellar/apache-spark/
```

```
/opt/homebrew/Cellar/apache-spark/3.5.3/libexec
4.0.0
```

The variable names `3.5.3`; the only version present is `4.0.0`. It points at nothing.

Meanwhile the `pyspark` in your venv (4.2.0) **ships its own copy of Spark** and doesn't
need the Homebrew one at all. But when `SPARK_HOME` is set, PySpark obeys it and looks
for `spark-submit` at that dead path.

**Confirm that's your problem:**

```bash
env -u SPARK_HOME uv run python -c "
from pyspark.sql import SparkSession
s = SparkSession.builder.master('local[1]').getOrCreate()
print('SUCCESS — spark', s.version)
s.stop()"
```

```
SUCCESS — spark 4.2.0
```

**Fix it permanently.** The variable is set in *two* files — fixing only one won't help,
because `.zprofile` runs for login shells and `.zshrc` for interactive ones:

```
~/.zshrc:8      export SPARK_HOME=/opt/homebrew/Cellar/apache-spark/3.5.3/libexec
~/.zshrc:9      export PATH="$SPARK_HOME/bin/:$PATH"
~/.zprofile:5   export SPARK_HOME=/opt/homebrew/Cellar/apache-spark/3.5.3/libexec
~/.zprofile:6   export PATH="$SPARK_HOME/bin/:$PATH"
```

Pick one:

- **Simplest — delete all four lines.** If you only use Spark through Python projects
  like this one, you don't need `SPARK_HOME` at all; each venv's `pyspark` brings its
  own.
- **Keep Homebrew Spark for other work — stop hardcoding the version.** Replace the two
  `SPARK_HOME` lines with the version-independent symlink Homebrew maintains:

  ```bash
  export SPARK_HOME=/opt/homebrew/opt/apache-spark/libexec
  ```

  This survives upgrades. But note it points at Spark **4.0.0** while this project's
  `pyspark` is **4.2.0** — mismatched versions cause their own confusing failures, so
  prefer the first option while working in this repo.

Then open a new terminal, or `exec zsh`, and re-run the check above.

> **Per-shell workaround** if you don't want to touch your profile right now:
> `unset SPARK_HOME` in the terminal you're working in. It lasts until you close it.

#### `model_names()` returns `[]`, or `KeyError` on a feature type

You skipped [Do you need PySpark?](#15-do-you-need-pyspark). Run `make generate-pyspark`.

#### `ModuleNotFoundError: No module named 'overture'`

You started Python without `uv run`, so you're in your system or `pyenv` interpreter
rather than the project's `.venv`. Use `uv run python` instead of `python`. See
[Running Python against the models](#21-running-python-against-the-models).

#### `command not found: overture-schema`

You're missing the `uv run` prefix, or you're not in the repo root. Every command in this
guide is `uv run overture-schema …`, run from the directory containing `pyproject.toml`.

#### uv warns about `exclude-newer` — and quietly rewrites your lockfile

```
warning: Failed to parse `pyproject.toml` during settings discovery:
  TOML parse error at line 10, column 17
     |
  10 | exclude-newer = "1 week"
     |                 ^^^^^^^^
  failed to parse year in date "1 week": failed to parse "1 we" as year ...
```

> **Do you actually have this problem?** Only if that banner appears when you run a
> command. If your commands print their output cleanly, skip this entire subsection —
> there is nothing to fix, and the four steps below are not maintenance you need to
> perform. Confirm in one line:
>
> ```bash
> uv run overture-schema --version
> ```
>
> A single line of output means you're fine. A wall of warning text above it means read on.

**If you do see it: this is not cosmetic. Fix it before you do anything else.**

The root `pyproject.toml` writes `exclude-newer` as a relative duration (`"1 week"`),
which caps how new a package `uv` will consider during dependency resolution. Only
reasonably recent `uv` versions parse that form.

An older `uv` fails to read the whole `[tool.uv]` block, says so, **and carries on
without the cap** — then, because its resolution no longer matches the committed
lockfile, rewrites `uv.lock` in place. You end up with a modified tracked file you never
asked to change:

```bash
git status --short uv.lock
git diff --stat uv.lock
```

On an affected machine:

```
 M uv.lock
 uv.lock | 807 +++++++++++++++++++-------------------
 1 file changed, 464 insertions(+), 343 deletions(-)
```

> **Both commands printing nothing is the healthy result.** `git status --short` and
> `git diff --stat` say nothing about a file that hasn't changed. Empty output here means
> your lockfile is untouched and there is nothing to fix. If you'd rather have an explicit
> answer than read silence:
>
> ```bash
> git diff --quiet uv.lock && echo "uv.lock: unmodified" || echo "uv.lock: MODIFIED"
> ```

It drops the `[options]` block that records the resolution settings, and pulls in
dependency versions past the cutoff the repo intended. Nothing breaks immediately — the
install works fine — but you're now building against a different dependency set than the
project pinned, and `git status` is dirty.

**Step 1 — check your version:**

```bash
uv --version
brew outdated uv
```

**Step 2 — upgrade:**

```bash
brew upgrade uv
```

**Step 3 — restore the lockfile if the old `uv` already rewrote it:**

```bash
git checkout uv.lock
```

**Step 4 — confirm:**

```bash
uv sync --all-packages --locked
```

```
Resolved 64 packages in 12ms
Audited 60 packages in 0.81ms
```

`--locked` fails outright if the lockfile isn't authoritative, so a clean pass means your
`uv`, the lockfile, and your `.venv` all agree. Run `git status --short uv.lock` once more
too — it should print nothing, which means the file is unmodified.

> **If you see `error: The lockfile at uv.lock needs to be updated, but --locked was
> provided`,** you're at step 3, not step 4. A previous `uv sync` under the old `uv`
> already modified the lock. `git checkout uv.lock` and re-run.

Once you're on a current `uv`, ordinary use leaves the lockfile alone — including the
`uv sync --all-packages --all-extras` that `make install`, `make check`, and
`make generate-pyspark` all run internally.

---

## 2. Exploring the models

You can't write code against a model you haven't looked at. This section is about finding
out what feature types exist, what fields they carry, and what values those fields
accept — before writing a line of code against them.

**Two things can answer your questions, and it's worth keeping them straight:**

| | What it is | Ask it with |
|---|---|---|
| **The model** | The Pydantic classes themselves — the source of truth, and what actually validates your data | Python: `Building.model_fields` |
| **The generated JSON Schema** | An artifact *rendered from* the model, in the GeoJSON shape | `overture-schema json-schema` + `jq` |

They agree, because one is generated from the other. The model is flatter and easier to
interrogate; the JSON Schema is the published contract and the thing other tools consume.
This section asks the model first, then the schema.

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

Press Ctrl-D to exit.

**A script file**, once you're writing more than a couple of lines:

```bash
uv run python explore.py
```

Unless a snippet is explicitly marked as shell, every Python block from here on is code
to run one of these three ways. An interactive session is the best fit for section 2 —
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

Filter with the tag options, which are shared by `list-types`, `validate`, and
`json-schema`:

| Option | Semantics |
|---|---|
| `--tag T` | OR — defines scope. Repeatable. |
| `--filter T` | AND — every listed tag must be present. Repeatable. |
| `--exclude T` | OR-NOT — any match drops the type. Repeatable. |

Tag format is `[namespace:]predicate[=value]`:

- plain — `feature`
- namespaced — `system:extension`
- key/value — `overture:theme=buildings`

```bash
uv run overture-schema list-types --tag overture:theme=buildings --tag overture:theme=places
```

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
sit alongside the rest, with **no nesting and no envelope**. A model is flat. (If you've
seen Overture data as GeoJSON with things tucked under `properties`, that's a
serialization format, not the model — [2.5](#25-ask-the-generated-json-schema-cli--jq)
covers why they differ.)

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
See [Gotchas](#12-gotchas).

This is the same information [2.5](#25-ask-the-generated-json-schema-cli--jq) reads out
of the JSON Schema, minus the envelope — `f.description` is the `description` keyword,
`f.metadata` of `[Gt(gt=0)]` is `exclusiveMinimum: 0`, and `f.is_required()` is
membership in a `required` array.

### 2.5 Ask the generated JSON Schema (CLI + jq)

Dump the JSON Schema for one type. Save it once rather than re-running the command for
every question:

```bash
uv run overture-schema json-schema --type building > building.schema.json
```

#### Two kinds of key

Before walking the nesting, one distinction that makes the rest obvious. Everything in a
JSON Schema document is a JSON object, so `jq keys` will happily list any level — but
what it lists alternates between two completely different kinds of name.

**Schema keywords** are vocabulary defined by the JSON Schema specification. They are
instructions to a validator, and the set is fixed — you could not invent a new one. Their
values describe the document:

```bash
jq 'keys' building.schema.json
```
```json
["$defs","additionalProperties","description","properties","required","title","type"]
```

```
.type                 = "object"
.title                = "building"
.description          = "Buildings are man-made structures with roofs..."
.required             = ["type","id","geometry","properties"]
.additionalProperties = false
```

Read that as prose: *this is an object, called `building`, described like so, these four
fields are mandatory, and no others are allowed.*

**Field names** are names that appear in actual data. They are not vocabulary — they come
from Overture and GeoJSON, and every one of them maps to a *subschema*: another little
JSON Schema object describing that one field.

```bash
jq '.properties | keys' building.schema.json
```
```json
["bbox","geometry","id","properties","type"]
```

```
.properties.type     = {"const":"Feature","type":"string"}
.properties.id       = {"description":"A feature ID...", ...}
.properties.geometry = {"description":"The building's footprint...", ...}
```

Those values aren't descriptions of the document — they're rules for one field each.
`.properties.type` says: *the data field named `type` must be the string `Feature`.*

So "keys" is technically accurate for both lists and useless for telling them apart. The
first list is **keywords**; the second is **field names**. The keyword `properties` is the
gate between them: everything under it is data field names, and each of those opens into
a subschema made of keywords again.

You can see both roles inside a single value:

```json
{"const": "Feature", "type": "string"}
```

The key `type` that got you here was a *field name*. The `type` inside the value is a
*keyword* meaning "JSON string." Same word, opposite roles, one level apart.

#### Mind the nesting

With that distinction, the path to the Overture fields reads cleanly. `.properties` is a
keyword, so its contents are field names — and they're GeoJSON's, the same envelope from
[Three keys named `type`](#three-keys-named-type):

```bash
jq '.properties | keys' building.schema.json
```
```json
["bbox","geometry","id","properties","type"]
```

One of those field names is itself `properties` — the GeoJSON member holding the Overture
fields. Descend into it, then through *its* `properties` keyword:

```bash
jq '.properties.properties.properties | keys' building.schema.json
```
```json
["class","facade_color","facade_material","has_parts","height","is_underground",
 "level","min_floor","min_height","names","num_floors","num_floors_underground",
 "roof_color","roof_direction","roof_height","roof_material","roof_orientation",
 "roof_shape","sources","subtype","theme","type","version"]
```

Three `properties` in a row, alternating role each time:

| Path segment | Kind | Meaning |
|---|---|---|
| `.properties` | keyword | "the fields of the GeoJSON object" |
| `.properties.properties` | field name | the GeoJSON field *named* `properties` |
| `.properties.properties.properties` | keyword | "the fields inside that one" |

Note `id`, `geometry`, and `bbox` are absent from the final list. They live on the
envelope, at `.properties.id` and so on — exactly as they do in the data.

#### That JSON object is not the field's value

A reasonable reading of this is "height is an object":

```json
{
  "description": "Height of the building or part in meters.\n\nThis is the distance from the lowest point to the highest point.",
  "exclusiveMinimum": 0,
  "title": "Height",
  "type": "number"
}
```

It isn't. **In the data, `height` is a plain number.** What you're looking at is the
*subschema* — the rules for `height`, not a value of `height`. And `"type": "number"` is
the keyword saying so.

The actual data looks like this:

```json
{"height": 21.34}
```

Every field's subschema is a JSON object, no matter how simple the field is, because
that's the only place to hang a description and a constraint. You can't attach
"must be greater than zero" to a bare `"number"`.

Each keyword traces back to one thing in the Python model —
`packages/overture-schema-theme-buildings/src/overture/schema/buildings/_common.py`:

```python
height: Annotated[
    float64 | None,
    Field(
        gt=0,
        description=textwrap.dedent("""
            Height of the building or part in meters.

            This is the distance from the lowest point to the highest point.
        """).strip(),
    ),
] = None
```

| Schema keyword | Comes from |
|---|---|
| `"type": "number"` | the `float64` annotation |
| `"exclusiveMinimum": 0` | `gt=0` — greater than, not greater-or-equal |
| `"description"` | the `description=` argument |
| `"title": "Height"` | generated by Pydantic from the field name |
| *absent from `required`* | the `= None` default |

Nobody hand-wrote that JSON. It's a rendering of the Python declaration, which is why the
JSON Schema, the validation errors, the PySpark checks, and the generated documentation
can't drift from each other — [section 6](#6-converting-the-schema-to-other-formats) is
all the other renderings of the same source.

#### Why a wrong path gives you `null`, not an error

Ask `jq` for a key that isn't there and it returns `null`. That is an answer, not a
failure — `null` means "no such key at this path":

```bash
jq '.properties.height' building.schema.json
jq '.properties.banana' building.schema.json
```
```
null
null
```

`height` isn't missing from the schema; it just isn't on the *envelope*, which only has
`bbox`, `geometry`, `id`, `properties`, and `type`. A `null` here almost always means you
stopped one level too high.

Two ways to make that louder. `jq -e` sets the exit status — `1` for `null`, `0` for a
real result, useful in scripts:

```bash
jq -e '.properties.height' building.schema.json > /dev/null; echo $?
jq -e '.properties.properties.properties.height' building.schema.json > /dev/null; echo $?
```
```
1
0
```

Or stop guessing at the nesting and let `jq` find the field for you:

```bash
jq -c 'paths | select(.[-1]=="height")' building.schema.json
```
```json
["properties","properties","properties","height"]
```

That prints the exact path to any field, which you can then read directly. Handy whenever
a lookup comes back `null` and you're not sure how deep the thing actually lives.

#### Asking useful questions

Which fields are mandatory — and here the envelope bites. There is no single `required`
list. There are **two**, one per level:

```bash
jq '.required' building.schema.json
jq '.properties.properties.required' building.schema.json
```
```json
["type","id","geometry","properties"]
["theme","type","version"]
```

Read them together:

| Required | Where | What it is |
|---|---|---|
| `type` | envelope | GeoJSON's own `"type": "Feature"` |
| `id` | envelope | the feature's ID |
| `geometry` | envelope | the shape |
| `properties` | envelope | the container itself must be present |
| `theme` | in `properties` | `buildings` |
| `type` | in `properties` | `building` |
| `version` | in `properties` | the feature version |

So **`id` and `geometry` are absolutely required** — they're just not in the array you'd
find by looking only under `properties`, because in GeoJSON they don't live under
`properties`. Asking `.properties.properties.required` and reading it as "the required
fields of a building" undercounts by exactly the fields the envelope owns.

Prove it by deleting them:

```bash
uv run python <<'PY'
import json, yaml
from overture.schema.buildings import Building

for drop in ["geometry", "id"]:
    d = yaml.safe_load(open("examples/buildings/building-polygon.yaml"))
    del d[drop]
    try:
        Building.model_validate_json(json.dumps(d))
        print(f"dropping {drop}: ACCEPTED")
    except Exception as e:
        print(f"dropping {drop}:", str(e).splitlines()[2].strip()[:30])
PY
```
```
dropping geometry: Field required
dropping id: Field required
```

**The model is the easier place to ask this question**, because it has no envelope — one
flat answer, all five:

```bash
uv run python -c "
from overture.schema.buildings import Building
print(sorted(n for n, f in Building.model_fields.items() if f.is_required()))"
```
```
['geometry', 'id', 'theme', 'type', 'version']
```

There are other `required` arrays deeper in the schema too — every nested structure has
its own. `Names`, `SourceItem`, and the two `geometry` variants each carry one:

```bash
jq -c 'paths | select(.[-1]=="required")' building.schema.json
```
```json
["$defs","NameRule","required"]
["$defs","Names","required"]
["$defs","Perspectives","required"]
["$defs","SourceItem","required"]
["properties","geometry","oneOf",0,"required"]
["properties","geometry","oneOf",1,"required"]
["properties","properties","not","required"]
["properties","properties","required"]
["required"]
```

`required` is always relative to the object it sits in — never a global list for the
feature.

#### Who decides what's required?

Nobody maintains that list. **It's derived** — in Pydantic, a field with no default is
required, and a field with a default is optional:

```bash
uv run python <<'PY'
from overture.schema.buildings import Building
from pydantic_core import PydanticUndefined

for n in ["version", "theme", "height", "num_floors"]:
    f = Building.model_fields[n]
    d = "no default" if f.default is PydanticUndefined else f"default={f.default!r}"
    print(f"{n:12} {d:16} -> {'REQUIRED' if f.is_required() else 'optional'}")
PY
```
```
version      no default       -> REQUIRED
theme        no default       -> REQUIRED
height       default=None     -> optional
num_floors   default=None     -> optional
```

So "who decided" is answered by finding where the field is declared. For a building, five
fields are required, and four of them come from the shared base class rather than from
buildings at all:

```bash
uv run python <<'PY'
from overture.schema.buildings import Building

for n, f in Building.model_fields.items():
    if not f.is_required():
        continue
    for cls in Building.__mro__:
        if n in getattr(cls, "__annotations__", {}):
            print(f"{n:10} -> {cls.__name__}")
            break
PY
```
```
id         -> OvertureFeature
geometry   -> Building
theme      -> OvertureFeature
type       -> OvertureFeature
version    -> OvertureFeature
```

`id`, `theme`, `type`, and `version` are required of *every* Overture feature — they're
declared once in `OvertureFeature`
(`packages/overture-schema-common/src/overture/schema/common/feature.py`):

```python
id: Id = Field(description="A feature ID. ...")
theme: ThemeT
type: TypeT
# Superclass `Feature` provides `geometry` and `bbox`.
version: FeatureVersion
```

No `= None`, so all four are mandatory. `Building` adds only `geometry`, narrowing the
inherited one to the polygon types a building may have.

The two `required` arrays in the JSON Schema split those five across the GeoJSON envelope
— `id` and `geometry` sit at `.required`, while `theme`, `type`, and `version` sit at
`.properties.properties.required`, since that's where they live in the data.

**As for the human answer:** the Overture Schema Working Group decides, and changes go
through the process in `CONTRIBUTING.md` — a PR plus a changelog fragment. Making a field
required is a breaking change, so it targets the `vnext` branch and waits for a major
release; making one optional is not, and can go to `main`.

One field's type, constraints, and documentation:

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

By **contract** I mean the set of rules a validator will enforce — what a producer must
satisfy and what a consumer may therefore rely on. For `height` that's: it must be a
number, and it must be strictly greater than zero.

But "the contract for `height`" is narrower than "everything true about `height`", in three
ways worth knowing before you rely on it.

**Optionality isn't in there.** Whether `height` may be omitted is recorded in a sibling
`required` array, not in the field's own subschema. A subschema describes the value *if
present*.

**Units are documentation, not a rule.** "in meters" appears in `description` — prose for
humans. Nothing rejects a value recorded in feet. The machine-checkable part is only
`type: number` and `exclusiveMinimum: 0`.

**Relationships between fields are mostly absent.** The schema *can* express cross-field
rules, and elsewhere it does — `@require_any_of`, `@forbid_if` and friends from
the `@require_any_of` / `@forbid_if` decorators in `overture-schema-system`. But no such rule ties `height` to
`min_height`, so this passes:

```bash
uv run python <<'PY'
import json, yaml
from overture.schema.buildings import Building

d = yaml.safe_load(open("examples/buildings/building-polygon.yaml"))
d["properties"]["height"] = 5
d["properties"]["min_height"] = 100      # a floor above the roof
print("accepted:", Building.model_validate_json(json.dumps(d)).height)
PY
```

```
accepted: 5.0
```

A building whose lowest point is 100m and whose highest is 5m is physically impossible and
schema-valid. Both fields satisfy their own contracts; nothing checks them against each
other.

So: a subschema is the complete machine-checkable contract for **one field in isolation**.
It is not a guarantee that the data makes sense. Same lesson as the stray comma in
[See it actually catch something](#see-it-actually-catch-something) — validation enforces
the schema, not correctness.

Enums and shared structures live at the top level under `$defs`, not nested:

```bash
jq -r '.["$defs"] | keys[]' building.schema.json
```
```
BuildingClass BuildingSubtype FacadeMaterial NameRule NameVariant Names
PerspectiveMode Perspectives RoofMaterial RoofOrientation RoofShape Side SourceItem
```

So the full list of valid values for a field, without reading Python source:

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

> **If the nesting is annoying, skip to Python.** `Building.model_fields` in
> [2.4](#24-ask-the-model-itself-python) gives you the same field list flat, with no
> envelope to walk through. The JSON Schema route is most useful when you want the exact
> published contract — or when you're feeding it to another tool, as in
> [section 8](#8-building-your-own-sdk-or-cli).

#### Wait — why is there a GeoJSON envelope at all?

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
[section 6](#6-converting-the-schema-to-other-formats) generates as a Spark `StructType`.

The honest summary is that there are two serializations and neither is subordinate:

| Serialization | Shape | Pydantic mode | Where you meet it |
|---|---|---|---|
| **Parquet** | flat / columnar | `python` | the release bucket, Spark, DuckDB — all bulk data |
| **GeoJSON** | nested envelope | `json` | single features, extracts, examples in this repo, web tooling |

The model supports both deliberately. The JSON Schema you're reading in this subsection
describes the second one, which is the only reason an envelope shows up here at all.

#### "Interchange format" — what that actually means

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

```bash
uv run python <<'PY'
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
PY
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

#### Is Pydantic wrapped around GeoJSON?

Short answer: **no.** But the question has three reasonable readings, and one of them is a
qualified yes, so it's worth taking them separately.

**"Is the model built on top of a GeoJSON structure?"** No. A model is a flat list of
fields, declared one at a time in Python. You can build one and use it without JSON ever
entering the picture:

```bash
uv run python <<'PY'
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
PY
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

```bash
uv run python <<'PY'
from overture.schema.buildings import Building
print("id in model_fields       :", "id" in Building.model_fields)
print("geometry in model_fields :", "geometry" in Building.model_fields)
print("a 'properties' field?    :", "properties" in Building.model_fields)
PY
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

```bash
uv run python <<'PY'
import json, yaml
from overture.schema.buildings import Building

b = Building.model_validate_json(
    json.dumps(yaml.safe_load(open("examples/buildings/building-polygon.yaml"))))

print("python mode:", sorted(b.model_dump(mode="python", by_alias=True, exclude_none=True))[:8])
print("json mode  :", sorted(b.model_dump(mode="json",   by_alias=True, exclude_none=True)))
PY
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
in [section 3](#3-writing-code-against-the-models) — where using the wrong mode for your
data shape is the most common way to get a confusing `ValidationError`.

#### Why `jq` for this

`jq` isn't required — you could parse the schema in Python. It suits *poking around*
specifically, for four reasons:

**Paths mirror the structure.** JSON is a tree and `jq` is a query language for trees, so
`.properties.properties.properties.height` reads exactly like the nesting it walks. You
compose a path left to right instead of writing traversal code.

**It answers "what is this?", not just "give me X".** Most JSON tools retrieve a value you
already know the name of. `jq` has structure-discovery built in:

```bash
jq 'keys' building.schema.json
jq -c 'paths | select(.[-1]=="height")' building.schema.json
```
```json
["$defs","additionalProperties","description","properties","required","title","type"]
["properties","properties","properties","height"]
```

That second one finds a field wherever it lives — you don't have to know the shape first.
That is the difference between a query tool and an exploration tool.

**It's a filter, so it composes.** Data in, data out — pipe it, redirect it, chain it with
`head`, feed one query's output to another. And because the output is JSON, `jq` composes
with itself.

**Zero setup.** No file to create, no imports, no session to keep alive. One line in the
shell you're already in.

It also reshapes, which is useful for scanning a lot at once — every field with its type,
as a table:

```bash
jq -r '.properties.properties.properties
       | to_entries[]
       | "\(.key)\t\(.value.type // .value["$ref"] // "?")"' building.schema.json
```
```
class            #/$defs/BuildingClass
facade_color     string
facade_material  #/$defs/FacadeMaterial
has_parts        boolean
height           number
is_underground   boolean
```

**Where it's the wrong tool.** `jq` is a whole separate language, its error messages are
terse, and — as the `null` above shows — it answers a wrong path with a shrug rather than
a complaint. For *this* schema, Python introspection is usually easier: the field list
comes out flat, with no GeoJSON envelope to walk. Use `jq` when you want the published
contract exactly as it ships, or when you're piping it into another tool. Use Python when
you want to understand the model. That's the next subsection.

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

---

## 3. Writing code against the models

Section 2 was about finding out what exists. This section is about using it: loading
real data into models, reading and changing it, and writing it back out.

### 3.1 A complete example, start to finish

Before any of the details, here is the whole job in one piece: load a feature, read it,
change it, write it back out, and confirm it still validates. Everything else in this
section is an explanation of a line in this snippet.

```bash
uv run python <<'PY'
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
PY
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

---

## 4. The three CLIs

Installing the workspace gives you three commands, from three different packages.

| Command | Package | Purpose |
|---|---|---|
| `overture-schema` | `overture-schema-cli` | Validate files, emit JSON Schema, list types |
| `overture-codegen` | `overture-schema-codegen` | Generate markdown docs and PySpark expressions |
| `overture-validate` | `overture-schema-pyspark` | Validate Parquet/S3 data at scale with Spark |

Prefix each with `uv run` inside the repo, or activate the venv.

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

```
Usage: overture-codegen [OPTIONS] COMMAND [ARGS]...

Commands:
  generate  Generate code/docs from discovered models.
  list      List all discovered models.
```

```
Usage: overture-codegen generate [OPTIONS]

  --format [markdown|pyspark]  Output format  [required]
  --tag / --filter / --exclude TEXT
  --output-dir PATH            Default: stdout
  --test-output-dir PATH       Write generated conformance tests (pyspark only)
```

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

```
Usage: overture-validate [OPTIONS] FEATURE_TYPE PATH

  -o, --output TEXT            Output path for validated Parquet.
  --head INTEGER               Error rows to display.  [default: 20]
  --conf TEXT                  Spark config key=value pairs.
  --count-only                 Report error count only.
  --skip-schema-check          Warn on schema mismatches instead of aborting.
  --skip-columns TEXT          Columns declared absent from data.
  --ignore-extra-columns TEXT  Extra data columns to ignore in schema comparison.
  --suppress TEXT              Suppress checks: FIELD or FIELD:CHECK.
```

```bash
overture-validate building local.parquet
overture-validate segment s3a://overturemaps-us-west-2/release/2026-07-22.0
overture-validate place data.parquet --count-only
overture-validate segment data.parquet --suppress version:bounds -o violations.parquet
```

It handles S3A and anonymous credentials for the public Overture bucket automatically,
and expands a release root into the Hive partition path for you. Full option and
path-resolution reference: `packages/overture-schema-pyspark/README.md`.

---

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
right thing to log or turn into a report.

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

---

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
[Register your own feature types](#83-register-your-own-feature-types).

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

Nothing in sections 2 through 9 changes. The behavior you learn there — entry-point
discovery, the two representations, `by_alias`, `TypeAdapter` for `Segment` — is independent
of how the packages get onto your machine.

---

---

# Part II — Extending and authoring the schema

## 8. Building your own SDK or CLI

Four approaches, cheapest first.

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

### 8.3 Register your own feature types

Your models become first-class: discovered by the CLI, accepted by `validate()`,
included in generated docs and JSON Schema. Nothing in the tooling special-cases
Overture.

```python
# mypkg/models.py
from typing import Literal
from overture.schema.common import OvertureFeature
from overture.schema.system.numeric import float32


class Vineyard(OvertureFeature[Literal["agriculture"], Literal["vineyard"]]):
    """A cultivated area planted with grapevines."""

    area_hectares: float32 | None = None
```

```toml
# mypkg/pyproject.toml
[project.entry-points."overture.models"]
vineyard = "mypkg.models:Vineyard"
```

Install it, and:

```bash
overture-schema list-types
overture-schema validate vineyard.json
overture-codegen generate --format markdown --output-dir out
```

To attach your own tags, register a **tag provider** on `overture.tag_providers`:

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

Tag namespaces are reserved: `feature` and `system:` belong to `overture-schema-system`,
`overture:` to `overture-schema-common`. A provider that tries to set a reserved tag from
an unauthorized package gets a logged warning and the tag is discarded. Use your own
namespace.

You don't have to build on `OvertureFeature` — subclass `system.Feature` directly for a
GeoJSON-serializing model with none of the Overture conventions.

### 8.4 Write a new codegen target

For a format nobody else generates — Arrow schemas, Avro, Go structs, protobuf — add a
renderer to the codegen rather than parsing JSON Schema back out. You get the full
semantic model: NewType names, constraint provenance, discriminated union structure — all
the things JSON Schema flattens away.

The pipeline is four layers with strictly downward imports:

```
Rendering        →  output formatting, all presentation decisions
Output Layout    →  what to generate, where it goes, how outputs link
Extraction       →  FieldShape, FieldSpec, RecordSpec, UnionSpec, EnumSpec
Discovery        →  discover_models()
```

Extraction is target-independent, so a new target is a new renderer, not new extraction
logic. The entry point:

```python
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.buildings import Building

spec = extract_model(Building)
spec.name  # 'Building'
spec.description  # the class docstring
spec.constraints  # model-level constraints

for f in spec.fields[:6]:
    print(f"{f.name:12} required={f.is_required!s:5} {type(f.shape).__name__}")
```

```
id           required=True  NewTypeShape
bbox         required=False Primitive
geometry     required=True  Primitive
theme        required=True  LiteralScalar
type         required=True  LiteralScalar
version      required=True  NewTypeShape
```

`FieldSpec` is `(name, shape, description, is_required, is_optional)`. The `shape` is a
`FieldShape` tree — `NewTypeShape`, `Primitive`, `LiteralScalar`, `ModelRef`,
`UnionRef`, and container variants — with sub-models and sub-unions already resolved.
Constraints carry provenance, so you can tell which NewType contributed which bound:

```python
from overture.schema.codegen.extraction.type_analyzer import analyze_type
from overture.schema.common.feature import FeatureVersion

shape, is_nullable, description = analyze_type(FeatureVersion)
# shape → NewTypeShape(name='FeatureVersion', inner=Primitive(base_type='int32',
#           constraints=(ConstraintSource(source_name='FeatureVersion', constraint=Ge(ge=0)), ...)))
```

`analyze_type` returns a **3-tuple** `(FieldShape, bool, str | None)` — the structural
shape, whether the field accepts `None`, and the first description found while
unwrapping. (The codegen README shows an older `TypeInfo`/`TypeKind` API that no longer
exists.)

To wire up a new format: add a column to `TypeMapping` in
`extraction/type_registry.py` for type-name resolution, write a pipeline module
consuming `ModelSpec` trees plus a renderer, and register the format in `cli.py`.

Further reading in the repo:

- `packages/overture-schema-codegen/docs/design.md` — architecture, data flow, extension points
- `packages/overture-schema-codegen/docs/walkthrough.md` — module-by-module trace of `Segment` through the pipeline

---

---

## 9. Registering models and tagging

How feature types make themselves known to the tooling. This is the mechanism that
lets your own models slot in alongside Overture's — see
[Register your own feature types](#83-register-your-own-feature-types) for a worked example.

The library is designed to support data producer extensions through multiple patterns.
This extensibility is a core feature that allows organizations to add custom fields and
types while maintaining compatibility with the base Overture schema. We are in the
process of determining how this should work.

### Model Registration via Entry Points

Models are registered using [setuptools entry
points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html) in each
package's `pyproject.toml` file. This enables automatic discovery and loading of models
at runtime without requiring explicit imports.

Registration is done in the `[project.entry-points."overture.models"]` section:

```toml
[project.entry-points."overture.models"]
building = "overture.schema.buildings:Building"
building_part = "overture.schema.buildings:BuildingPart"
```

The discovery system provides programmatic access to registered models:

```python
from overture.schema.system.discovery import discover_models, get_registered_model

# Discover all registered models, keyed by ModelKey
all_models = discover_models()

# Get a specific model by name
building_model = get_registered_model("building")
if building_model:
    building = building_model.model_validate(building_data)
```

### Tagging

Each `ModelKey` returned by `discover_models()` carries a `frozenset[str]` of tags
that classify the model orthogonally to its entry-point name -- whether the model
is a `Feature` subclass, which Overture theme it belongs to, which package shipped
it, and so on. Downstream tools (the CLI, codegen, third-party consumers) use tags
to filter the working set without importing every model:

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

Tags are produced by *tag providers* registered on the `overture.tag_providers`
entry-point group. The `system` and `common` packages ship the built-in providers
(`feature` and `overture:theme=*`); third parties can register their own
to attach custom tags during discovery. See the [`overture-schema-system`
README](packages/overture-schema-system/README.md#tagging) for tag format,
reserved namespaces, and provider authoring.


---

## 10. Authoring new schema models

### Quick Start

#### Essential Imports

Copy what you need for most models:

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

#### Templates

Copy-paste starting points for the four shapes you'll write most often — a plain
model, a feature, an enum, and a model with validation constraints — live together in
[Templates and quick reference](#13-templates-and-quick-reference) rather than being
repeated here.

---

### Basic Concepts

#### Models and Inheritance

##### What are Pydantic models?

Pydantic models are Python classes that define data structures and their constraints. Think of them like UML classes with built-in data validation - each model defines what fields are allowed and what types of data they can contain.

##### Model Base Classes and Inheritance

**What is a "base class"?** A base class defines common fields and behaviors that other classes can reuse. Think of it like a slide template - you create one layout, then make specific slides that use that structure.

**What is "inheritance"?** Inheritance means one class automatically gets all the fields and behaviors from another class. If Building inherits from OvertureFeature, it automatically gets all of Feature's fields (like `id`, `geometry`) plus any new fields you add to Building (like `height`). When multiple parent classes have the same field name, Python uses a [specific order](https://docs.python.org/3/tutorial/classes.html#multiple-inheritance) to determine which one takes precedence.

**@no_extra_fields** - Use for structured data components that should reject unknown fields:

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

**OvertureFeature[ThemeT, TypeT]** - A generic base class for all geospatial features with typed theme and type parameters:

```python
from typing import Literal
from overture.schema.common import OvertureFeature
from overture.schema.system.numeric import float64


class Building(OvertureFeature[Literal["buildings"], Literal["building"]]):
    """A building feature with strongly-typed theme and type."""

    # Inherits: id, theme, type, geometry, bbox, version, sources
    height: float64 | None = None
```

**What does "generic" mean?** The `OvertureFeature[ThemeT, TypeT]` syntax makes OvertureFeature a "generic" class - think of it like a template that can be customized with specific values. The square brackets `[]` contain "type parameters" that specify exactly what theme and type this feature represents.

**What are ThemeT and TypeT?** These are placeholders for specific text values:

- **ThemeT**: The data theme (like "buildings", "places", "transportation")
- **TypeT**: The specific feature type within that theme (like "building", "place", "segment")

**What is `Literal`?** `Literal` means the field must be exactly one of the specified values - nothing else is allowed. So `Literal["buildings"]` means this theme can only be "buildings", not any other string.

By specifying `OvertureFeature[Literal["buildings"], Literal["building"]]`, you're saying "this is a Feature that must have theme='buildings' and type='building'" - no other values are allowed. This prevents mistakes like accidentally creating a building with theme="places".

##### Inheritance Patterns

**Multiple inheritance** combines fields from several base classes:

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

##### Field Aliases

Sometimes you need a field name that conflicts with Python keywords or conventions (hint: you'll get an error when you try to use it). Use `Field(alias="<data field name>")` to map between Python-friendly field names and the actual data field names:

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

A common example is `class_` with `Field(alias="class")` since "class" is a Python keyword but a common field name in data schemas.

#### Field Types

##### Required vs Optional Fields

```python
class Building(OvertureFeature):
    # Required field (no default value)
    geometry: Geometry

    # Optional field (has default value of None)
    height: float64 | None = None
```

- **Required fields**: Must be provided when creating an instance
- **Optional fields**: Can be omitted; they have a default value (usually `None`)

> [!WARNING]
> **Always use `None` defaults** for optional fields. Non-`None` defaults create ambiguity between schema defaults and actual data values.

**Why do non-`None` defaults cause problems?**

1. **Data transformation ambiguity**: Pydantic adds default values that weren't in the input, making it impossible to distinguish between original data and schema defaults.

2. **Schema vs. data confusion**: Schemas serve multiple purposes:
   - **Validation only**: Check if existing data is valid (shouldn't transform it)
   - **Data processing**: Parse and potentially transform data with Pydantic
   - **Documentation**: Show developers what fields exist and what they mean

3. **Implicit semantic meaning**: Default values encode business logic into the schema, which should be in business logic instead.

**Better approaches:**

1. **Use `None` and document semantics:**

   ```python
   access_policy: Annotated[
       str | None,
       Field(description="Access policy for the place. When absent, assume 'open'"),
   ] = None
   ```

2. **Always populate in data pipeline:**

   ```python
   # In your data processing pipeline, always set the value
   place.access_policy = place.access_policy or "open"
   ```

Keep the schema separate from business logic. The schema describes the shape of data, not the business rules about what missing values mean.

##### Numeric Types

**Always use specific numeric types instead of Python's generic `int`/`float`:**

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

**When to use each:**

- **`int32`**: Most integer fields (years, counts, IDs)
- **`uint8`**: Small positive values (0-255), like color components, confidence percentages
- **`uint16`**: Medium positive values (0-65K), like ports, small counts
- **`uint32`**: Large positive values, like population, large IDs
- **`float64`**: Most decimal numbers (heights, coordinates, measurements) - **this is the default choice**
- **`float32`**: When space is critical and precision isn't

When in doubt, use `int32` (equivalent to `int`), `int64` (equivalent to `long`, although [not safely representable in JSON](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER)), or `float64` (equivalent to `double`).

**Why specific numeric types matter:**

The specific numeric types are crucial for data interchange and storage compatibility:

- **Cross-platform consistency**: Ensures the same data types across Python, Arrow, Parquet, and other geospatial tools
- **Round-trip compatibility**: Data round-trips cleanly between Parquet files, databases (PostgreSQL, Trino), Shapefiles, and JSON Schema
- **Value range validation**: Prevents invalid values (e.g., negative heights, RGB values > 255)
- **Storage efficiency**: `uint8` uses 1 byte vs `int64` which uses 8 bytes
- **Built-in validation**: These types use Pydantic `Field()` constraints to validate ranges (e.g., `Field(ge=0, le=100)` ensures values stay within bounds)

##### Union Types

Union types allow a field to accept multiple different types. The `|` symbol means "or":

```python
from typing import Literal


class Building(OvertureFeature):
    # This field can be either a string OR None (most common union)
    name: str | None = None

    # This field can be one of specific string values OR None
    status: Literal["active", "inactive", "pending"] | None = None
```

**Common union patterns:**

```python
# Optional field (most common union)
height: float64 | None = None  # Can be a number or missing

# Specific string values (an alternative to enums where descriptions aren't needed)
priority: Literal["low", "medium", "high"] | None = None

# Boolean or None
is_verified: bool | None = None
```

**Union best practices:**

- Keep unions simple - avoid more than 2-3 types when possible
- Optional fields will include `None` to become optional
- Use `Literal` values for specific string choices rather than mixing basic types
- **Avoid mixed-type unions** like `str | int32` - these don't work well with many storage layers

> [!WARNING]
> **Storage compatibility**: Mixed-type unions (combining different basic types like `str | int32`) don't work with Parquet and other storage layers. Use `Literal` values or separate fields instead.

#### Field Enhancement

##### Adding Descriptions and Constraints with Annotated

`Annotated` is Python's way to add extra information (metadata) to a type without changing the type itself. Think of it like adding notes or constraints to a field definition.

**Basic concept:**

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

**What goes inside `Annotated`:**

1. **First argument**: The actual type (`str`, `int32`, `list[str]`, etc.)
2. **Additional arguments**: Metadata like constraints, descriptions, validation rules

##### Field Constraints

Use Pydantic's `Field()` function to add constraints and descriptions:

**Numeric constraints:**

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

**Numeric constraint options:**

- **`ge`**: Greater than or equal to (≥)
- **`gt`**: Greater than (>)
- **`le`**: Less than or equal to (≤)
- **`lt`**: Less than (<)

**String constraints:**

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

**String constraint options:**

- **`min_length`**: Minimum string length
- **`max_length`**: Maximum string length
- **`pattern`**: Regular expression pattern (regex)

#### Collections and Lists

##### Basic List Fields

```python
class Building(Feature):
    # Simple list of strings
    tags: list[str] | None = None

    # List of complex objects
    access_rules: list[AccessRule] | None = None
```

##### List Constraints

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

**List constraint options:**

- **`min_length`**: Minimum number of items
- **`max_length`**: Maximum number of items
- **`UniqueItemsConstraint()`**: No duplicate items (custom validation)

**Important**: `UniqueItemsConstraint()` must come AFTER `Field()` for proper JSON Schema generation.

> [!CAUTION]
> **Constraint order matters**: Always put `Field()` before `UniqueItemsConstraint()` or JSON Schema generation will create `minLength` (string constraint) instead of `minItems` (array constraint).
>
> **Why**: Pydantic processes annotations in order for JSON Schema generation. `Field()` must come first to set up the field properly. For lists, `Field(min_length=1)` creates a `minItems` constraint in the JSON Schema because the type immediately before it is a list. If `UniqueItemsConstraint()` comes first, Pydantic doesn't see the list type and treats `min_length` as a string constraint (`minLength`).

##### List Behavior

Lists maintain their **insertion order** (the order data exists in the field), but they are **not automatically sorted**.

#### Enumerations

**What is an enumeration (enum)?** An enumeration is a way to define a fixed set of allowed values for a field. Think of it like a multiple-choice question - you define all the valid answers ahead of time, and users can only pick from those options.

For example, instead of allowing any string for a "status" field (which could lead to typos like "activ" or "Active"), you create an enum with exactly "active", "inactive", and "pending" as the only allowed values.

**Enums vs Literal:** You can achieve similar results with `Literal["active", "inactive", "pending"]`, but formal enums are better when you need descriptions, documentation, or want to reuse the same set of values across multiple fields.

##### Creating Enums

Enums define a fixed set of allowed values:

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

##### Documenting Enum Values

Add documentation to describe what the enum and its values mean. In Python, you do this with **docstrings** - text enclosed in triple quotes `"""` that describes what something does:

Use `DocumentedEnum` from `overture.schema.system.doc` when enum members need their own descriptions for code generation and documentation tooling. Each member takes a `(value, description)` tuple:

```python
from overture.schema.system.doc import DocumentedEnum


class VehicleType(str, DocumentedEnum):
    """Types of vehicles for transportation."""

    CAR = ("car", "Standard passenger vehicle")
    TRUCK = ("truck", "Commercial freight vehicle")
    BICYCLE = ("bicycle", "Human-powered two-wheeler")
    MOTORCYCLE = ("motorcycle", "Motorized two-wheeler")
```

Members without descriptions use the plain value form -- documentation is optional per-member:

```python
class ConnectionState(str, DocumentedEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    QUIESCING = (
        "quiescing",
        "Gracefully shutting down, rejecting new requests but completing existing ones",
    )
```

Use `DocumentedEnum` over plain `str, Enum` when the enum members' semantics aren't obvious from their names and downstream tools (code generators, documentation renderers) need access to member-level descriptions. Use plain `str, Enum` for self-explanatory values.

##### Why str, Enum?

Inheriting from `str, Enum` makes enum values work as both enums and strings, which is useful for JSON serialization and compatibility.

---

### Advanced Patterns

#### Relationship Patterns

##### What are relationships?

Relationships represent connections between different features or models. Think of them like links that connect related pieces of information — for example, a building part that is structurally part of a building, or a division area that is administratively nested under a division.

Pydantic provides several ways to express these relationships, each suited to different use cases and complexity levels. Before choosing a pattern, it's important to understand the **semantic type** of the relationship you're modeling.

---

##### Semantic Relationship Types

Every relationship between two features carries a semantic meaning about coupling strength, lifecycle dependency, and ownership. The schema defines four relationship types, ordered from strongest to weakest coupling. The types describe the *nature* of the link, not which feature is "parent" or "child." Direction is implicit: the feature holding the reference is the source, and the type it references is the destination.

###### `COMPOSITION` — Structural Whole-Part

A structural whole-part relationship with lifecycle dependency. The part has no independent meaning outside the whole. Deleting the whole invalidates the part.

**Test question:** *"If I delete the whole, does keeping the part orphaned make any sense at all?"* If the answer is no, it's `COMPOSITION`.

**Examples:**
- `BuildingPart` → `Building` — part *is part of* building
- `DivisionBoundary` → `Division` — boundary line *defines the boundary of* division

###### `AGGREGATION` — Grouping Without Lifecycle Dependency

A grouping or collection relationship where both members are independently viable. No lifecycle dependency — the member survives reassignment to another group or orphaning.

**Test question:** *"Can both sides belong to something else or nothing and still be a valid map feature?"* If yes, they form an `AGGREGATION`.

**Examples:**
- `Route` → `Segment` — route *groups* segments
- `TrailSegment` → `NationalPark` — segment *is grouped by* park

###### `HIERARCHY` — Organizational Nesting

An organizational or classificatory nesting relationship. This is not about structural assembly — it's about administrative parentage, taxonomy, or categorization.

**Test question:** *"Is this about organizational subordination rather than structural assembly?"* If yes, it's `HIERARCHY`.

**Examples:**
- `DivisionArea` → `Division` — area *is child of* division
- `Division` → `Division` — child division nested under parent

###### `ASSOCIATION` — Peer-Level Reference

A peer-level reference with no ownership, containment, or nesting. Neither feature depends on or contains the other. This is the fallback when none of the stronger types apply.

**Test question:** *"Are these just peers that know about each other?"* If yes, it's `ASSOCIATION`.

**Examples:**
- `Segment` → `Connector` — segment references its start/end connector
- `Building` → `Address` — a building references its address, neither owns the other

---

##### Selection Priority

When a relationship could fit multiple types, the choice follows a **diamond decision**: start at the top, fork in the middle based on the *kind* of coupling, and fall through to the bottom only when no stronger type applies.

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

---

##### The `role` Field

The `Reference` annotation accepts an optional `role` parameter — a snake_case string that further qualifies the relationship from the source's perspective. It has no effect on schema validation; it is informational metadata for documentation and tooling.

Use `role` when the semantic type alone is ambiguous. For example, multiple `HIERARCHY` references on the same model can be disambiguated:

```python
# Without role: two HIERARCHY references to Division — which is which?
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

The `role` must be a non-empty snake_case string (lowercase letters, digits, underscores). It describes the source's role relative to the target using source-perspective phrasing.

---

##### Implementation Patterns

###### 1. Direct References (Foreign Keys)

The fundamental pattern is a direct reference where one feature "points to" another using an ID field with type safety and semantic information.

```python
from typing import Annotated, Literal
from pydantic import Field
from overture.schema.common import OvertureFeature
from overture.schema.system.ref import Id, Reference, Relationship


# COMPOSITION — part points to its whole
class BuildingPart(OvertureFeature[Literal["buildings"], Literal["building_part"]]):
    """A structural part of a building."""

    building_id: Annotated[
        Id,
        Reference(Relationship.COMPOSITION, Building, role="part_of"),
        Field(description="The building to which this part belongs"),
    ]


# HIERARCHY — child points to parent
class DivisionArea(OvertureFeature[Literal["divisions"], Literal["division_area"]]):
    """Area polygon nested under a division."""

    division_id: Annotated[
        Id,
        Reference(Relationship.HIERARCHY, Division, role="child_of"),
        Field(description="Division ID of the parent division of this area."),
    ]


# ASSOCIATION — peer reference, no ownership
class ConnectorReference(BaseModel):
    """Reference to a connector feature."""

    connector_id: Annotated[
        Id, Reference(Relationship.ASSOCIATION, Connector, role="connects_to")
    ]
```

###### 2. Association as a Separate Feature (Complex Relationships)

When the relationship itself needs to store information, create a dedicated feature to represent it. This applies regardless of the semantic type — any of the four types can carry metadata.

**Simple relationship (use Pattern 1):**
- "Building Part A is part of Building B" — just needs an ID reference.

**Complex relationship (use Pattern 2):**
- "Admin Area X has City Center Y as its primary center since 2010 with 85% confidence" — the relationship has properties.

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

**When to use separate association features:**
- The relationship has properties (confidence scores, dates, types, notes).
- Many-to-many connections exist.
- You need to query the relationships independently.

###### 3. Collection References

When a feature needs to reference multiple other features, use a list of references. The semantic type still matters.

```python
# COMPOSITION — boundary defines two divisions
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


# AGGREGATION — route groups segments
class Route(OvertureFeature[Literal["transportation"], Literal["route"]]):
    """A transportation route passing through multiple segments."""

    segment_ids: Annotated[
        list[Id],
        Reference(Relationship.AGGREGATION, TransportationSegment, role="groups"),
        Field(min_length=1, description="Ordered segments in this route"),
        UniqueItemsConstraint(),
    ]
```

---

##### Best Practices

###### Always Use Reference Annotations

Include `Reference` annotations for semantic clarity and documentation:

```python
# Good — complete relationship information with semantic type and role
division_id: Annotated[
    Id,
    Reference(Relationship.HIERARCHY, Division, role="child_of"),
    Field(description="Division ID of the parent division of this area."),
]

# Avoid — missing semantic information
division_id: Id
```

###### Choose the Right Semantic Type First, Then the Right Pattern

1. **Determine the semantic type** using the selection priority and test questions above.
2. **Then choose the implementation pattern:**
   - Simple relationships → Direct references (Pattern 1)
   - Relationships with metadata → Separate association features (Pattern 2)
   - One-to-many references → Collection references (Pattern 3)

#### Discriminated Unions

**What is a discriminated union?** A discriminated union is a type that can be backed by one of several different models, where a specific field (the "discriminator") determines which model it actually is. Think of it like a form that changes its fields based on a category selection.

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

The `discriminator="subtype"` tells Pydantic to look at the `subtype` field to determine which specific model to use. If `subtype` is "road", it uses `RoadSegment`; if "rail", it uses `RailSegment`.

##### Abstract vs Concrete Classes

**What's the difference?** In UML and traditional OOP, abstract classes cannot be instantiated - they serve as templates for concrete classes. In Pydantic, by default, **all classes are concrete** (can be instantiated), but you can make classes abstract when needed.

**Current pattern (all concrete):**

```python
# Both can be instantiated as map features
base_segment = TransportationSegment(subtype=Subtype.ROAD, geometry=...)  # Valid
road_segment = RoadSegment(subtype=Subtype.ROAD, geometry=..., class_=...)  # Valid
```

**Making the base class abstract:**

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

**Registration pattern (recommended when working with Overture models):**

Instead of making classes abstract, we use **entry point registration** where only specific concrete types are discoverable as map features:

```toml
# In packages/overture-schema-theme-transportation/pyproject.toml
[project.entry-points."overture.models"]
connector = "overture.schema.transportation:Connector"
segment = "overture.schema.transportation:Segment"
```

**Real example:** See [`packages/overture-schema-theme-transportation/src/overture/schema/transportation/segment/__init__.py`](packages/overture-schema-theme-transportation/src/overture/schema/transportation/segment/__init__.py) where:

- **`Segment`** is a discriminated union: `RoadSegment | RailSegment | WaterSegment`
- **`TransportationSegment`** is the concrete base class that all segment types inherit from
- **Individual segment types** (`RoadSegment`, `RailSegment`, `WaterSegment`) are NOT directly registered

**This registration pattern means:**

1. Only **`Segment`** (the union type) is discoverable as an official map feature
2. The union automatically resolves to the correct concrete type based on the `subtype` field
3. All classes (`TransportationSegment`, `RoadSegment`, etc.) can be reused as base classes for alternate implementations

#### Pattern Properties (Constrained Key-Value Maps)

**What are pattern properties?** Pattern properties let you create key-value maps where the keys must follow a specific pattern (like language codes) and values have specific types.

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

**Example data:**

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

The `additionalProperties: False` ensures only keys matching the pattern are allowed when generated JSON Schema is used.

#### Nested List Validation

**What is nested list validation?** This pattern validates both the outer list and the inner structure of each item, with constraints at multiple levels.

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

This creates validation at three levels:

1. **Individual items**: Each `HierarchyItem` validates its own fields (`division_id`, `name`)
2. **Inner lists**: Each inner list must have at least 1 item (`min_length=1`)
3. **Outer list**: The `hierarchies` field must have at least 1 inner list (`min_length=1`)

#### Type Aliases for Reusable Patterns

**What are type aliases?** Type aliases let you create custom names for complex or frequently-used types. Think of them like creating shortcuts or nicknames for long type definitions.

**What is `NewType`?** `NewType` creates a distinct type that's based on an existing type but is treated as different for type checking purposes. This helps prevent mistakes like using an email address where you need a country code, or using a person's name where you need an ID - they're all strings, but they have different meanings and shouldn't be interchangeable.

**Note**: `NewType` is primarily useful when working with Pydantic models in Python code (development, testing, certain data processing tasks). It doesn't affect data validation or JSON Schema generation - it's a development tool to catch mistakes before they happen.

> [!WARNING]
> **Naming conflicts**: Never use the same name for a model class and type alias in the same module - this creates circular references and confusing code.

**Guidelines:**

- **Model classes**: Use noun names (`SourceItem`, `AccessRule`, `GeometricScope`)
- **Type aliases**: Use plural or descriptive names (`Sources`, `AccessRules`, `ConnectivityData`)
- **Avoid using the same names**: Use different names for models and type aliases, even if they're related

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

**Why use type aliases?**

1. **Prevent mistakes**: `SegmentId` and `CountryCode` are both strings, but you can't mix them up when they're created using `NewType`
2. **Reusable patterns**: Define complex field validation once, use it many times
3. **Self-documenting code**: `EmailList` is clearer than `list[str]`
4. **Consistency**: Everyone uses the same validation rules for the same concept

---

### Integration Guide

#### Project Architecture

##### File Organization

Organize code by scope, and avoid circular imports.

**Cross-theme shared**: the `overture-schema-common` package. Definitions more than
one theme needs -- `OvertureFeature`, `Names`, `Sources`, the scoping framework.

**One module per feature type**: at the theme package root, named after the type in
snake_case.

```text
packages/overture-schema-theme-buildings/src/overture/schema/buildings/
    __init__.py         # re-exports the public names, declares __all__
    _common.py          # shared by Building and BuildingPart
    building.py         # Building, BuildingSubtype, BuildingClass
    building_part.py    # BuildingPart
```

The module owns everything specific to its type: the `Feature` subclass, its enums,
its NewTypes, and its supporting models. `building.py` defines `BuildingSubtype` and
`BuildingClass` next to `Building`, because nothing else uses them.

**Theme-level shared**: `_common.py` at the theme package root, for definitions two
or more types in the theme need. `buildings/_common.py` holds `Appearance`,
`RoofShape`, and the material enums that both `Building` and `BuildingPart` use. The
leading underscore marks the module private -- the theme's `__init__.py` re-exports
the public names from it.

**A type large enough to split**: a subpackage named after the type, applying the
same rules one level down.

```text
packages/overture-schema-theme-transportation/src/overture/schema/transportation/
    __init__.py         # re-exports from connector and segment
    connector.py        # Connector
    segment/
        __init__.py     # assembles the Segment discriminated union, re-exports
        _common.py      # TransportationSegment and what the arms share
        road.py         # RoadSegment and its supporting types
        rail.py         # RailSegment and its supporting types
        water.py        # WaterSegment
```

Every `__init__.py` re-exports its public names and declares `__all__`, so consumers
import from the package rather than reaching into the defining module:
`from overture.schema.buildings import Building`, not
`from overture.schema.buildings.building import Building`. Entry points name the
package root for the same reason -- `building = "overture.schema.buildings:Building"`.

There is no `models.py` / `enums.py` / `types.py` split. An enum lives in the module
whose type uses it, and moves up to `_common.py` when a second type needs it.

##### Import Organization

```python
# Standard library imports first
from enum import Enum
from typing import Annotated, Literal, NewType

# Third-party imports
from pydantic import BaseModel, ConfigDict, Field

# Cross-theme and system imports
from overture.schema.common.scoping import Heading, Scope, scoped
from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields

# Local imports last -- siblings in the theme, then the module's own package
from ..connector import Connector
from ._common import SegmentSubtype, TransportationSegment
```

`uv run ruff format <file>` will sort your imports in this order automatically.

##### Why Not Use @field_validator or @model_validator?

This project uses a custom validation system that generates better JSON Schema output and supports code generation (without additional work, `@field_validator` and `@model_validator` don't make their constraints discoverable). Always use constraints from `overture.schema.system` instead of using Pydantic validation decorators:

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

#### Migrating from JSON Schema

If you're familiar with JSON Schema files (like `schema/schema.yaml`), this section helps translate those patterns to Pydantic models.

##### How $defs and $ref Translate

**JSON Schema approach:**

```yaml
# In defs.yaml
"$defs":
  propertyDefinitions:
    address:
      type: object
      properties:
        freeform: { type: string }
        locality: { type: string }

# In building.yaml
properties:
  address: { "$ref": "../defs.yaml#/$defs/propertyDefinitions/address" }
```

**Pydantic approach:**

```python
# In overture-schema-theme-addresses/src/overture/schema/addresses/address.py
@no_extra_fields
class Address(BaseModel):
    """A postal address."""

    freeform: str | None = None
    locality: str | None = None


# In overture-schema-theme-buildings/src/overture/schema/buildings/building.py
class Building(OvertureFeature):
    address: Address | None = None
```

**Primary differences:**

- JSON Schema uses `$ref` to reference definitions; Pydantic uses direct Python imports
- JSON Schema definitions live in `$defs`; Pydantic models are regular Python classes grouped into modules
- JSON Schema allows inline definitions; Pydantic encourages separate model classes

##### How Containers Work

**JSON Schema containers** (like `namesContainer`, `shapeContainer`) are reusable property groups:

```yaml
# In defs.yaml
propertyContainers:
  namesContainer:
    properties:
      names: { "$ref": "#/$defs/propertyDefinitions/allNames" }

  shapeContainer:
    properties:
      height: { type: number }
      num_floors: { type: integer }

# In building.yaml
allOf:
  - "$ref": ../defs.yaml#/$defs/propertyContainers/namesContainer
  - "$ref": ./defs.yaml#/$defs/propertyContainers/shapeContainer
```

**Pydantic equivalent** uses **mixin classes**:

```python
# namesContainer -> Named, in
# overture-schema-common/src/overture/schema/common/names.py
class Named(BaseModel):
    """Properties defining the names of a feature."""

    names: Names | None = None


# shapeContainer -> Appearance, in buildings/_common.py,
# shared by Building and BuildingPart
class Appearance(BaseModel):
    """Physical and visual properties of a building."""

    height: float64 | None = None
    num_floors: int32 | None = None
    # ... roof and facade fields


# Usage with multiple inheritance -- this is how Building is actually declared
class Building(
    OvertureFeature[Literal["buildings"], Literal["building"]],
    Named,
    Stacked,
    Appearance,
): ...  # inherits names, level, height, num_floors, and the rest from its parents
```

JSON Schema containers become **mixin classes** in Pydantic that you inherit from.

##### Common Translation Patterns

| JSON Schema | Pydantic | Notes |
|-------------|----------|-------|
| `"$ref": "other.yaml#/path"` | `from other import Model` | Direct Python imports |
| `allOf: [ref1, ref2]` | `class Model(Base1, Base2)` | Multiple inheritance |
| `minLength: 1` | `Field(min_length=1)` | Field constraints |
| `minimum: 0, maximum: 100` | `Field(ge=0, le=100)` | Numeric ranges |
| `uniqueItems: true` | `UniqueItemsConstraint()` | Custom constraint |
| `enum: [a, b, c]` | `class E(str, Enum): A="a"` | Enum class |
| `type: ["string", "null"]` | `str \| None = None` | Optional types |
| `if/then` conditional | Custom validation constraints | Model constraints |

---


---

## 11. Development workflow


This project uses [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
# Install dependencies for the entire workspace
uv sync --all-packages

# Run all tests and type/code quality checks
make check

# Run tests for a specific package
uv run pytest packages/overture-schema-theme-buildings/

# Run tests matching a pattern
uv run pytest -k "buildings"
```

Auto-format / fix code to align with project expectations:

```shell
uv run ruff check --fix
uv run ruff format
uv run docformatter --in-place --recursive packages/
```

---

# Part III — Reference

## 12. Gotchas

Things that cost time if you don't know them.

| Gotcha | What happens | Fix |
|---|---|---|
| `model_validate(geojson_dict)` | `ValidationError`: missing `theme`/`version`, `type` is `'Feature'` | Use `model_validate_json()`. Python mode expects flat data, JSON mode expects GeoJSON. |
| `model_dump()` without `by_alias` | Emits `class_`, not `class`; output won't re-validate | Always `by_alias=True` |
| `Segment.model_validate(...)` | `AttributeError` — it's a union alias, not a class | `TypeAdapter(Segment).validate_json(...)` |
| `model_names()` returns `[]` | PySpark expressions are generated, not committed | `make generate-pyspark` (or `make install`) |
| Dumps full of `null` | Unset optionals serialize explicitly | `exclude_none=True` |
| Absent list → `[]` → won't re-validate | An omitted optional list defaults to `[]` on the model, dumps as `[]`, then fails a `min_length` check on the way back in | `exclude_defaults=True`, or drop empty lists before re-validating |

Asymmetric round-trip, worth knowing about: an optional list that is simply *absent*
from the input becomes an empty list on the model, and an empty list is not the same as
absent on the way back out.

```python
segments = TypeAdapter(Segment)
seg = segments.validate_json(
    open("road-indoors.yaml-as-json").read()
)  # no `connectors` key
seg.connectors  # []      ← not None

flat = seg.model_dump(mode="python", by_alias=True, exclude_none=True)
flat["connectors"]  # []      ← exclude_none doesn't drop it
segments.validate_python(flat)
# ValidationError: road.connectors
#   List should have at least 2 items after validation, not 0
```

The same document validates fine on the way in (the CLI accepts it) and fails on the way
back. `exclude_defaults=True` avoids it, as does pruning empty lists before re-validating.

### Docs in the repo that are currently wrong

- **`pip install overture-schema`** — in every package README. Nothing is on PyPI yet;
  see [7.3](#73-what-changes-once-these-packages-are-published). Every other item that
  stood here has been fixed, and `tests/test_documented_imports.py` now imports every
  `overture.*` statement in every tracked Markdown file, so a broken one fails the suite
  rather than accumulating here.

---

## 13. Templates and quick reference

### Reference

#### Complete Templates

##### Basic Model Template

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

##### Feature Template

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

##### Enum Template

```python
from enum import Enum


class MyEnum(str, Enum):
    """Description of what this enum represents."""

    VALUE_ONE = "value_one"
    VALUE_TWO = "value_two"
    VALUE_THREE = "value_three"
```

##### Model with Validation Constraints

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

##### Association Feature Template

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
    # ASSOCIATION); what the reference means is carried by `role`. Two
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

#### Quick Reference

##### Essential Patterns (Most Common)

```python
# Basic field types
name: str  # Required string
name: str | None = None  # Optional string
count: int32  # Required integer
priority: Literal["high", "medium", "low"] | None = None  # Constrained values

# Validated fields
height: Annotated[float64 | None, Field(ge=0, description="Height in meters")] = None
tags: Annotated[list[str] | None, Field(min_length=1), UniqueItemsConstraint()] = None

# Association patterns -- Relationship is the kind, role is the meaning
parent_id: Annotated[
    Id | None,
    Reference(Relationship.HIERARCHY, ParentModel, role="child_of"),
] = None
connector_ids: list[Id]  # References to multiple related features
```

##### Model Templates

```python
# Non-feature model
@no_extra_fields
class Address(BaseModel):
    street: str
    city: str | None = None


# Feature model
class Building(OvertureFeature[Literal["buildings"], Literal["building"]]):
    geometry: Geometry
    height: float64 | None = None


# Enum
class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
```

##### Constraint Reference

| Type | Constraint | JSON Schema | Example |
|------|------------|-------------|---------|
| **Numeric** | `ge=0, le=100` | `minimum`, `maximum` | `Field(ge=0, le=100)` |
| **String** | `min_length=1, pattern=r"..."` | `minLength`, `pattern` | `Field(min_length=1, pattern=r"^[A-Z]+$")` |
| **List** | `min_length=1, UniqueItemsConstraint()` | `minItems`, `uniqueItems` | `Field(min_length=1), UniqueItemsConstraint()` |
| **Custom** | `LanguageTagConstraint()` | Custom validation | `LanguageTagConstraint()` |

##### Import Cheatsheet

```python
# Essential imports for most models
from typing import Annotated, Literal
from enum import Enum
from pydantic import Field
from overture.schema.common import OvertureFeature
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.numeric import int32, float64

# For associations and references
from overture.schema.system.ref import Id, Reference, Relationship
```

##### Naming Conventions

- **Classes**: `PascalCase` (`Building`, `AccessRule`)
- **Fields**: `snake_case` (`construction_year`, `has_parts`)
- **Enums**: `UPPER_SNAKE_CASE = "value"` (`ACTIVE = "active"`)
