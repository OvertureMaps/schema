# Tags: Extensible Model Grouping via Entry Points

Replace the hardcoded `namespace` concept (`"overture"`, `"annex"`) with tags --
string labels declared by package authors and derived by tag providers. Tags
become the filtering and grouping mechanism for model discovery, driven by
package authors rather than central coordination.

Theme becomes a tag (`overture:theme=buildings`), not a structural field.
`system` provides generic key-based grouping without understanding what
"theme" means. Any package can declare theme tags (or any other structured
tag) without special support in the discovery layer.

## Phase 1: Structured Tags

Replace namespace with tags, move discovery to `system`, update CLI.

### Tag Format

Tags are strings following the pattern `[namespace:]key[=value]`:

- **Plain**: `overture`, `draft`
- **Namespaced**: `system:extension` -- `:` separates ownership/reservation
- **Namespaced k/v**: `overture:theme=buildings`, `codegen:schema_root=overture.schema`

`:` signals ownership/reservation. `=` signals a dimension with a value
(groupable via `--group-by`). One level of each -- no nested colons or
multiple `=` signs.

### Data Model

`ModelKey` drops `namespace` and `theme`, gains `name`:

```python
@dataclass(frozen=True, slots=True)
class ModelKey:
    name: str              # friendly name from entry point key
    class_name: str        # entry point value (module:Class)
    tags: frozenset[str]   # plain and structured tags
```

No `namespace` field, no `theme` field. Both are tags.

`name` is the entry point key (before any `#` suffix). It serves as the
model's friendly identifier in CLI output and codegen path generation.

### Entry Point Format

Entry point keys are `name` or `name#tag1,tag2`. No `theme:type` prefix --
theme is a package-level keyword. The entry point group remains
`overture.models`.

```toml
[project]
keywords = ["overture:theme=buildings"]

[project.entry-points."overture.models"]
building = "overture.schema.buildings:Building"
"building_part#draft" = "overture.schema.buildings:BuildingPart"
```

A model's tags are the union of:

- `[project].keywords` from the distribution metadata (read via
  `entry_point.dist.metadata["Keywords"]`)
- Per-model `#` tags from the entry point name
- Tag providers (Phase 2)

Note: `[project].keywords` is also used for PyPI search, so schema tags and
PyPI keywords share a namespace. This was considered and accepted -- in
practice, schema-relevant keywords and PyPI discoverability keywords overlap
naturally, and the `#` per-model mechanism covers cases where finer control is
needed.

### Tag Prefix Reservation

The `system:` prefix is reserved for tag providers registered by
`overture-schema-system`. Discovery rejects author-declared tags (keywords
and `#`) that start with `system:`. Static sources containing `system:*` tags
produce an error (or warning + discard).

All other prefixes are convention-based with no enforcement.

### Tag Parsing Helpers

`system` provides utilities for working with structured tags:

```python
def tags_by_key(tags: frozenset[str], key: str) -> set[str]:
    """Extract values for k/v tags with the given key.

    tags_by_key(frozenset({"overture:theme=buildings", "overture", "draft"}), "overture:theme")
    -> {"buildings"}
    """

def tags_by_namespace(tags: frozenset[str], namespace: str) -> set[str]:
    """Extract tag bodies within a namespace.

    tags_by_namespace(frozenset({"system:extension", "overture"}), "system")
    -> {"extension"}
    """
```

`tags_by_key` is the primitive that CLI `--group-by` and codegen path
generation build on. Both live in `system` alongside `ModelKey`.

### Discovery

`discover_models` and `ModelKey` move to `overture.schema.system.discovery`:

```python
def discover_models(tags: set[str] | None = None) -> dict[ModelKey, type[BaseModel]]:
```

When `tags` is provided, any-match semantics apply: models whose effective tags
intersect the filter set are included. When `None`, all models are returned.

Implementation:

