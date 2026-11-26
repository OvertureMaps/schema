## [2.0.1] - 2026-11-10

### Documentation

- Converted the CLI's `Args` docstring sections to numpydoc `Parameters`, with types copied from the annotations. ([#804](https://github.com/OvertureMaps/schema/issues/804))

### Miscellaneous

- Typed `introspect_union`'s argument as `TypeForm[object]`, [PEP 747](https://peps.python.org/pep-0747/)'s type for a type expression, instead of `Any`. ([#794](https://github.com/OvertureMaps/schema/issues/794))
- Raised the minimum pydantic version to 2.14, matching `overture-schema-system`. ([#810](https://github.com/OvertureMaps/schema/issues/810))


## [2.0.0] - 2026-09-02

### Bug Fixes

- Fixed `--help` example blocks rendering a literal `\b` instead of Click's no-rewrap marker, and replaced the tag-filter examples that cited tags discovery never emitted. ([#668](https://github.com/OvertureMaps/schema/issues/668))

### Miscellaneous

- Updated CLI heterogeneous collection test fixtures to align with the Places schema removal of the deprecated `categories` field. ([#434](https://github.com/OvertureMaps/schema/issues/434))
- Declared explicit version floors for workspace dependencies. ([#557](https://github.com/OvertureMaps/schema/issues/557))
- Raised the minimum pydantic version to 2.13.0. ([#593](https://github.com/OvertureMaps/schema/issues/593))
- Migrated the build backend from hatchling to uv_build and made `overture.schema` a PEP 420 namespace package. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Added a test verifying CLI correctly generates the unified JSON Schema. ([#671](https://github.com/OvertureMaps/schema/issues/671))
