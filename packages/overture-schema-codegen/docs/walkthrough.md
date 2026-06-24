# Walkthrough: overture-schema-codegen

Pydantic's serialization machinery destroys the vocabulary that documentation needs. The
codegen recovers it.

Consider the transportation theme's `Segment` type -- a discriminated union of
`RoadSegment`, `RailSegment`, and `WaterSegment`. All three share fields inherited from
`TransportationSegment`. Each adds variant-specific fields. The discriminator field
`subtype` carries a `Literal` value (`"road"`, `"rail"`, `"water"`) that selects the
arm. Call `model_json_schema()` and the union collapses into an `anyOf` array with
duplicated field definitions, the discriminator mapping disappears, and the common-base
relationship between variants is unrecoverable.

The same loss happens at the field level. `FeatureVersion = NewType("FeatureVersion",
int32)` where `int32 = NewType("int32", Annotated[int, Field(ge=0, le=2147483647)])`
becomes `{"type": "integer", "minimum": 0, "maximum": 2147483647}`. Three things
vanished: the name "FeatureVersion," the name "int32," and the fact that `ge=0` came
from the `int32` layer rather than `FeatureVersion`. Custom constraint classes like
`GeometryTypeConstraint` lose their identity -- the class name, its docstring, and its
relationship to a specific NewType dissolve into anonymous JSON Schema keywords.

Documentation needs all of this. The codegen exists to preserve it.

Navigating Python's type annotation machinery -- NewType chains, nested `Annotated`
wrappers, union filtering, generic resolution -- is complex. The codegen does it once.
`analyze_type()` unwraps annotations into `FieldShape`, a tree-shaped target-independent
representation. Extractors build specs from these shapes. Renderers consume specs without
re-entering the type system. New output targets add renderers, not extraction logic.

The solution decomposes into four layers. Discovery finds models. Extraction unwraps
them into flat specifications. Output Layout decides what to generate and where it goes.
Rendering formats the output. Imports flow strictly downward -- no layer references the
one above it.

Sixteen sections follow, ordered by dependency: each module appears before anything that
imports it. The final section inverts this and traces the full pipeline top-down.
Segment threads through as the primary example, since its path through the system --
union classification, common base discovery, variant field partitioning, discriminator
extraction, tagged rendering -- exercises more of the pipeline than any model feature
does.

---

## 1. Discovery

The pipeline starts in `overture-schema-common`, not in the codegen package itself.
`discover_models()` calls `importlib.metadata.entry_points(group="overture.models")` and
loads every registered model. Each entry point name encodes identity as a
colon-delimited triple (`overture:buildings:building`); each value encodes the Python
location (`overture.schema.buildings:Building`). The function parses both formats --
three-part names carry a theme component, two-part names set theme to `None` -- and
returns `dict[ModelKey, type[BaseModel]]`.

`ModelKey` is a frozen dataclass with four fields: `namespace`, `theme`, `type`, and
`entry_point`. The `entry_point` field preserves the raw `module:Class` string that
downstream modules split to determine output directory structure.

The return dict includes both concrete `BaseModel` subclasses and type aliases.
`Building` is a concrete class -- `isinstance(Building, type)` returns true. `Segment`
is not. It is an `Annotated` alias wrapping `Union[RoadSegment, RailSegment,
WaterSegment]` with a discriminator field. `isinstance` and `issubclass` cannot inspect
it. The entry point `overture:transportation:segment` maps to
`overture.schema.transportation:Segment`, which loads the alias itself.

The codegen classifies these at the CLI boundary: `is_model_class` identifies concrete
`BaseModel` subclasses, `is_union_alias` calls `analyze_type` to identify discriminated
unions. From that point forward both records and unions are `ModelSpec` values
(`RecordSpec | UnionSpec`) and flow through the same pipeline.

## 2. Leaf utilities

One module with no internal dependencies, serving multiple layers. PascalCase to
snake_case conversion lives in `overture.schema.system.case` (used by the pyspark
generator and the markdown path assignment); markdown output filenames are
`f"{to_snake_case(name)}.md"` at the call site.

### extraction/docstring.py

Distinguishes author-written docstrings from auto-generated ones. Both `Enum` and
`NewType` produce default docstrings that vary across Python versions. Rather than
hardcoding version-specific strings, the module creates temporary instances at import
time, captures their `__doc__` attributes, then deletes the instances:

```python
class _DocstringProbeEnum(Enum):
    pass

_ENUM_DEFAULT_DOCSTRING = _DocstringProbeEnum.__doc__
del _DocstringProbeEnum
```

`is_custom_docstring` compares a given docstring against these captured defaults and an
optional inherited docstring. The enum extractor uses this both at class level and
per-member, since `DocumentedEnum` members carry individual `__doc__` attributes.

