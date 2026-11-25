# Glossary

Use this page to look up a term. Each definition is a sentence or two. The terms come in
three groups: the map data, such as entity, feature and feature type; the Python packages
that define the schema, such as workspace and entry point; and building on the schema,
such as extension schema, extension dataset and GERS Extension. For the reasons behind a
term, see [Concepts](concepts.md).

Terms in the second group are cross-referenced to the page and section that covers them
in full: [the schema guides](README.md) for using the schema,
[Writing models](writing-models.md) for extending it, and [Concepts](concepts.md) for
background.

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

The feature type within a theme, and a mandatory property on every feature, for example
`theme=buildings`, `type=building`. Together `theme` and `type` identify the feature type.

### Subtype

An optional third property that further refines the feature type, for example
`theme=transportation`, `type=segment`, `subtype=road`. Where a type has subtypes, the
model for that type is usually a [discriminated union](#discriminated-union) with one model
per subtype. Note the spelling: the field is `subtype`, not `subType`.

### GERS

The Global Entity Reference System. A feature's `id` may be a GERS ID if, and only if,
the feature represents an entity that is part of GERS.

---

## Toolchain

### Alias

Three unrelated things in this codebase go by this name. Which one is meant is almost
always clear from context, but they're different:

1. **Field alias**: a mapping from a Python attribute name to the name the data uses,
   declared with `Field(alias=...)`. It exists because some data field names are not legal
   Python identifiers: `Building.class_` has `alias="class"`, since `class` is a
   reserved word. Dump with `by_alias=True` to get the data name back.
2. **Type alias**: a module-level name bound to a type expression rather than to a class.
   `Segment` is one: it is an `Annotated[Union[...], Discriminator(...)]`, *not* a class.
   This is why `Segment.model_validate(...)` raises `AttributeError` and you need
   `TypeAdapter(Segment).validate_python(...)` instead. See
   [Working with Segment and other unions](working-with-features.md#working-with-segment-and-other-unions).
3. **Entry-point name**: the short name a model registers under, which need not match the
   class name. `building = "overture.schema.buildings:Building"` registers the class
   `Building` under the name `building`.

### Entry point

The mechanism by which a package advertises something to the rest of the installed
environment, declared in `pyproject.toml`. Nothing imports these directly; they are
discovered at runtime. The schema uses four groups: `overture.models` (feature types),
`overture.tag_providers` ([tags](#tag)), `project.scripts` (the CLIs), and `pytest11`
(test plugins). Registering your own model is a matter of adding an entry point. See
[Register your own feature types](writing-models.md#package-and-register-your-models).

### Workspace

One repository containing several independently-versioned packages that share a single
lockfile and a single virtual environment. Declared by `[tool.uv.workspace]` in the root
`pyproject.toml`. The schema repo is a `uv` workspace of thirteen packages. You only work
with the workspace when you install from a clone. See
[The uv workspace](concepts.md#the-uv-workspace).

### Metapackage

A package that ships no code of its own and exists only to depend on others.
`overture-schema` is one: installing it pulls in all six themes, the validation
functions, and the CLI. It doesn't pull in `overture-schema-codegen` or
`overture-schema-pyspark`. Its namespace root contains nothing but a `py.typed` marker, which is why `from overture.schema import Building`
fails.

### Flat shape

The form a feature takes as a single record with no nesting of core properties: `id`,
`geometry`, `theme`, `type` and the rest are all at the same level. This is the shape
the Pydantic models use, and the shape Overture publishes in Parquet.
`model_validate()` expects it. Individual properties can still have nested values, such
as `names` or `sources`. "Flat" means only that there's no GeoJSON envelope.

### Envelope

The GeoJSON form of a feature, where most properties are tucked under a `properties` key
alongside a top-level `type: "Feature"`. Distinct from the [flat shape](#flat-shape), and
the most common source of confusion when validating: `model_validate()` rejects it,
`model_validate_json()` accepts it. See
[Two representations](working-with-features.md#two-representations).

### Discriminated union

A union of models where one field's value decides which model applies. `Segment` is
discriminated on `subtype`: `road` selects `RoadSegment`, `rail` selects `RailSegment`,
`water` selects `WaterSegment`. Pydantic uses the discriminator to pick a model without
trying each in turn, which also makes validation errors point at the right model.

### NewType

A distinct type wrapping an existing one, used to give a plain value a name and a set of
constraints, such as `Id`, `CountryCodeAlpha2`, and `LanguageTag`. At runtime the value is still a
`str`; the wrapper has the validation rules and survives into the generated artifacts,
which is why it is preferred over a bare `str` with a `Field` constraint.

### ModelKey

The key type that `discover_models()` returns. It has the model's entry-point `name`, its
`entry_point` string, and its [tags](#tag). Not a plain string, and not a tuple. Code
that assumes either will break.

### Tag

A string attached to a model during discovery, classifying it orthogonally to its name, such as
`feature` or `overture:theme=buildings`. Tags are what the CLI's `--tag` / `--filter` /
`--exclude` options select on. They are produced by *tag providers* registered on the
`overture.tag_providers` entry-point group; third parties can register their own. Eight
tags exist today: `feature`, `overture`, and one `overture:theme=*` per theme. `overture`
marks a model built on Overture's feature model, meaning it subclasses `OvertureFeature`, which
a third party's own type can also be; it is not a claim that the type belongs to the
Overture schema.

### Spec

The target-independent description of a model produced by the codegen's extraction layer,
before any output format is chosen: `RecordSpec` for a model, `UnionSpec` for a
discriminated union, `FieldSpec` for a field, `EnumSpec` for an enum. Renderers consume
specs; they never touch Pydantic models directly. This split is what lets a new output
format be a new renderer rather than new extraction logic. See
[Write a new codegen target](../packages/overture-schema-codegen/docs/adding-a-target.md).

### Extra

An optional dependency group declared under `[project.optional-dependencies]` and
installed with bracket syntax (`package[extra]`) or `uv sync --all-extras`. Distinct from
"extra fields", which is what `no_extra_fields` forbids on a model.

### Spark schema

A description of the columns in a Spark DataFrame: each column's name, its type, and
whether it can be null. Spark calls this object a `StructType`. `overture-schema-pyspark`
generates one for each feature type from the Pydantic models. `overture-validate` compares
your data's columns with it before checking values, and you can pass it to
`spark.read.schema(...)` so Spark reads data with the expected types. See
[PySpark expressions and Spark schemas](generating-other-formats.md#pyspark-expressions-and-spark-schemas).

---

## Extensions

These terms describe how others build on the schema. The Schema Working Group set them in
October 2026. Terms still under discussion, such as a name for adding new feature types,
aren't listed here yet.

### Schema

A packaged Pydantic definition of one or more models. The reference schema, extension
schemas, and GERS extension schemas are all schemas. "Package" by itself still means a
Python package, the unit you install.

### Reference schema

The schema Overture publishes and maintains: the models in this repository's
`overture-schema-theme-*` packages.

### Reference data

The data Overture releases against the reference schema. Data belongs in the reference
only if it describes entities in a theme Overture identifies with [GERS](#gers), matters
for assigning IDs and matching, and is, or has a realistic path to becoming, a commodity.
A few exceptions, such as operating status, are in the reference anyway. Anything else can
be a [GERS Extension](#gers-extension) or a [supplemental dataset](#supplemental-dataset).

### Extension schema

A schema that adds properties to a model it doesn't own.

### GERS extension schema

An extension schema that adds properties to GERS-enabled feature types in the reference
schema, either directly or by extending another GERS extension schema. Example: GEM
structural properties.

### Extension dataset

Data published against an extension schema. One schema can have many extension datasets.

### GERS extension dataset

An extension dataset keyed on GERS IDs. Example: GATIS has one schema, with a dataset for
Philadelphia and another for Prague.

### GERS Extension

A GERS extension schema together with the GERS extension datasets listed against it.
GERS Extensions add columns to reference features, not rows. Example: postal codes on
divisions.

### Candidate GERS Extension

A GERS extension schema with no listed data yet. Example: operating hours.

### Supplemental dataset

Any data that isn't reference data or an extension dataset. That includes more features
of a type the reference already defines, and data for new feature types. Overture doesn't
validate or endorse supplemental datasets.

New feature types aren't GERS Extensions, even when their properties reference GERS IDs.

### Extensions framework

The tooling for extension schemas. Today it covers adding properties only. Adding new
models uses the existing [entry-point](#entry-point) discovery mechanism. See
[Register your own feature types](writing-models.md#package-and-register-your-models).

### Retired terms

Don't use "bundle," "type extension," or "private package." "Type extension" collides with
scalar extensions (`Extends(...)`) in the schema library. "Private" is a state, not a kind
of package: a schema that isn't listed.

---

## Next steps

If you want to know why a term exists, and not only what it means, read
[Concepts](concepts.md). To see the terms in use, follow
[the schema guides](README.md). To suggest a term or a better definition, post in
[GitHub Discussions](https://github.com/orgs/OvertureMaps/discussions).
