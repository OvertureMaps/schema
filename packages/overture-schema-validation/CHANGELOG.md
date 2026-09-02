## [2.0.0] - 2026-09-02

### Documentation

- Corrected the README's usage examples, which showed `validate_json` accepting the flat tabular shape rather than GeoJSON. ([#668](https://github.com/OvertureMaps/schema/issues/668))

### Miscellaneous

- Migrated the build backend from hatchling to uv_build and made `overture.schema` a PEP 420 namespace package. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Extracted `validate()` and `validate_json()` into the new `overture-schema-validation` package, off the shared `overture.schema` namespace root. ([#622](https://github.com/OvertureMaps/schema/issues/622))