`clean_docstring` delegates to `inspect.cleandoc` and returns `None` for empty results.
`first_docstring_line` takes the first line only -- used by renderers that show
summaries.

## 3. Type analysis

This is the module the entire package exists to house. `analyze_type` takes a raw type
annotation and returns `tuple[FieldShape, bool, str | None]` -- the structural shape,
whether the field is optional, and the first description found in the annotation chain.
`FieldShape` is a discriminated union tree that fully describes the type without any
reference to Python's typing machinery.

### The recursion

`_unwrap` peels one annotation layer per call frame and returns a `FieldShape` subtree.
Each case handles one wrapper kind:

**NewType** constructs a `_NewTypeCtx` carrying the NewType's name and callable
reference, then recurses into `__supertype__` with that context active. After the
recursion returns, `_erase_inner_newtypes` strips every `NewTypeShape` reachable through
the recursion result's `ArrayOf` layers so that exactly one `NewTypeShape` remains per
spine. The frame then wraps the (now wrapper-free) inner shape:
`NewTypeShape(name="FeatureVersion", inner=<recursion result>)`. Inner NewType names
survive as the terminal `Primitive.base_type`.

**Annotated** collects every metadata object in the `args[1:]` slice as a
`ConstraintSource`, tagging each with the active `newtype_ctx`. If a `FieldInfo` is
present, its `metadata` list contributes additional constraint sources (Pydantic unpacks
`Field(min_length=1)` into annotated-types objects there). Descriptions are captured
from `FieldInfo.description` -- first one found wins, so the outermost annotation's
documentation takes precedence. The collected constraints are then attached to the
recursion result via `attach_constraints`, which walks any leading `NewTypeShape`
wrappers to prepend the constraints on the first structural layer (`ArrayOf`, `MapOf`,
or scalar terminal) that can hold them. Raw `MinLen` / `MaxLen` constraints are wrapped
into typed `ArrayMinLen` / `ScalarMinLen` (and `MaxLen` variants) matching the attachment
layer, so length-constraint dispatch is type-keyed downstream.

**Union** delegates to `_peel_union`. That helper filters `NoneType` (marks optional),
`Sentinel` instances, and `Literal` sentinel arms. If multiple concrete `BaseModel`
subclasses remain, it invokes `union_resolver` and returns a `_Resolved` short-circuit.
A single remaining arm returns `_ContinueWith`, and `_unwrap` recurses into it.

**list** recurses into the element type and wraps the result in `ArrayOf`. Nested lists
(`list[list[str]]`) produce nested `ArrayOf` instances -- there is no numeric depth
counter. Constraints contributed by an `Annotated` wrapper at any particular list level
land on that level's `ArrayOf` node because `attach_constraints` prepends to the
outermost structural layer, which is exactly the `ArrayOf` that was just constructed.

**dict** recurses separately for key and value types (with `newtype_ctx=None` for both,
since dict keys and values are independent spines) and returns `MapOf`.

**Terminal** classification in `_terminal` handles the base case: `Any` becomes
`AnyScalar`, `Literal` becomes `LiteralScalar`, `BaseModel` subclasses route through
`model_resolver` (or fall back to `Primitive(source_type=cls)`), everything else becomes
`Primitive(base_type=newtype_ctx.name or annotation.__name__)`.

### Concrete walkthroughs

**Segment (union path).** `_unwrap` receives the `Annotated` alias for Segment. The
`Annotated` case collects discriminator metadata from `FieldInfo`, then sees the inner
annotation is a union. `_peel_union` finds three concrete `BaseModel` arms, invokes
`union_resolver`, and returns `_Resolved(UnionRef(...))` carrying the `UnionSpec` that
the resolver constructed. The `Annotated` handler attaches the discriminator constraints
and returns. Two frames deep, done.

**FeatureVersion (NewType chain path).** `FeatureVersion = NewType("FeatureVersion",
int32)` where `int32 = NewType("int32", Annotated[int, Field(ge=0, le=2147483647)])`.

Frame 1 sees `FeatureVersion` -- a NewType. Constructs `_NewTypeCtx("FeatureVersion",
FeatureVersion)`, recurses into `int32`. Frame 2 sees `int32` -- also a NewType.
Constructs `_NewTypeCtx("int32", int32)`, recurses into `Annotated[int, Field(ge=0,
...)]`. Frame 3 sees `Annotated`. Collects `ConstraintSource(source_name="int32",
constraint=<Field metadata ge/le>)`. Recurses into `int`. Frame 4 hits the terminal
`int`. `newtype_ctx` is still `_NewTypeCtx("int32", int32)` -- frame 3 passed frame 2's
context through unchanged, since `Annotated` does not introduce a NewType -- so
`_terminal` uses `newtype_ctx.name` (`"int32"`) as `base_type`. Returns
`Primitive(base_type="int32")`. Frame 3 attaches the constraints: `Primitive` gets the
`ge=0` / `le=2147483647` sources prepended. Frame 2's `_erase_inner_newtypes` sees a
bare `Primitive` -- no `NewTypeShape` to strip -- and wraps the result in
`NewTypeShape(name="int32", inner=Primitive(...))`. Frame 1's `_erase_inner_newtypes`
strips that inner `NewTypeShape`, yielding `Primitive(...)`, and wraps it in
`NewTypeShape(name="FeatureVersion", inner=Primitive(...))`.

