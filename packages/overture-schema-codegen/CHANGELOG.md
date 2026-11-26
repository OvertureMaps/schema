## [2.0.1] - 2026-11-10

### Bug Fixes

- Fixed the generated Markdown reference on Python 3.11+ showing enum values as `Class.MEMBER` (`DivisionSubtype.COUNTRY` instead of `country`) in model-constraint notes, example tables, and enum-member `Literal` types. ([#811](https://github.com/OvertureMaps/schema/issues/811))

### Documentation

- Wrote the types of documented parameters and return values in numpydoc form, matching their annotations. ([#804](https://github.com/OvertureMaps/schema/issues/804))

### Miscellaneous

- Published the package README as the PyPI project description, and added maintainers and project URLs to the package metadata. ([#734](https://github.com/OvertureMaps/schema/issues/734))
- Made the package type-check cleanly under every supported Python version, not only 3.10. ([#782](https://github.com/OvertureMaps/schema/issues/782))
- Typed `UnionSpec.source_annotation`, `extract_union`'s annotation and `load_examples`'s validation type as `TypeForm[BaseModel]`, [PEP 747](https://peps.python.org/pep-0747/)'s type for a type expression, so mypy checks them against pydantic 2.14's `TypeAdapter`; the package now requires `typing-extensions` 4.13.0 or newer. ([#794](https://github.com/OvertureMaps/schema/issues/794))


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
