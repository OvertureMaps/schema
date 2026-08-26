Overture Schema
===

This code in this repository defines the Overture schema.


_ Note: You'll find reference documentation, tutorials, and examples of working with Overture data
at [docs.overturemaps.org](https://docs.overturemaps.org/).__

## What's in this repository

| Path | What it is |
|---|---|
| `packages/` | The schema, authored as [Pydantic](https://docs.pydantic.dev/latest/) models and published as Python packages. |
| `reference/examples/` | Feature instances that are **expected to validate** — one file per case, organized by theme. |
| `reference/counterexamples/` | Feature instances that are **expected to fail**, most carrying the specific error they should raise. |
| `tests/` | Tests that span packages, including the check that keeps the imports in these docs working. |
| `docs/` | Source for the schema pages on docs.overturemaps.org, plus the versioning reference. |
| `schema/` | **Deprecated.** The YAML JSON Schema — see [The YAML schema](#the-yaml-schema-deprecated). |
| `examples/`, `counterexamples/` | **Deprecated.** Fixtures for the YAML schema, not the Pydantic models. |

Note the two sets of examples. `reference/examples/` and `reference/counterexamples/` are
the current ones, exercised by the Python test suite. The top-level `examples/` and
`counterexamples/` belong to the deprecated YAML schema. They overlap heavily but have
drifted apart; when you add a case, add it under `reference/`.

## Python packages

Thirteen packages under `packages/`, versioned and released independently:

- **`overture-schema`** — the umbrella package. Depends on all themes and support
  packages for a coherent set. **This is what consumers pin.**
- **Themes** — `theme-addresses`, `theme-base`, `theme-buildings`, `theme-divisions`,
  `theme-places`, `theme-transportation`. One package per theme, each holding its feature
  types and the structures they share.
- **Foundation** — `system` (the base types every model builds on) and `common`
  (structures shared across themes, like names and sources).
- **Tooling** — `cli` (validate data, generate JSON Schema), `codegen` (generate docs and
  code from the models), `validation` (validate against the union of all discovered
  models), `pyspark` (validation expressions for Spark).

These pages are for people working with the packages in code:

- [SCHEMA_GUIDE.md](SCHEMA_GUIDE.md) — install the packages, explore the models, validate
  data, generate artifacts. **Start here.**
- [AUTHORING.md](AUTHORING.md) — register your own feature types, author new schema
  models, build an SDK or CLI on the models.
- [CONCEPTS.md](CONCEPTS.md) — why the schema is Pydantic, why it is many packages, and
  what the GeoJSON envelope is.
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — symptom-indexed fixes and known gotchas.
- [GLOSSARY.md](GLOSSARY.md) — vocabulary for both the data model (entity, feature type,
  theme) and the Python toolchain (entry point, workspace, discriminated union).

Run the full test and quality suite with:

```bash
make check
```

## The YAML schema (deprecated)

`schema/` holds the previous definition of the Overture schema as JSON Schema written in
YAML, with `schema/schema.yaml` as its entry point. It is validated by `./test.sh` (which
needs [`jv`](https://github.com/santhosh-tekuri/jsonschema)) against the top-level
`examples/` and `counterexamples/`, wired up in
[test-schema.yaml](.github/workflows/test-schema.yaml).

**It is deprecated and scheduled for removal in December 2026.** It stays until then
because docs.overturemaps.org still builds from it: the interactive schema blocks come
from `schema/`, and the sample features come from `examples/`. See
[docs/README.md](docs/README.md).

**Until it is removed, backward-compatible changes belong in both places.** A change to
the published data should land in the Pydantic models *and* in the YAML, so the two
definitions stay in step for as long as both are live.

## Project history

The schema working group opened this repository in January 2023, and the artifacts of
every phase of development are still here. 

| | |
|---|---|
| **Jan 2023** | Repository created as `schema-wg`, chartered to design the data schema and GERS. |
| **Mar 2023** | The schema takes shape as JSON Schema written in YAML: `schema/`, `examples/`, `counterexamples/`, and `test.sh` all arrive together. |
| **Aug 2023** | The Schema Task Force writes a *doctrine* on top of the project's tenets, to aim the work at a vision rather than react week to week. |
| **Jul 2024** | Overture data reaches general availability. |
| **Jul 2025** | Pydantic rewrite begins.
| **Nov 2025** | `packages/` are merged to main. The Pydantic schema and the YAML schema are developed in parallel. |
| **Aug 2026** | Repository docs consolidated into the guides listed above. |
| **Dec 2026** | `schema/`, `examples/`, and `counterexamples/` scheduled for removal. |

1,788 commits from 71 contributors.

### The tenets and the doctrine

The working group set down six tenets early on, under the heading *"These are our tenets
unless you know better ones"* — address the core and enable the periphery; invent across
the gap; backward-compatible is forward-compatible; the world is neither flat nor still;
empower, don't dictate; always open, never closed. They still govern the design, and are
recorded with their consequences in [CONCEPTS.md](CONCEPTS.md#the-tenets).

At the Schema Task Force meeting on 2023-08-30, the group decided to work toward a stated
vision rather than react week to week, and wrote a short doctrine built on those tenets for
the Working Group to ratify. It made five commitments:

- **The schema optimizes for specific use cases, but allows extension.** Structure targets
  selected use cases; user extensions unblock everyone else.
- **The schema gets better over time.** Properties for core use cases keep landing, known
  issues keep getting fixed, and the schema advances in a backward-compatible way.
- **The schema is a cohesive whole.** Same problems get same solutions and same things get
  same names, within and across themes, so that understanding one theme carries to the rest.
- **The schema is usable for data consumption by humans.**
- **The schema is usable for data consumption by open source tools.**

The doctrine flagged the last two as an unresolved tension and said the project should lean
toward one. The 2025 move to Pydantic is what settled it: the models are authored for humans
to read and edit, and the artifacts tools need — JSON Schema, PySpark expressions,
documentation — are generated from them. See
[Why Pydantic rather than JSON Schema](CONCEPTS.md#why-pydantic-rather-than-json-schema).

The specifics the doctrine argued over have all since been resolved. The `admins` theme is
now `divisions`; the camelCase property names it cited (`isoCountryCodeAlpha2`,
`road.roadNames`) became snake_case in February 2024; and the `entityId` property it
proposed as the schema/GERS interface never shipped — features carry a GERS `id` directly.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branching strategy, workflow, and contribution
guidelines.

## Feedback

Please provide feedback or ask questions at
[Discussions](https://github.com/orgs/OvertureMaps/discussions).
