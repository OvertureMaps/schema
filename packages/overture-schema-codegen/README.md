# Overture Schema Codegen

Generates documentation from Overture Maps Pydantic schema definitions.

Pydantic's `model_json_schema()` flattens the schema's domain vocabulary into JSON
Schema primitives. NewType names disappear, constraint provenance is lost (which NewType
contributed which bound), custom constraint classes lose their identity (a
`GeometryTypeConstraint` becomes an anonymous `enum` array), and discriminated union
structure collapses into `anyOf` arrays with duplicated fields.

Navigating Python's type annotation machinery -- NewType chains, nested `Annotated`
wrappers, union filtering, generic resolution -- is complex. The codegen does it once.
`analyze_type()` unwraps annotations into `TypeInfo`, a flat target-independent
representation. Extractors build specs from `TypeInfo`. Renderers consume specs without
touching the type system. New output targets (Arrow schemas, PySpark expressions) add
renderers, not extraction logic.

## Usage

```bash
# Generate markdown documentation for all themes
overture-codegen generate --format markdown --output-dir docs/schema/reference

# Generate for a single theme
overture-codegen generate --format markdown --tag overture:theme=buildings --output-dir out/

# List discovered models
overture-codegen list
```

The generator discovers models via `overture.models` entry points (provided by theme
packages like `overture-schema-buildings-theme`), extracts type information, and renders
output pages with cross-page links, constraint descriptions, and validated examples.

## Architecture

Four layers with strict downward imports -- no layer references the one above it:

```text
Rendering            Output formatting, all presentation decisions
    ^
Output Layout        What to generate, where it goes, how outputs link
    ^
Extraction           TypeInfo, FieldSpec, RecordSpec, UnionSpec
    ^
Discovery            discover_models() from overture-schema-common
```

**Discovery** loads registered Pydantic models via entry points. The return dict
includes both concrete `BaseModel` subclasses (like `Building`) and discriminated union
type aliases (like `Segment`). Both satisfy the `ModelSpec` protocol and flow through
the same pipeline.

**Extraction** unwraps type annotations into specs. `analyze_type()` is the central
function -- a single iterative loop that peels NewType, Annotated, Union, and container
wrappers, accumulating constraints tagged with the NewType that contributed them.
Domain-specific extractors (`model_extraction`, `union_extraction`, `enum_extraction`,
`newtype_extraction`, `numeric_extraction`) call `analyze_type()` for field types and
produce spec dataclasses.

**Output Layout** determines what artifacts to generate and where they go. Supplementary
type collection walks expanded feature trees to find referenced enums, NewTypes, and
sub-models. Path assignment maps every type to an output file path mirroring the Python
module structure. Link computation and reverse references enable cross-page navigation.

**Rendering** consumes specs and owns all presentation decisions. Markdown output uses
Jinja2 templates for feature pages (with field tables, constraint sections, and
examples), enum pages, NewType pages, and aggregate numeric/geometry reference pages.

`markdown/pipeline.py` orchestrates the full pipeline without I/O, returning
`list[RenderedPage]`. The CLI writes files to disk with Docusaurus frontmatter.

## Programmatic use

```python
from overture.schema.codegen.extraction.type_analyzer import analyze_type, TypeKind

info = analyze_type(some_annotation)
assert info.kind == TypeKind.PRIMITIVE
assert info.base_type == "int32"
assert info.newtype_name == "FeatureVersion"
# Constraints carry provenance:
for cs in info.constraints:
    print(f"{cs.constraint} from {cs.source}")
```

## Fetching sample data

Theme packages include example records in their `pyproject.toml` files under
`[[examples.<Type>]]` sections. The codegen validates these against Pydantic
models and renders them in feature pages.

To fetch a fresh sample from the latest Overture release using DuckDB:

```bash
duckdb -json \
  -c "load spatial" \
  -c "attach 'http://labs.overturemaps.org/data/latest.ddb' as overture" \
  -c "select to_json(columns(*))
      from (
        select * REPLACE ST_AsText(geometry) as geometry
        from overture.place
        USING SAMPLE 1
      )" \
  | jq .
```

The `latest.ddb` database always points to the current release. Tables use
the type name directly (`overture.place`, `overture.segment`,
`overture.building`, etc.). Convert the JSON output to TOML for inclusion in
the theme's `pyproject.toml`.

## Further reading

- [Design document](docs/design.md) -- architecture, extension points, data flow
  diagrams
- [Walkthrough](docs/walkthrough.md) -- module-by-module narrative tracing Segment
  through the full pipeline