The two paths demonstrate the function's range. Segment exits after two frames via
`union_resolver`. FeatureVersion recurses four frames through a NewType chain, with
constraint provenance tagging surviving to rendering.

## 4. Data structures

`extraction/specs.py` defines the vocabulary shared between extraction and rendering. Every spec is
a dataclass with no methods beyond field access and, in `UnionSpec`'s case, one cached
property.

**FieldSpec** represents one model field: alias-resolved name, `shape: FieldShape`,
description, required flag. `ModelRef` and `UnionRef` shapes carry their resolved specs
(populated during `extract_model` recursion), so consumers can follow the tree without a
separate expansion pass.

**RecordSpec** represents one Pydantic model: class name, cleaned docstring, fields in
documentation order, source class reference, the entry point string that located it, and
model-level constraints from decorators like `@require_any_of`.

**UnionSpec** represents a discriminated union type alias. Segment's `UnionSpec` carries
`members=[RoadSegment, RailSegment, WaterSegment]`, `discriminator_field="subtype"`, and
`common_base=TransportationSegment`. Its `annotated_fields` list pairs each `FieldSpec`
with `variant_sources` -- a tuple of `BaseModel` subclasses indicating which union
members contribute that field, or `None` for fields from `TransportationSegment` shared
across all members. The `fields` cached property unwraps this for code that doesn't need
provenance. Each member also has its already-extracted `RecordSpec` retained in
`member_specs: list[MemberSpec]` so downstream consumers (check builder, base-row
generator) reuse it instead of re-extracting the subtree. `UnionSpec` uses `eq=False`
because it contains mutable lists and a `cached_property` -- dataclass-generated
`__eq__` would be unreliable.

**ModelSpec** is the type alias `RecordSpec | UnionSpec`. Type collection, rendering
dispatch, and example loading all operate on `ModelSpec`. Consumers narrow with
`isinstance` when they need `UnionSpec`-specific attributes like `discriminator_field`.

**EnumSpec** and **EnumMemberSpec** serve enums. **NewTypeSpec** serves NewTypes.
**NumericSpec** serves numeric primitives with an `Interval` for bounds and optional
`float_bits`.

