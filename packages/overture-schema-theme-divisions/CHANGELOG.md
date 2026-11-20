## [2.0.1] - 2026-11-10

### Bug Fixes

- Fixed `Division`, `DivisionArea`, and `DivisionBoundary` accepting features without the `admin_level` their subtype requires when validated with Pydantic or `overture-schema validate`. The generated JSON Schema already required it. ([#784](https://github.com/OvertureMaps/schema/issues/784))

### Miscellaneous

- Raised the minimum pydantic version to 2.14, matching `overture-schema-system`. ([#810](https://github.com/OvertureMaps/schema/issues/810))
- Raised the minimum `overture-schema-system` to 2.0.1, so installing this package alone includes the fix that enforces the `admin_level` rules on `Division`, `DivisionArea` and `DivisionBoundary`.


## [2.0.0] - 2026-09-02

### Miscellaneous

- Declared explicit version floors for workspace dependencies. ([#557](https://github.com/OvertureMaps/schema/issues/557))
- Raised the minimum pydantic version to 2.13.0. ([#593](https://github.com/OvertureMaps/schema/issues/593))
- Migrated the build backend from hatchling to uv_build and made `overture.schema` a PEP 420 namespace package. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Regenerated baseline schemas for optional `sources[].dataset`. ([#633](https://github.com/OvertureMaps/schema/issues/633))
- Rename theme packages to improve sorting and grouping characteristics. ([#649](https://github.com/OvertureMaps/schema/issues/649))
- Regenerated the JSON Schema baseline to include the `$schema` dialect declaration. ([#671](https://github.com/OvertureMaps/schema/issues/671))
