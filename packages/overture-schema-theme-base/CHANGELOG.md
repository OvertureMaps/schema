## [2.0.1] - 2026-11-10

### Documentation

- Explained in the `Water` docstring that `"physical"` water features overlap `"ocean"` and other water features by design, and fixed the `subytpe` typo. ([#780](https://github.com/OvertureMaps/schema/issues/780))
- Wrote the types of documented parameters and return values in numpydoc form, matching their annotations, and replaced the underlined `Ocean`, `Physical` and `Inland Water` headings in the `Water` description with bold headings. ([#804](https://github.com/OvertureMaps/schema/issues/804))

### Miscellaneous

- Raised the minimum pydantic version to 2.14, matching `overture-schema-system`. ([#810](https://github.com/OvertureMaps/schema/issues/810))


## [2.0.0] - 2026-09-02

### Breaking Changes

- Made `class` and `subtype` required on `Land` and `Water`, matching `Infrastructure` and `LandUse`; constructing either without them now raises instead of falling back to `land`/`water`. ([#696](https://github.com/OvertureMaps/schema/issues/696))
- Base feature models that inherit `Stacked` (`Infrastructure`, `Land`, `LandUse`, and `Water`) now yield `None` instead of `0` when parsed without a `level`. ([#696](https://github.com/OvertureMaps/schema/issues/696))

### Miscellaneous

- Declared explicit version floors for workspace dependencies. ([#557](https://github.com/OvertureMaps/schema/issues/557))
- Raised the minimum pydantic version to 2.13.0. ([#593](https://github.com/OvertureMaps/schema/issues/593))
- Migrated the build backend from hatchling to uv_build and made `overture.schema` a PEP 420 namespace package. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Regenerated baseline schemas for optional `sources[].dataset`. ([#633](https://github.com/OvertureMaps/schema/issues/633))
- Rename theme packages to improve sorting and grouping characteristics. ([#649](https://github.com/OvertureMaps/schema/issues/649))
- Regenerated the JSON Schema baseline to include the `$schema` dialect declaration. ([#671](https://github.com/OvertureMaps/schema/issues/671))