**SupplementarySpec** is the union type alias `EnumSpec | NewTypeSpec | RecordSpec |
PydanticTypeSpec` -- the set of non-feature types that need their own output pages.
`PydanticTypeSpec` covers Pydantic built-ins like `HttpUrl` and `EmailStr` (carrying the
class plus a pointer back to Pydantic's docs). `NumericSpec` and geometry types are
excluded because they render on aggregate pages rather than individual ones.

### Classification functions

Three functions at the bottom of `extraction/specs.py` classify discovery results.
`is_model_class` is a `TypeGuard` that checks `isinstance(obj, type) and issubclass(obj,
BaseModel)`. `is_union_alias` calls `analyze_type` with a sentinel `union_resolver` that
raises immediately on detection -- the only place outside the type analyzer that touches
Python type annotations. `filter_model_classes` applies the model guard across the
discovery dict's values.

## 5. Type registry

Maps type names to per-target display strings. `PRIMITIVE_TYPES` contains 15 entries:
four signed integer widths, three unsigned, two floats, `str`/`bool`, two Python builtin
aliases (`int` maps to `int64`, `float` maps to `float64`), and two geometry types
(`Geometry`, `BBox`). Each maps to a `TypeMapping` with a `markdown` field.

`is_semantic_newtype` answers a question: does this NewType deserve its own
documentation page? The function returns true when the outermost name differs from the
base type (`FeatureVersion` wrapping `int32`) or when the base type has no registry
entry (`HexColor` wrapping `str` via constraints). It returns false for registered
primitives (`int32` wrapping `int`) -- those are the type system's building blocks, not
user-facing concepts.

`resolve_type_name` looks up the registry by `base_type`, tries `source_type.__name__`
when the first lookup fails, and falls back to `base_type` as a last resort. Semantic
NewTypes wrapping unregistered classes (like `Sources` wrapping `SourceItem`) use the
underlying class name rather than the NewType alias -- `source_type.__name__` takes
precedence.

## 6. Model extraction

`extract_model` converts a Pydantic `BaseModel` subclass into a `RecordSpec`.

### Field ordering

Documentation order differs from Python declaration order. `_class_order` produces the
MRO-aware sequence: for single inheritance, reversed MRO puts base class fields first
and derived fields last. For multiple inheritance, the primary chain (first base) comes
first, then the class's own fields, then mixin fields. This matches how a reader
encounters the model -- shared structure before specialization.

`_field_order` walks the class hierarchy produced by `_class_order` and collects
`__annotations__` keys, deduplicating as it goes.

### Field extraction

For each field, the extractor resolves the alias chain (`validation_alias` > `alias` >
Python name via `resolve_field_alias`), calls `analyze_type` on `field_info.annotation`,
and builds a `FieldSpec`. The extractor uses `field_info.annotation` rather than
`get_type_hints()` because the latter returns unresolved TypeVars for generic base
classes.

One subtlety: Pydantic strips the `Annotated` wrapper from some fields and moves the
metadata to `field_info.metadata`. When this happens, `analyze_type` sees a bare type
and misses the constraints. `_attach_field_metadata` routes them through
`attach_constraints` -- tagging them with `source=None` since they came from the field's
own annotation rather than a NewType chain -- so length-constraint typing happens here
just as it does during normal `Annotated` unwrapping.

Model-level constraints come from `ModelConstraint.get_model_constraints(model_class)`,
which inspects decorators like `@require_any_of` and `@require_if`.

### Recursive extraction

`extract_model` recursively resolves sub-models and sub-unions during field extraction,
building `ModelRef`/`UnionRef` shapes with their specs already populated. It maintains a
shared cache keyed by Python class and an ancestor set for cycle detection.

The cache insert happens *before* recursion. Without this ordering, a back-edge
encounter would find no cached entry and infinite-loop instead of marking
`starts_cycle=True`. The sequence: create the partial `RecordSpec`, insert it into the
cache, then populate its fields. Shared references (the same sub-model used in multiple
fields) reuse the cached `RecordSpec` without marking cycles.

`UnionRef` fields resolve via the `union_resolver` callback -- they appear as a single
row in the output, linking to their members, rather than expanding inline.

## 7. Other extractors

### Enum extraction

`extract_enum` iterates members, checking `is_custom_docstring` for both class-level and
per-member descriptions. `DocumentedEnum` members carry `__doc__` attributes that the
extractor preserves. The class-level docstring is passed as `inherited_doc` to the
per-member check, so members that inherit the class docstring verbatim get
`description=None`.

### NewType extraction

`extract_newtype` calls `analyze_type` on the NewType callable and extracts the custom
docstring. When the NewType has no explicit docstring, it falls back to the description
returned by `analyze_type` -- the first `Field.description` found in the `Annotated`
metadata chain.

### Union extraction

The most involved extractor. Walk through `Segment` concretely.

`extract_union("Segment", annotation)` calls `_union_members`, which runs `analyze_type`
with a capturing `union_resolver` that raises out of the analysis as soon as it sees a
multi-arm union of `BaseModel` subclasses. The captured tuple gives the three member
types plus any description from enclosing `Annotated` layers.

Next, `_find_common_base` intersects each member's filtered MRO (BaseModel subclasses
only, excluding `BaseModel` itself). All three share `TransportationSegment` in their
MRO. The function picks the most-derived class in the intersection -- the one whose
worst-case MRO distance is smallest. `TransportationSegment` wins: it is the direct
parent of all three members.

The extractor calls `extract_model(TransportationSegment)` to get the shared field set.
Fields like `id`, `geometry`, `version`, `sources`, and `subtype` appear in the common
base. These become shared `AnnotatedField` entries with `variant_sources=None`.

Then it extracts each member: `RoadSegment`, `RailSegment`, `WaterSegment`. Each result
is retained on the `UnionSpec` as a `MemberSpec(member_cls, spec)` so consumers don't
re-extract. Fields not in the shared set are variant-specific, deduplicated by
`(name, structural_fingerprint)` where the fingerprint walks the field's `FieldShape`
tree, capturing every wrapper layer plus the terminal type. If `RoadSegment` and
`WaterSegment` both define a `width` field with the same fingerprint, the
`AnnotatedField` accumulates both classes: `variant_sources=(RoadSegment,
WaterSegment)`. Fields unique to one member get a single-element tuple. When two members
declare the same field name with the same structural fingerprint but diverging
constraints, the extractor raises rather than silently dropping one member's
constraints.

