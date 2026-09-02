## [2.0.0] - 2026-09-02

### Breaking Changes

- Made segment `connectors` a required field. It previously defaulted to an empty list, a value its own `min_length=2` constraint rejected, so a segment without connectors failed re-validation after a dump. Every segment in published Overture data already carries two or more connectors. ([#669](https://github.com/OvertureMaps/schema/issues/669))
- Removed the `is_max_speed_variable` default of `False`; a rule parsed without the flag now yields `None` instead of `False`. ([#696](https://github.com/OvertureMaps/schema/issues/696))

### Miscellaneous

- Declared explicit version floors for workspace dependencies. ([#557](https://github.com/OvertureMaps/schema/issues/557))
- Raised the minimum pydantic version to 2.13.0. ([#593](https://github.com/OvertureMaps/schema/issues/593))
- Migrated the build backend from hatchling to uv_build and made `overture.schema` a PEP 420 namespace package. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Regenerated baseline schemas for optional `sources[].dataset`. ([#633](https://github.com/OvertureMaps/schema/issues/633))
- Rename theme packages to improve sorting and grouping characteristics. ([#649](https://github.com/OvertureMaps/schema/issues/649))
- Regenerated the JSON Schema baseline to include the `$schema` dialect declaration. ([#671](https://github.com/OvertureMaps/schema/issues/671))