1. Iterate `overture.models` entry points
2. Split name on `#` to separate `name` from per-model tags
3. Load the model class via `entry_point.load()`
4. Read `entry_point.dist.metadata["Keywords"]` for package-level tags
5. Union package tags and per-model tags, rejecting any `system:*` tags
6. Run tag providers (Phase 2)
7. Build `ModelKey(name=name, class_name=entry_point.value, tags=frozenset(tags))`

### CLI

`--namespace`, `--overture-types`, and `--theme` are removed. Replaced by:

- `--tag <tag>` (repeatable, OR within tags, AND across other dimensions)
- `--group-by <key>` -- group output by values of matching `[ns:]key=*` tags

Repeated `--tag` flags use OR: `--tag foo --tag bar` matches models with
either tag.

`list-types` with `--group-by` groups by the specified tag key and displays
tags per model:

```
$ overture-schema list-types --group-by overture:theme

buildings
  building          overture
  building_part     overture, draft

places
  place             overture

(ungrouped)
  sources           overture
```

Models without a matching tag appear in "(ungrouped)".

`--group-by` is generic: `--group-by acme:category` works if packages use
`acme:category=widgets` tags. Default behavior (no `--group-by`): flat list
with tags column.

### Migration

Existing `namespace:theme:type` entry points become `name` (just the type
name). The `namespace` and `theme` fields are removed from `ModelKey`. Theme
moves to `overture:theme=X` in `[project].keywords` on each theme package.

The `overture` namespace does not need replacement as a keyword or `#` tag --
Phase 2 introduces a tag provider in `core` that derives the `overture` tag
from `OvertureFeature` inheritance. The `annex` namespace has no equivalent;
annex packages either declare their own keywords or rely on tag providers.

### What Moves

- `discover_models`, `ModelKey` move to `overture.schema.system.discovery`
- Tag parsing helpers (`tags_by_key`, `tags_by_namespace`) live in `system`
- CLI imports from `system` directly

---

## Phase 2: Tag Providers

Derived tags from model introspection. The `overture` tag (currently a hardcoded
namespace) becomes a derived tag produced by a provider in `core`.

### Provider Mechanism