`extract_discriminator` inspects the `Annotated` metadata for a `FieldInfo` with a
discriminator attribute. For Segment, it finds `subtype` and builds the mapping:
`{"road": RoadSegment, "rail": RailSegment, "water": WaterSegment}` by checking each
member for single-value `Literal` fields on the discriminator.

### Primitive extraction

`partition_numeric_and_geometry_types` reads a module's `__all__` exports. NewType
exports are numeric primitives; non-constraint class exports are geometry types.

`extract_numerics` builds `NumericSpec` objects. For each primitive name it resolves
the object from the module, calls `extract_newtype` for the type analysis, then extracts
numeric bounds from constraints. `extract_numeric_bounds` scans constraint objects for
`ge`/`gt`/`le`/`lt` attributes and packs them into an `Interval`.

## 8. Constraint prose

Two modules convert constraint objects into human-readable text.

### Field constraints

`extraction/field_constraints.py` pattern-matches constraint types. `Interval` renders
as `lower <= x <= upper` using Unicode comparison operators. Single-bound constraints
(`Ge`, `Gt`, `Le`, `Lt`) render as `>= value` or `< value`. Length constraints
(`MinLen`, `MaxLen`) render as plain prose (e.g. "Minimum length: 1"). `GeometryTypeConstraint` lists
allowed geometry types by name, converting snake_case values to PascalCase. `Reference`
describes the relationship and target model, using an optional `link_fn` to produce
markdown links.

Opaque constraints -- classes that inherit `object.__repr__` without customization --
render as their class name plus docstring. When a regex pattern attribute exists, the
prose includes it.

`constraint_display_text` is the top-level entry point. It checks whether the constraint
is opaque and has a docstring, and if so, produces a composite description combining the
docstring, class name, and pattern. Otherwise it delegates to
`describe_field_constraint`.

### Model constraints

`extraction/model_constraints.py` handles model-level constraints from decorators.
`analyze_model_constraints` returns two things in one pass: a list of section-level
descriptions and a dict mapping field names to the constraint descriptions that
reference them.

The module consolidates related conditionals. Three `require_if` constraints with the
same target fields but different trigger values merge into "when X is one of: a, b, c"
instead of three separate bullets. `_consolidation_key` groups constraints by `(type,
field_names, condition_field_name)`. Groups with one member render normally; groups with
multiple members produce consolidated prose.

`NoExtraFieldsConstraint` is silently skipped -- it is a structural validation rule, not
something a documentation reader acts on.

## 9. Module layout

Translates Python module paths into output directory paths. `compute_schema_root` finds
the longest common dotted prefix across all entry point module paths. Given paths like
`overture.schema.buildings`, `overture.schema.places`, and
`overture.schema.transportation`, the root is `overture.schema`. For a single unique
path, it drops the last component.

`compute_output_dir` mirrors the remaining package structure after stripping the root.
Packages (directories with `__path__` per PEP 302) keep all components. File modules
drop their last component, since the `.py` filename adds no useful structure.
`is_package_module` checks `sys.modules` for `__path__` to make this distinction.

The entry point string `overture.schema.buildings:Building` encodes both module and
class. `entry_point_module` extracts the module path, `entry_point_class` extracts the
class name. `output_dir_for_entry_point` composes these to produce the output directory
for a feature.

## 10. Supplementary type collection

`collect_all_supplementary_types` walks the expanded field trees of all feature specs to
discover every referenced type that needs its own output page: enums, semantic NewTypes,
and sub-models.

The walk maintains a visited set for models and a feature name set for skip detection.
Types that are themselves top-level features get skipped. For `UnionRef` fields, the function extracts and walks each member's fields. For
semantic NewTypes, it walks the `__supertype__` chain to collect intermediate NewTypes --
`Id` wraps `NoWhitespaceString` wraps `str`, and both `Id` and `NoWhitespaceString` get
their own pages. `walk_shape` from `field_walk.py` handles recursion into `ArrayOf`,
`MapOf`, and `NewTypeShape` wrappers.

`ModelRef` fields follow their `.model` reference (populated during `extract_model`
recursion) into nested `RecordSpec` trees.

A single field matches multiple conditions independently. A semantic NewType wrapping a
`ModelRef` triggers both NewType extraction and model collection. The checks use
independent `if` statements, not `elif`.

## 11. Path assignment

`build_placement_registry` builds the complete `dict[TypeIdentity, PurePosixPath]`
mapping each type to its output file path. Four tiers:

Aggregate pages come first. All numeric primitives point to
`system/primitive/primitives.md`. All geometry types point to
`system/primitive/geometry.md`. These are hardcoded paths since the types share a single
reference page.

Feature specs get individual pages. Output directories derive from
`output_dir_for_entry_point`. Filenames are the snake-case type name with a `.md`
extension.

