Overture Maps Schema
===

The Overture Maps schema working group is responsible for designing the Overture Maps Data Schema and the Global Entity Reference System (GERS).

## Documentation
The contents of this repository are presented in a more human-friendly format at [docs.overturemaps.org](https://docs.overturemaps.org/)

## Python packages
The schema is authored as [Pydantic](https://docs.pydantic.dev/latest/) models, published
as a set of Python packages under `packages/`. See
[SCHEMA_GUIDE.md](SCHEMA_GUIDE.md) for installing them, validating data, generating
artifacts, and authoring new schema models.

## Schema reference

- [GLOSSARY.md](GLOSSARY.md) — vocabulary for both the data model (entity, feature type,
  theme) and the Python toolchain (entry point, workspace, discriminated union).
- [SCHEMA_CONVENTIONS.md](SCHEMA_CONVENTIONS.md) — naming and modelling conventions.
  **Out of date:** it predates the Pydantic packages and still describes JSON Schema as
  the way the schema is defined, spells `subtype` as `subType`, and leaves the extensions
  section unfinished. Useful for the conventions themselves; check anything structural
  against [SCHEMA_GUIDE.md](SCHEMA_GUIDE.md).

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for branching strategy, workflow, and contribution guidelines.

## Feedback
Please provide feedback or ask questions at [Discussions](https://github.com/orgs/OvertureMaps/discussions).


