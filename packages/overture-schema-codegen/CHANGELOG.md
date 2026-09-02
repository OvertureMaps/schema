## [2.0.0] - 2026-09-02

### Bug Fixes

- Fixed RootModel entry points producing a spurious `root` column and going undocumented: they are now skipped from PySpark generation and documented as markdown type aliases (a self-referential RootModel now raises a clear error instead of recursing). ([#593](https://github.com/OvertureMaps/schema/issues/593))
- Fixed `overture-codegen list` printing a raw `typing.Annotated[...]` expression for discriminated-union entry points such as `Segment`; entries now list by their entry-point class name. ([#668](https://github.com/OvertureMaps/schema/issues/668))

### Documentation

- Rewrote the README's programmatic-use section against the current `analyze_type()` signature, which returns a `FieldShape` tuple rather than the removed `TypeInfo`/`TypeKind`. ([#668](https://github.com/OvertureMaps/schema/issues/668))

### Miscellaneous

- Declared explicit version floors for workspace dependencies. ([#557](https://github.com/OvertureMaps/schema/issues/557))
- Migrated the build backend to uv_build and stopped emitting `__init__.py` in the generated PySpark trees, making them PEP 420 namespace packages. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Updated scaffold test expectations for optional `sources[].dataset`. ([#633](https://github.com/OvertureMaps/schema/issues/633))
- Rename theme packages to improve sorting and grouping characteristics. ([#649](https://github.com/OvertureMaps/schema/issues/649))