Supplementary specs get module-derived paths from `source_type.__module__`. When a
supplementary type's output directory falls under a feature directory,
`_nest_under_types` inserts a `types/` segment. Without this insertion, an enum defined
in `overture.schema.buildings` would land alongside the Building feature page. With it,
the enum lands in `buildings/types/` -- preventing supplementary type pages from
cluttering feature directories.

`_nest_under_types` sorts feature directories by path length (descending) before
checking containment, so the most specific match wins.

`PydanticTypeSpec` entries (e.g. `HttpUrl`) bypass module mirroring and land at
`pydantic/<source_module>/<slug>.md`, keeping the generated Pydantic reference set
isolated from theme directories.

## 12. Links and reverse references

### Link computation

`LinkContext` carries the current page's output path and the full `dict[TypeIdentity,
PurePosixPath]` registry. When a renderer formats a type reference, it calls
`resolve_link` with the target's `TypeIdentity` to compute a relative path. Identities
without registry entries return `None`, telling renderers to show inline code instead
of a broken link. `resolve_link_or_slug` provides a fallback when a link is required
regardless.

`relative_link` computes `../` navigation between any two paths in the output tree. It
finds the common prefix of directory components, counts the levels up from the source
directory, and descends into the target. Both paths must be normalized -- the function
rejects `..` components to prevent path traversal surprises.

### Reverse references

`compute_reverse_references` walks all feature fields and supplementary specs to build
`dict[TypeIdentity, list[UsedByEntry]]`. Each entry maps a target identity to the list
of types that reference it. Entries sort models before NewTypes, alphabetical within
each group.

The function tracks references with sets for deduplication, then sorts into lists at the
end. It skips self-references and references to types not in the supplementary spec dict
(features don't need "used by" sections since they are the entry points).

NewType specs register additional references from their constraint sources. If `Id`
inherits a constraint from `NoWhitespaceString`, the reverse reference captures that
`Id` uses `NoWhitespaceString` -- even though the relationship is through constraint
provenance rather than direct field reference.

## 13. Markdown type formatting

`markdown/type_format.py` converts a field's `FieldShape` into display strings for
markdown output.

`format_type` handles the full range of field types. Single-value `LiteralScalar`s
render as `"value"` in backticks. Semantic NewTypes and enums/models get markdown links
via `_resolve_type_link`, which checks the `LinkContext` registry and falls back to plain
code spans. For types with a linked identity (semantic NewTypes, enums, models), list
rendering depends on where the `ArrayOf` layers sit relative to the `NewTypeShape`
boundary. An `ArrayOf` sitting outside the `NewTypeShape` in the shape tree means the
list wraps the NewType (`list[PhoneNumber]`) and renders as `list<PhoneNumber>`. A
`NewTypeShape` with an `ArrayOf` inner means the NewType wraps a list internally
(`Sources` wrapping `list[SourceItem]`) and renders with a `(list)` qualifier. Non-NewType
identities (enums, models) use `list<X>` syntax. Linked inner types use broken-backtick
syntax (`` `list<` `` ... `` `>` ``) built as a single wrapper to avoid adjacent backticks
that CommonMark would interpret as multi-backtick code span delimiters. `MapOf` shapes
render as `` `map<K, V>` ``. Qualifiers (optional, list, map) append in parentheses.

`UnionRef` members format independently -- each gets its own link resolution, joined
with pipe separators escaped for table-cell safety.

`format_underlying_type` handles NewType page headers. It links enums and models that
have their own pages but skips the outermost NewType name to avoid self-referencing.

## 14. Markdown rendering

`markdown/renderer.py` is the template driver.

### Templates

Six Jinja2 templates in `markdown/templates/`. `feature.md.jinja2` renders a field table
with Name, Type, and Description columns, an optional Constraints section, an optional
Examples section, and a "Used By" partial. `enum.md.jinja2` renders a bullet list of
values. `newtype.md.jinja2` shows underlying type and constraints with provenance links.
`primitives.md.jinja2` and `geometry.md.jinja2` render aggregate reference pages.
`_used_by.md.jinja2` is an included partial.

The Jinja2 environment registers `linkify_urls` as a filter, which wraps bare URLs in
markdown link syntax. The filter uses a two-pass approach: extract code spans first (to
avoid modifying URLs inside backticks), linkify the remaining text, then restore code
spans.

### Field expansion

`render_model` dispatches on spec type. `RecordSpec` gets `_expand_model_fields`, which
walks the pre-populated `FieldSpec.model` tree and produces dot-notation rows.
`sources[0].dataset` appears as a single row in the flat field table, with `[]`
appended per nesting level to list-of-model fields (so a doubly-nested list gets
`[][]`). Expansion stops at fields marked with
`starts_cycle`.

`UnionSpec` gets `_expand_union_fields`, which adds italic variant tags to
variant-specific fields. For Segment, shared fields from `TransportationSegment` (like
`id`, `geometry`, `sources`) render as plain rows. Variant-specific fields get tagged:
`_short_variant_name` strips the union name suffix, so `RoadSegment` becomes `Road`,
`WaterSegment` becomes `Water`. A field present in two of three members renders as ``
`width` *(Road, Water)* ``. Shared fields render without tags.

### Constraint annotation

Field-level constraints from the field's own annotation (not inherited from NewType
chains) annotate the field's description cell as italic text. The distinction matters:
constraints with `source=None` came from the field itself, while constraints with a
named source live on the NewType's own page.

Model-level constraints annotate top-level field rows (those without dot-notation
prefixes) using the `field_notes` dict from `analyze_model_constraints`.

### Example formatting

Example values render in backticks for monospace consistency. Booleans use
`true`/`false` (not Python's `True`/`False`). `None` renders as `null`. Long values
truncate at 100 characters. Lists and dicts use compact bracket/brace notation.

### Aggregate pages

`render_primitives_from_specs` sorts primitives by bit-width key (prefix then numeric
width), groups into signed integers, unsigned integers, and floats, and formats ranges.
Integer ranges show both bounds as a compact "lower to upper" form; `int64`-scale bounds
use `2^63` notation for readability. `render_geometry_from_values` produces a
comma-separated backtick list.

## 15. Example loader

Loads example data from theme `pyproject.toml` files and validates it against the
schema.

`resolve_pyproject_path` walks up from a model's module file to find `pyproject.toml`.
`load_examples_from_toml` reads the `[examples.ModelName]` TOML section.

Validation requires two preprocessing steps that handle flat-schema conventions.

Literal fields (like `theme="buildings"`) are omitted from examples since they carry
constant values. `_inject_literal_fields` adds them back before validation by scanning
`model_fields` for single-value `Literal` annotations via `single_literal_value`.

Discriminated union examples from flat Parquet schemas include null fields from
non-selected variant arms. `_strip_null_unknown_fields` removes null-valued fields not
in the common base's field set, so the selected arm's validator accepts the data without
choking on fields that belong to sibling variants.

`validate_example` returns a Pydantic model instance. `flatten_model_instance` walks the
instance recursively using `isinstance(value, BaseModel)` to distinguish model fields
(recurse with dot notation) from dict fields (keep as leaf values). Lists of models
use bracket notation (`sources[0].dataset`), nested lists use double-index notation
(`hierarchies[0][1].name`). The model instance itself encodes the type structure,
eliminating the need for external schema information.

For discriminated unions, the concrete variant instance lacks fields from other arms.
`augment_missing_fields` compares base field names against the union's merged field list
and appends `(name, None)` for absent fields, matching the flat Parquet schema where all
variant columns exist.

`order_example_rows` sorts by field position in the documentation's field order using a
stable sort, so sub-fields maintain their original relative order.

`load_examples` orchestrates the full flow: find the pyproject.toml, load the TOML
section, validate each example, flatten via `flatten_model_instance`, augment missing
fields, and order. Invalid examples log a warning and skip rather than failing the
pipeline.

## 16. Orchestration and CLI

### The pipeline

`generate_markdown_pages` in `markdown/pipeline.py` is the "main" function. It takes
feature specs and a schema root, returns rendered pages without touching the filesystem.
Seven steps (tree expansion now happens inside `extract_model`):

1. **Partition primitive and geometry names** from the system primitive module's
   `__all__` exports.

2. **Collect supplementary types** by walking feature trees.

3. **Build the placement registry** mapping every type to its output file path.

4. **Compute reverse references** across all features and supplements.

5. **Render each feature** with its `LinkContext`, loaded examples, and used-by entries.

6. **Render each supplementary type** -- dispatching to `render_enum`, `render_newtype`,
   `render_model` (for sub-models), or `render_pydantic_type` based on spec type.

7. **Render aggregate pages** for primitives and geometry.

The return value is `list[RenderedPage]` -- frozen dataclasses carrying content, output
path, and a boolean `is_model` flag. The caller decides what to do with them.

### The CLI

`cli.py` is a thin Click wrapper. The `generate` command discovers models, computes
schema root from *all* entry points (before any theme filtering), classifies each entry
as model or union via `is_model_class` and `is_union_alias`, extracts specs, calls the
pipeline, and writes output.

Schema root computation uses all entry points deliberately. Theme filtering narrows
which features appear in the output, but the directory structure must remain stable
regardless of which themes are selected. Computing the root from filtered paths would
shift output directories when themes change.

Feature pages get Docusaurus frontmatter (`sidebar_position: 1`) prepended. The CLI
generates `_category_.json` files for sidebar navigation, assigning positions
alphabetically with feature directories first.

The `list` command prints sorted model names -- a diagnostic tool for verifying which
models the entry point system discovers.

---

## Top-down trace: Segment through the pipeline

A reader who reached this point has seen every module in isolation. This section follows
`Segment` from discovery to rendered markdown, showing how the pieces compose.

**Discovery.** The CLI calls `discover_models()`. The entry point
`overture:transportation:segment` loads `overture.schema.transportation:Segment` -- the
`Annotated[Union[...]]` alias. `Segment` lands in the return dict keyed by
`ModelKey(namespace="overture", theme="transportation", type="segment",
entry_point="overture.schema.transportation:Segment")`.

**Classification.** The CLI tests each entry. `is_model_class(Segment)` returns false --
`Segment` is not a class. `is_union_alias(Segment)` calls `analyze_type` with a sentinel
`union_resolver` that raises on detection. The CLI routes Segment to `extract_union`.

**Extraction.** `extract_union("Segment", annotation)` calls `_union_members`, which
runs `analyze_type` with a capturing `union_resolver` to grab the three member types
plus the union description. `_find_common_base` picks `TransportationSegment` as the
shared parent. The extractor calls `extract_model` on the common base and on each
member -- the results are cached on the `UnionSpec` as `member_specs` -- and partitions
the non-shared fields into `AnnotatedField` entries with variant provenance.
`extract_discriminator` finds `subtype` and builds `{"road": RoadSegment, "rail":
RailSegment, "water": WaterSegment}`. The result is a `UnionSpec` (a `ModelSpec`).

Meanwhile, concrete models like `Building` go through `extract_model`, which calls
`analyze_type` on each field annotation. A field typed `FeatureVersion` unwraps through
two NewType layers and an `Annotated` layer, producing a `NewTypeShape(name="FeatureVersion",
inner=Primitive(base_type="int32", constraints=(...)))` shape with constraint provenance
linking `ge=0` back to the `int32` NewType. Both extraction paths produce `ModelSpec`
values.

**Pipeline entry.** The feature specs enter `generate_markdown_pages`.
Sub-model `FieldShape` trees are fully resolved -- `ModelRef` nodes already carry their
`RecordSpec` from recursive `extract_model` calls. No separate expansion pass is needed.

**Layout.** `partition_numeric_and_geometry_types` reads the system module's exports.
`collect_all_supplementary_types` walks Segment's field shapes and discovers referenced
enums (like `Subtype`), semantic NewTypes (like `Id`, `Sources`), and sub-models. The
walk follows `ModelRef.model` references down the tree, and for `UnionRef` shapes,
extracts and walks each member's fields separately.

`build_placement_registry` assigns Segment's output path from its entry point:
`entry_point_module` extracts `overture.schema.transportation`, `compute_output_dir`
strips the schema root and mirrors the remaining structure. Supplementary types get
module-derived paths with `types/` inserted under feature directories.

**Reverse references.** `compute_reverse_references` walks Segment's fields and records
that Segment references `Subtype`, `Id`, `Sources`, and other types. These references
populate "Used By" sections: the `Subtype` enum page shows that Segment uses it.

**Rendering.** The pipeline builds a `LinkContext` from Segment's output path and the
full registry. `render_model` dispatches to `_expand_union_fields` because the spec is
a `UnionSpec`. Shared fields from `TransportationSegment` render as plain rows.
Variant-specific fields get italic tags: `` `road_class` *(Road)* ``. The renderer
formats each field's `FieldShape` via `format_type`, which resolves links through the
`LinkContext` -- `Subtype` gets a relative link to its enum page, `Id` links to its
NewType page. Constraints with `source_name=None` annotate field rows; constraints with
named sources appear on the source NewType's page instead.

The example loader finds `pyproject.toml` in the transportation theme package, reads
`[examples.Segment]`, validates each example against the union alias (injecting literal
fields, stripping null fields from non-selected arms), flattens the model instance to
dot-notation via `flatten_model_instance`, augments missing cross-arm fields, and orders
by field position.

The Jinja2 template assembles the field table, optional constraints section, examples,
and "Used By" partial into markdown.

**Output.** The pipeline returns a `RenderedPage` with Segment's content, its output
path, and `is_model=True`. The CLI prepends Docusaurus frontmatter and writes the
file. `_category_.json` files get generated for sidebar navigation.

**The layering principle.** At every stage, the modules that do the work never reach
back up the dependency chain. Renderers consume specs and registries but never import
extractors. Extractors consume `analyze_type` but never import renderers. The type
analyzer imports nothing from the codegen package except `clean_docstring`. Any module
can be understood, tested, and modified by reading only the modules below it.
