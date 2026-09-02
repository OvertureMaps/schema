## [2.0.0] - 2026-09-02

### Features

- Each `overture-schema` release now attaches `overture-schema.json`, the unified JSON Schema for the whole official Overture schema. ([#671](https://github.com/OvertureMaps/schema/issues/671))

### Documentation

- Rewrote the README against the real import surface: `overture.schema` is a namespace root, so models import from their theme packages and the utility functions from `overture.schema.validation` and `overture.schema.system`. ([#668](https://github.com/OvertureMaps/schema/issues/668))

### Miscellaneous

- Added per-package release-trigger workflow, towncrier changelog fragments, and a fragment-required CI check.
  Declared explicit version floors for workspace dependencies. ([#557](https://github.com/OvertureMaps/schema/issues/557))
- Raised the minimum pydantic version to 2.13.0. ([#593](https://github.com/OvertureMaps/schema/issues/593))
- Migrated the build backend to uv_build with an explicit `overture.schema` namespace module root shipping only `py.typed`. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Moved `validate()` and `validate_json()` into the new `overture-schema-validation` dependency; the `overture.schema` namespace root is now a bare pkgutil shim. ([#622](https://github.com/OvertureMaps/schema/issues/622))
- Rename theme packages to improve sorting and grouping characteristics. ([#649](https://github.com/OvertureMaps/schema/issues/649))