A new entry point group `overture.tag_providers` registers callables. The entry
point key is informational (describes the provider's purpose) and not
interpreted by discovery.

Provider signature:

```python
(model_class: type[BaseModel], key: ModelKey, tags: set[str]) -> set[str]
```

Providers receive the accumulated tag set and return a tag set (either the
same object mutated or a new set). Tags accumulate across providers: each
provider sees the result of all prior providers plus the static tags. The
caller copies the set before passing it to each provider and diffs the copy
against the return value to detect additions and removals. Providers can
remove static tags (from keywords and `#`) and tags added by earlier
providers.

**Unresolved: provider ordering.** Since providers chain, execution order
affects results. Leading candidate: alphabetical by entry point name with
rc.d-style numeric prefixes (`10_extensions`, `50_overture`, `90_approved`).
Since the entry point key is informational, providers self-register their
ordering. Published guidance would define what the priority ranges mean (e.g.,
0-19 for structural tags, 20-49 for derived tags, 50-79 for classification,
80-99 for approval/policy). Ranges are illustrative -- actual boundaries TBD.

Providers run after static tag resolution, before filtering. Only tag
providers registered by `overture-schema-system` may add `system:`-prefixed
tags. Discovery enforces this by checking `entry_point.dist.name` before
accepting `system:` additions. This is a convention boundary, not a security
mechanism -- any package could name itself `overture-schema-system`. It
prevents accidental `system:` claims from third-party providers and
ecosystem-specific packages (like `core`).

### Two-Phase Discovery

With tag providers, `discover_models` becomes:

1. **Load phase**: load models, resolve static tags (keywords + `#`)
2. **Enrich phase**: load all `overture.tag_providers` entry points, run each
   provider (passing a copy of the current tags), diff input/output to detect
   changes, enforce `system:` prefix rules
3. Freeze final `set[str]` tags into `frozenset[str]` on `ModelKey`, apply
   filter, return

### The `overture` Tag Provider

Lives in `core`, registered as an entry point:

```toml
# packages/overture-schema-core/pyproject.toml
[project.entry-points."overture.tag_providers"]
overture = "overture.schema.core.tags:overture_provider"
```

```python
from overture.schema.core import OvertureFeature

def overture_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    if isinstance(model_class, type) and issubclass(model_class, OvertureFeature):
        tags.add("overture")
    return tags
```

This provider does NOT add `overture:theme=X` -- theme comes from package
keywords. The provider adds only the flat `overture` tag based on
inheritance.

Theme packages do not need `"overture"` in `[project].keywords`. The tag is
derived from `OvertureFeature` inheritance by this provider.

---

## Phase 3: Extension Support

Layer extension registration and discovery onto the tagging system. The
extension mechanism itself (how extensions modify or compose with base models)
is TBD and designed separately. This phase builds on Roel's proposal but that
design is still subject to change. What follows covers registration, discovery,
and CLI display only.

### Extension Primitives

`@extends` decorator and `Extends()` annotation move from `core` to
`overture.schema.system`. These declare that a model augments one or more base
models:

```python
@extends(Building, Place)
class OperatingHours(BaseModel):
    hours: ...
    timezone: ...
```

Or as a `NewType` with annotation:

```python
OperatingHours = Annotated[OperatingHoursModel, Extends(Building, Place)]
```

### Extension Tag Provider

Lives in `system`, registered as an entry point:

```toml
# packages/overture-schema-system/pyproject.toml
[project.entry-points."overture.tag_providers"]
extensions = "overture.schema.system.tags:extension_provider"
```

```python
def extension_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    if extends_classes(model_class):
        tags.add("system:extension")
    return tags
```

Package authors register extensions as regular `overture.models` entry points.
Extensions follow the same naming rules as other models: `name` or
`name#tag1,tag2`. The `system:extension` tag is derived automatically; authors
never declare it.

### Extension Discovery Helper

Extensions declare which base models they augment (via `@extends` /
`Extends()`), but callers typically need the reverse: given a base model, which
extensions apply to it? A convenience function in `system` builds this reverse
mapping:

```python
def extension_graph(
    models: dict[ModelKey, type[BaseModel]],
) -> dict[type[BaseModel], list[type[BaseModel]]]:
    """Map base models to the extensions that apply to them."""
```

Filters `models` for the `system:extension` tag, calls `extends_classes()` on
each to get its declared base models, and inverts the relationship. The CLI
uses this to show registered extensions alongside the models they extend
without reimplementing the traversal.

### CLI Display

The CLI treats `system:extension` as a presentation hint:

**`list-types`**: extensions appear in a separate section listing which models
they extend. Core models show a compact cross-reference to available extensions.

```
$ overture-schema list-types --group-by overture:theme

buildings
  building              overture
    + capacity, operating-hours
  building_part         overture, draft

places
  place                 overture
    + operating-hours

extensions
  capacity              system:extension
    extends: building
  operating-hours       system:extension
    extends: building, place
```

**`describe-type` on a core model**: includes a "Registered extensions" section
after the model's own fields.

```
building    overture, overture:theme=buildings

  Fields:
    geometry    Geometry
    subtype     BuildingSubtype | None
    ...

  Registered extensions:
    capacity          max_occupancy, floor_area, ...
    operating-hours   hours, timezone, ...
```

**`describe-type` on an extension**: shows which models it extends and full
field definitions.

---

## Phase 4: Manifest-Driven Approval (Sketch)

A tag provider that checks models against a curated manifest, enabling
organizations to certify which models (and extensions) they endorse.

### Concept

A tag provider reads a manifest of approved entries and adds an approval tag
to matching models. This lets an organization certify models without requiring
changes to the model packages themselves.

### Shape

The manifest lives in a dedicated package (e.g.,
`overture-schema-official-extensions`) that depends on nothing but `system`.
It registers a tag provider:

```toml
# packages/overture-schema-official-extensions/pyproject.toml
[project.entry-points."overture.tag_providers"]
approved = "overture.schema.official_extensions:approved_provider"
```

The manifest can match against class names (entry point values), entry point
names, and/or package names with optional version specifiers. Package names
are harder to collide than class names, making them a stronger identifier for
third-party extensions.

```python
APPROVED = {
    # by class name
    "overture.schema.buildings:Building",
    "overture.schema.buildings:BuildingPart",
    # by package name (with optional version specifier)
    "acme-schema-parcels>=1.0",
}

def approved_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    if _matches_manifest(key):
        tags.add("approved")
    return tags
```

Note: `approved` is an unprefixed tag (not `system:approved`) since this
provider lives outside `system`.

Note: `_matches_manifest` needs more than `ModelKey` to match against package
names. `ModelKey` carries `class_name` (the entry point value) but not the
distribution/package name. The provider will need access to additional context
(e.g., the entry point object itself, or an enriched key). The right mechanism
is TBD.

### Use Cases

- **Overture release certification**: only models in the manifest are tagged
  `approved` for a given release. The manifest package is versioned alongside
  the release.
- **Organizational policy**: a company publishes their own manifest package
  with their own approved set (including approved extensions).
- **CLI filtering**: `--tag approved` shows only certified models.

---

## Appendix: Codegen Path Generation

Two strategies depending on whether a type has an entry point.

### Feature Models (have entry points and tags)

`tags_by_key(key.tags, "overture:theme")` provides the theme directory
(omitted if absent). `to_snake_case(spec.name)` provides the subdirectory and
filename.

```
{theme}/{slug}/{slug}.md       # with theme tag
{slug}/{slug}.md               # without theme tag
```

No module path involved for features.

### Supplementary Types (no entry points)

Module prefix stripping replaces theme-tag matching for path generation.

**`schema_root` resolution** (checked in order):

1. **Explicit tag**: `codegen:schema_root=overture.schema` in package keywords
2. **Tag provider**: `core` registers a provider that adds
   `codegen:schema_root=overture.schema` to models from Overture packages
3. **Heuristic**: compute common prefix of module paths across the entry
   point group (the `compute_schema_root()` fallback)

**Path algorithm** for any type:

1. Resolve `schema_root` for the type's distribution
2. Get `__module__`, strip `{schema_root}.` prefix
3. Walk remaining components, keep only packages
   (`hasattr(mod, '__path__')`) -- drops file-level modules
4. Result is the directory path

| `__module__` | Root | After strip | Pkg-filtered | Path |
|---|---|---|---|---|
| `o.s.divisions.division.models` | `overture.schema` | `divisions.division.models` | `divisions.division` | `divisions/division/` |
| `acme.widgets.places.models` | `acme.widgets` | `places.models` | `places` | `places/` |
| `acme.widgets.places.restaurants.types` | `acme.widgets` | `places.restaurants.types` | `places.restaurants` | `places/restaurants/` |

Then the existing nesting logic decides: single-feature reference nests under
that feature; multi-feature reference stays at theme/intermediate level.

### Core/System Types

Uses the same `schema_root` + package-filter algorithm. With
`schema_root=overture.schema`, a type in `overture.schema.core.cartography`
yields path `core/` (if `cartography` is a file) or `core/cartography/`
(if promoted to a package).

The hardcoded `_SUBSYSTEM_MAP` exists because file-level modules lose
path significance when filtered. Promoting meaningful modules (like
`cartography.py`) to packages eliminates the map -- a code organization
change noted as follow-up work.

`compute_schema_root()` and `_SCHEMA_PREFIX` are replaced by the
`schema_root` tag.
