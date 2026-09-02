## [2.0.0] - 2026-09-02

### Features

- Ensured the `json_schema()` function includes the JSON Schema dialect (`$schema`). ([#671](https://github.com/OvertureMaps/schema/issues/671))

### Miscellaneous

- Raised the minimum pydantic version to 2.13.0. ([#593](https://github.com/OvertureMaps/schema/issues/593))
- Migrated the build backend from hatchling to uv_build and made `overture.schema` a PEP 420 namespace package. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Reserved the plain `overture` tag to `overture-schema-common` and documented its provider in the README. ([#668](https://github.com/OvertureMaps/schema/issues/668))
