# Tags: Extensible Model Grouping via Entry Points

Move model discovery into `system`, eliminating assumptions about Overture in
the process. Replace the hardcoded `namespace` concept (`"overture"`, `"annex"`)
and the `ModelKind` classifier with tags -- string labels derived by tag
providers. Tags become the filtering, grouping, and classification mechanism
for model discovery, driven by introspection and package metadata rather than
central coordination.

`system` provides generic tag-based grouping without understanding what any
particular tag means. Any package can register tag providers that classify
models without special support in the discovery layer.

## Purpose

Tags serve three roles:

- **CLI filtering**: select subsets of models for output and codegen
  (`--tag overture`, `--tag draft`)
- **Classification and endorsement**: distinguish features from extensions,
  mark models as vetted or approved by an authority
- **Marketplace taxonomy**: browse and classify models and extensions in a
  future extension catalog

These roles overlap -- a tag like `overture:theme=buildings` serves both
filtering and taxonomy. The design accommodates this overlap through
structured tags that encode both ownership and dimension (see Tag Format).

## Generalizing the Classifier

The `pydantic-extensions` branch introduces `ModelKind`, an enum that
classifies models by introspecting their type hierarchy:

```python
class ModelKind(str, Enum):
    OVERTURE_MODEL = "overture_model"
    EXTENSION_MODEL = "extension_model"
    BASE_MODEL = "base_model"
```

`ModelKind.of()` inspects a model and returns a fixed classification.
`discover_models` then hardcodes how each kind maps to namespace and theme:

```python
match ModelKind.of(model_class):
    case ModelKind.OVERTURE_MODEL:
        ns = "overture"
        theme = get_args(first_class.model_fields["theme"].annotation)[0]
    case ModelKind.EXTENSION_MODEL:
        ns = "extensions"
    case ModelKind.BASE_MODEL:
        ns = "annex"
```

This works for the current set of three categories but embeds assumptions
that limit extensibility:

- **Closed classification set.** Adding a new kind requires changing the enum
  and every `match` statement that consumes it. Third-party packages cannot
  introduce new classifications.
- **Overture-specific logic in discovery.** `OVERTURE_MODEL` detection depends
  on `OvertureFeature`, which lives in `core`. Discovery in `system` should
  not import from `core`.
- **Classification and discovery are coupled.** The `match` block maps kinds
  to structural fields (`namespace`, `theme`). The mapping is implicit and
  changes when the data model changes.

Tags generalize this. A tag provider does the same introspection work as
`ModelKind.of()` but returns tags instead of enum values:

| `ModelKind` | Equivalent tags | Provider location |
|---|---|---|
| `OVERTURE_MODEL` | `feature`, `overture` | `system`, `core` |
| `EXTENSION_MODEL` | `system:extension` | `system` |
| `BASE_MODEL` | *(no tag -- it's the default)* | -- |

The `feature` tag comes from `Feature` inheritance (checked in `system`).
The `overture` tag comes from `OvertureFeature` inheritance (checked in
`core`). These are separate providers because the concepts live in separate
packages -- `system` knows about `Feature` but not `OvertureFeature`.

The classification becomes open: any package can register a tag provider that
adds new classifications without modifying `system` or `core`. Discovery
consumes tags generically -- it does not understand what any tag means.

Theme stops being a structural field derived from model annotations inside
discovery. It becomes a tag (`overture:theme=buildings`) produced by a
provider in `core` that reads the model's `theme` field. Discovery sees
theme tags the same way it sees any other tag.

---

## Tag Format

Tags are strings following the pattern `[prefix:]key[=value]`:

- **Plain**: `overture`, `draft`, `feature`
- **Prefixed**: `system:extension` -- `:` separates ownership
- **Prefixed k/v**: `overture:theme=buildings`

`:` signals ownership and enables prefix reservation (see Privileged Packages
and Tag Reservation). `=` signals a dimension with a value (groupable via
`--group-by`). One level of each -- no nested colons or multiple `=` signs.

### Tag Limits

To prevent unbounded tag proliferation, tag providers should add O(1) tags
per model -- classifications and dimensional values, not open-ended lists.
Discovery warns when a model accumulates more than 16 tags after all
providers run. This is a diagnostic guard, not a hard limit; it catches
runaway providers without constraining legitimate use.

---

## Privileged Packages and Tag Reservation

### Prefix Reservation

Prefixed tags (`prefix:*`) are owned by specific packages. A privilege table
in `system` maps prefixes to the packages authorized to produce them:

```python
# overture.schema.system.privileges
RESERVED_PREFIXES: dict[str, set[str]] = {
    "system": {"overture-schema-system"},
    "overture": {"overture-schema-core"},
}
```

Discovery enforces this: when a tag provider adds a prefixed tag, the
provider's `entry_point.dist.name` must appear in the authorized set for
that prefix. Violations produce a warning and the tag is discarded.

The table is maintained in `system` and updated as the ecosystem grows. New
packages claim prefixes by submitting changes to this table.

### Plain Tag Reservation

Specific plain tags (no colon) can also be reserved:

```python
RESERVED_TAGS: dict[str, set[str]] = {
    "overture": {"overture-schema-core"},
    "feature": {"overture-schema-system"},
}
```

Same enforcement: only authorized packages may produce these tags via tag
providers. Unauthorized providers that attempt to add reserved tags see a
warning and discard.

This is the less-preferred mechanism. Reserving individual strings does not
scale -- every new reserved word requires an update to the table. Prefix
reservation (`overture:*` owned by `overture-schema-core`) covers open-ended
families of tags without per-tag coordination. Plain tag reservation handles
the small set of broad classifications where a prefix would add noise
without information.

### Why Prefix-Based Reservation

The alternative is flat reservation only -- reserve specific strings
(`overture`, `feature`, `extension`, `buildings`, `theme`) without prefix
semantics. Flat tags keep the `key=value` dimension, and they're shorter.
But making the prefix opaque has costs:

**Structured tags encode relationships that flat tags cannot.** With
`overture:theme=buildings`, `--group-by overture:theme` extracts the
dimension and groups by its values. With flat tags `theme` and `buildings`,
grouping requires sniffing for pairings -- "does this model have both
`theme` and `buildings`?" -- and the pairing is implicit. A model tagged
`theme`, `buildings`, `residential` is ambiguous: are `buildings` and
`residential` both theme values, or is `residential` a separate
classification?

**Tags serve both endorsement and discovery.** A flat `buildings` tag in a
marketplace context is ambiguous: does it mean "this package relates to
buildings" (taxonomy) or "this package is the endorsed buildings schema"
(endorsement)? `overture:theme=buildings` unambiguously signals taxonomy;
endorsement lives in a separate tag (`approved`).

**Multi-ecosystem support requires disambiguation.** When multiple
ecosystems share the discovery mechanism, prefixes prevent collision:
`overture:theme=buildings` and `acme:theme=industrial` coexist cleanly.
Flat `buildings` and `industrial` need external context to distinguish
their purpose.

**`system` benefits from prefixed tags internally.** `system:extension`
encodes both the authority (`system`) and the classification (`extension`).
If `system` uses prefixed tags but the external convention is flat, you have
two tag systems.

Prefix-based reservation is the primary mechanism. Flat reservation handles
the small set of unambiguous, high-frequency classifications where a prefix
would be pure noise (`overture`, `feature`).

---

## Phase 1: Tag Providers and Discovery

Tag providers are the mechanism from the start, not a later addition.
Discovery loads models, runs tag providers to derive tags, then filters.

### Data Model

`ModelKey` drops `namespace` and `theme`, gains `name`:

```python
@dataclass(frozen=True, slots=True)
class ModelKey:
    name: str              # entry point name
    class_name: str        # entry point value (module:Class)
    tags: frozenset[str]   # plain and structured tags
```

No `namespace` field, no `theme` field. Both are expressed as tags.

`name` is the `overture.models` entry point name. It serves as an identifier
for the package maintainer. CLI output and codegen paths use the class name
and module path (introspectable from the entry point value), not the entry
point key. Since `overture.models` keys have no functional role in the
system, the `name#tag1,tag2` syntax discussed in Deferred: Package Keywords
as Tag Source remains viable -- the `#` suffix would not affect any consumer.

(By contrast, `overture.tag_providers` entry point names carry rc.d-style
numeric prefixes that determine provider execution order -- see Provider
Mechanism.)

### Entry Point Format

Entry point keys are the model's name. The entry point group remains
`overture.models`.

```toml
[project.entry-points."overture.models"]
building = "overture.schema.buildings:Building"
building_part = "overture.schema.buildings:BuildingPart"
```

Tags come from tag providers. Providers can introspect model classes,
package metadata, and entry point attributes to derive tags (see Deferred:
Package Keywords as Tag Source for an example).

### Provider Mechanism

A new entry point group `overture.tag_providers` registers callables. The
entry point name determines execution order using rc.d-style numeric prefixes
(`10_feature`, `50_overture`, `90_approved`).

Provider signature:

```python
(model_class: type[BaseModel], key: ModelKey, tags: set[str]) -> set[str]
```

Providers receive the accumulated tag set and return a (potentially modified)
set. Tags accumulate across providers: each provider sees the result of all
prior providers. The caller copies the set before passing it to each provider
and diffs the copy against the return value to detect additions and removals.
Providers can remove tags added by earlier providers.

Only providers from packages authorized in the privilege table may add
reserved tags or prefixed tags. Discovery enforces this by checking
`entry_point.dist.name` against the privilege table after each provider runs.

**Ordering**: numeric prefixes on entry point names determine execution order.
Published guidance defines priority ranges:

- 0-19: structural tags (`feature`, `system:extension` in Phase 2)
- 20-49: derived classifications (`overture`)
- 50-79: taxonomy tags (`overture:theme=buildings`)
- 80-99: approval/policy tags (`approved`)

Ranges are illustrative -- actual boundaries TBD.

### Built-in Tag Providers

**`feature` provider** (in `system`, priority 10):

Classifies models that derive from `Feature` (`overture.schema.system.feature`).
This is the generic base class for all feature models; `OvertureFeature`
extends it in `core`.

```toml
# packages/overture-schema-system/pyproject.toml
[project.entry-points."overture.tag_providers"]
"10_feature" = "overture.schema.system.tags:feature_provider"
```

```python
from overture.schema.system.feature import Feature

def feature_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    if isinstance(model_class, type) and issubclass(model_class, Feature):
        tags.add("feature")
    return tags
```

**`overture` provider** (in `core`, priority 50):

Classifies models that derive from `OvertureFeature`.

```toml
# packages/overture-schema-core/pyproject.toml
[project.entry-points."overture.tag_providers"]
"50_overture" = "overture.schema.core.tags:overture_provider"
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

This provider does NOT add `overture:theme=X` -- theme is a separate
provider (also in `core`) that reads the model's `theme` field annotation.

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

When `tags` is provided, any-match semantics apply: models whose effective
tags intersect the filter set are included. When `None`, all models are
returned.

Implementation:

1. Iterate `overture.models` entry points
2. Load the model class via `entry_point.load()`
3. Load all `overture.tag_providers` entry points, sorted by key
4. For each model, run each provider in order: copy the current tag set,
   call the provider, diff the result, enforce the privilege table
5. Warn if a model exceeds 16 tags
6. Freeze final `set[str]` into `frozenset[str]` on `ModelKey`, apply
   filter, return

### CLI

`--namespace`, `--overture-types`, and `--theme` are removed. Replaced by:

- `--tag <tag>` (repeatable, OR semantics)
- `--group-by <key>` -- group output by values of matching
  `[prefix:]key=*` tags

Repeated `--tag` flags use OR: `--tag foo --tag bar` matches models with
either tag.

`list-types` with `--group-by` groups by the specified tag key and displays
tags per model:

```
$ overture-schema list-types --group-by overture:theme

buildings
  building          overture, feature
  building_part     overture, feature, draft

places
  place             overture, feature

(ungrouped)
  sources           overture
```

Models without a matching tag appear in "(ungrouped)".

`--group-by` is generic: `--group-by acme:category` works if packages
register tag providers that produce `acme:category=widgets` tags. Default
behavior (no `--group-by`): flat list with tags column.

### Migration

Existing `namespace:theme:type` entry points become just the type name. The
`namespace` and `theme` fields are removed from `ModelKey`. Theme moves to a
tag provider in `core` that reads model field annotations. The `overture`
namespace becomes a derived tag from `OvertureFeature` inheritance. The
`annex` namespace has no equivalent; annex packages either register their
own tag providers or rely on generic classification.

### What Moves

- `discover_models`, `ModelKey` move to `overture.schema.system.discovery`
- Tag provider infrastructure, privilege table live in `system`
- `feature` provider lives in `system` (`extension` provider added in Phase 2)
- `overture` and theme providers live in `core`
- Tag parsing helpers (`tags_by_key`, `tags_by_namespace`) live in `system`
- CLI imports from `system` directly

---

## Phase 2: Extension Support

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
"15_extensions" = "overture.schema.system.tags:extension_provider"
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
The `system:extension` tag is derived automatically; authors never declare it.

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
  building              overture, feature
    + capacity, operating-hours
  building_part         overture, feature, draft

places
  place                 overture, feature
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
building    overture, feature, overture:theme=buildings

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

## Phase 3: Manifest-Driven Approval (Sketch)

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
"90_approved" = "overture.schema.official_extensions:approved_provider"
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

## Deferred: Package Keywords as Tag Source

Package keywords (`[project].keywords` in `pyproject.toml`) are a natural
source of tags -- they're part of Python distribution metadata and appear in
PyPI search. The initial design derives all tags from tag providers, but a
provider could surface keywords as tags:

```python
def keyword_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    # Requires access to distribution metadata via entry point or enriched key
    dist = _get_distribution(key)
    for kw in dist.metadata.get_all("Keyword", []):
        kw = kw.strip()
        if kw and not _is_reserved(kw):
            tags.add(kw)
    return tags
```

This is deferred because tag providers handle the initial use cases
(classification, theme, extensions) without requiring package authors to
declare keywords. Keywords become useful when:

- Third-party packages want to self-declare tags without writing a provider
- A catalog needs author-supplied taxonomy tags beyond what introspection
  can derive

The provider above needs access to distribution metadata through `ModelKey`
or a separate context object -- the current `ModelKey` does not carry this.
Adding it is straightforward when the need arises.

Note: `[project].keywords` is also used for PyPI search, so schema tags and
PyPI keywords share a namespace. In practice, schema-relevant keywords and
PyPI discoverability keywords overlap naturally.

---

## Security Roadmap

The privilege model is convention-based. The privilege table checks
`entry_point.dist.name`, which any package can spoof by naming itself
`overture-schema-system`. This prevents accidental claims, not adversarial
ones.

This is acceptable for the current stage. The Python packaging ecosystem
provides a path to stronger guarantees when needed:

- **Trusted Publishers** (PyPI): ties package uploads to specific CI/CD
  identities (GitHub Actions OIDC), preventing unauthorized releases of
  known package names. Already available on PyPI.
- **Provenance attestations** (PEP 740): Sigstore-based build provenance
  lets consumers verify that a package was built from a specific source
  repository by a specific workflow. PyPI supports this today for packages
  using Trusted Publishers.
- **Repository-based classification**: `[project.urls]` metadata carries
  source repository URLs. A future tag provider could use verified
  provenance to classify packages by origin repository -- e.g., packages
  built from the `OvertureMaps/schema` repo get `core` status, packages
  from `OvertureMaps/schema-extensions` get `vetted` status.

The privilege table's interface stays the same as enforcement strengthens;
only the verification backend changes. Convention-based enforcement upgrades
to cryptographic enforcement without changing tag semantics.
