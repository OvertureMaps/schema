# Glossary

Two vocabularies meet in this repository. The first describes the map: what an entity is,
what a feature is, how feature types are named. The second describes the Python packages
that define the schema: workspaces, entry points, specs. Both are collected here.

Terms in the second group are cross-referenced to the section of
[SCHEMA_GUIDE.md](SCHEMA_GUIDE.md) that covers them in full.

---

## Data model

### Entity

An entity is a thing in the physical world. It can relate both to physical objects or more
abstract concepts that have a spatial presence (e.g. administrative areas are not physical
objects as such, but they have physical properties that define their location and extent).
An entity can only exist once.

### Feature

A Feature is an abstraction of a specific entity in the map. It exists only in its digital
form.

### Feature Class

Feature Class is a synonym for "Feature Type". The preferred term is "Feature Type".

### Feature Type

A Feature Type is a type of entities with common properties as described in the Overture
Schema.

### Instance

Instance is a synonym for "Feature". The preferred term is "Feature".

### Object

Object is a synonym for "Instance" or "Feature". The preferred term is "Feature".

### Theme

The top-level grouping a feature type belongs to, and a mandatory property on every
feature. The term is deliberately chosen over "layer" to avoid that word's baggage. There
are six: `addresses`, `base`, `buildings`, `divisions`, `places`, `transportation`. Each
ships as its own Python package, `overture-schema-theme-*`.

### Type

The feature type within a theme, and a mandatory property on every feature — for example
`theme=buildings`, `type=building`. Together `theme` and `type` identify the feature type.

### Subtype

An optional third property that further refines the feature type — for example
`theme=transportation`, `type=segment`, `subtype=road`. Where a type has subtypes, the
model for that type is usually a [discriminated union](#discriminated-union) with one arm
per subtype. Note the spelling: the field is `subtype`, not `subType`.

### GERS

The Global Entity Reference System. A feature's `id` may be a GERS ID if — and only if —
the feature represents an entity that is part of GERS.

---

## Toolchain

### Alias

Three unrelated things in this codebase go by this name. Which one is meant is almost
always clear from context, but they are worth separating:

1. **Field alias** — a mapping from a Python attribute name to the name the data uses,
   declared with `Field(alias=...)`. It exists because some data field names are not legal
   Python identifiers: `Building.class_` carries `alias="class"`, since `class` is a
   reserved word. Dump with `by_alias=True` to get the data name back.
2. **Type alias** — a module-level name bound to a type expression rather than to a class.
   `Segment` is one: it is an `Annotated[Union[...], Discriminator(...)]`, *not* a class.
   This is why `Segment.model_validate(...)` raises `AttributeError` and you need
   `TypeAdapter(Segment).validate_python(...)` instead. See
   [Working with Segment and other unions](SCHEMA_GUIDE.md#35-working-with-segment-and-other-unions).
3. **Entry-point name** — the short name a model registers under, which need not match the
   class name. `building = "overture.schema.buildings:Building"` registers the class
   `Building` under the name `building`.

### Entry point

The mechanism by which a package advertises something to the rest of the installed
environment, declared in `pyproject.toml`. Nothing imports these directly; they are
discovered at runtime. The schema uses four groups: `overture.models` (feature types),
`overture.tag_providers` ([tags](#tag)), `project.scripts` (the CLIs), and `pytest11`
(test plugins). Registering your own model is a matter of adding an entry point — see
[Register your own feature types](SCHEMA_GUIDE.md#83-register-your-own-feature-types).

### Workspace

One repository containing several independently-versioned packages that share a single
lockfile and a single virtual environment. Declared by `[tool.uv.workspace]` in the root
`pyproject.toml`. The schema repo is a `uv` workspace of thirteen packages. See
[What "workspace" means](SCHEMA_GUIDE.md#what-workspace-means).

### Metapackage

A package that ships no code of its own and exists only to depend on others.
`overture-schema` is one: installing it pulls in every theme. Its namespace root contains
nothing but a `py.typed` marker, which is why `from overture.schema import Building`
fails.

### Flat shape

The form a feature takes as a single record with no nesting of core properties — `id`,
`geometry`, `theme`, `type` and the rest all sitting at the same level. This is the shape
the Pydantic models use, and the shape Overture publishes in Parquet.
`model_validate()` expects it.

### Envelope

The GeoJSON form of a feature, where most properties are tucked under a `properties` key
alongside a top-level `type: "Feature"`. Distinct from the [flat shape](#flat-shape), and
the single most common source of confusion when validating: `model_validate()` rejects it,
`model_validate_json()` accepts it. See
[Two representations](SCHEMA_GUIDE.md#32-the-one-thing-to-understand-two-representations).

### Discriminated union

A union of models where one field's value decides which arm applies. `Segment` is
discriminated on `subtype`: `road` selects `RoadSegment`, `rail` selects `RailSegment`,
`water` selects `WaterSegment`. Pydantic uses the discriminator to pick an arm without
trying each in turn, which also makes validation errors point at the right model.

### NewType

A distinct type wrapping an existing one, used to give a plain value a name and a set of
constraints — `Id`, `CountryCodeAlpha2`, `LanguageTag`. At runtime the value is still a
`str`; the wrapper carries the validation rules and survives into the generated artifacts,
which is why it is preferred over a bare `str` with a `Field` constraint.

### ModelKey

The key type returned by `discover_models()`. Carries the model's entry-point `name`, its
`entry_point` string, and its [tags](#tag). Not a plain string, and not a tuple — code
that assumes either will break.

### Tag

A string attached to a model during discovery, classifying it orthogonally to its name —
`feature`, or `overture:theme=buildings`. Tags are what the CLI's `--tag` / `--filter` /
`--exclude` options select on. They are produced by *tag providers* registered on the
`overture.tag_providers` entry-point group; third parties can register their own. Eight
tags exist today: `feature`, `overture`, and one `overture:theme=*` per theme. `overture`
marks a model built on Overture's feature model — it subclasses `OvertureFeature` — which
a third party's own type can also be; it is not a claim that the type belongs to the
Overture schema.

### Spec

The target-independent description of a model produced by the codegen's extraction layer,
before any output format is chosen — `RecordSpec` for a model, `UnionSpec` for a
discriminated union, `FieldSpec` for a field, `EnumSpec` for an enum. Renderers consume
specs; they never touch Pydantic models directly. This split is what lets a new output
format be a new renderer rather than new extraction logic. See
[Write a new codegen target](SCHEMA_GUIDE.md#84-write-a-new-codegen-target).

### Extra

An optional dependency group declared under `[project.optional-dependencies]` and
installed with bracket syntax (`package[extra]`) or `uv sync --all-extras`. Distinct from
"extra fields", which is what `no_extra_fields` forbids on a model.
