## [2.0.0] - 2026-09-02

### Breaking Changes

- Buildings and building parts parsed without a `level` now yield `None` instead of `0`, following the removal of the `Stacked.level` default. ([#696](https://github.com/OvertureMaps/schema/issues/696))

### Features

- Add `shelter` to the building `class` enum so shelter structures (e.g. public transport shelters) can receive a class value. ([#656](https://github.com/OvertureMaps/schema/issues/656))

### Miscellaneous

- Declared explicit version floors for workspace dependencies. ([#557](https://github.com/OvertureMaps/schema/issues/557))
- Raised the minimum pydantic version to 2.13.0. ([#593](https://github.com/OvertureMaps/schema/issues/593))
- Migrated the build backend from hatchling to uv_build and made `overture.schema` a PEP 420 namespace package. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Regenerated baseline schemas for optional `sources[].dataset`. ([#633](https://github.com/OvertureMaps/schema/issues/633))
- Rename theme packages to improve sorting and grouping characteristics. ([#649](https://github.com/OvertureMaps/schema/issues/649))
- Regenerated the JSON Schema baseline to include the `$schema` dialect declaration. ([#671](https://github.com/OvertureMaps/schema/issues/671))
