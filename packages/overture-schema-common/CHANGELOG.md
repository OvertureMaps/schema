## [2.0.0] - 2026-09-02

### Breaking Changes

- Removed the `level` default of `0`; a feature parsed without a level now yields `None` instead of `0`, and the field description states that absence means visual level. ([#696](https://github.com/OvertureMaps/schema/issues/696))

### Features

- Made `sources[].dataset` optional; sources entries no longer require a `dataset` value. ([#633](https://github.com/OvertureMaps/schema/issues/633))
- Added an `overture` tag provider that marks every entry point built on `OvertureFeature`, so consumers can select those types by tag instead of importing `OvertureFeature`. ([#668](https://github.com/OvertureMaps/schema/issues/668))

### Miscellaneous

- Declared explicit version floors for workspace dependencies. ([#557](https://github.com/OvertureMaps/schema/issues/557))
- Raised the minimum pydantic version to 2.13.0. ([#593](https://github.com/OvertureMaps/schema/issues/593))
- Migrated the build backend from hatchling to uv_build and made `overture.schema` a PEP 420 namespace package. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Added `deepdiff` to the development dependency group. ([#622](https://github.com/OvertureMaps/schema/issues/622))
