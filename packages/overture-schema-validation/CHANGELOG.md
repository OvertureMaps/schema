## [2.0.1] - 2026-11-10

### Bug Fixes

- `validate()` and `validate_json()` no longer accept `None`. The non-discriminated union was built with `reduce(or_, models, None)`, whose `None` initializer made the resulting union admit `None`, so `validate(None)` and `validate_json("null")` returned successfully instead of raising `ValidationError`. ([#720](https://github.com/OvertureMaps/schema/issues/720))

### Miscellaneous

- Made the package pass mypy against pydantic 2.14, which annotates `TypeAdapter`'s argument as `TypeForm`, [PEP 747](https://peps.python.org/pep-0747/)'s type for a value that is itself a type expression; runtime behavior is unchanged. ([#794](https://github.com/OvertureMaps/schema/issues/794))
- Raised the minimum pydantic version to 2.14, matching `overture-schema-system`. ([#810](https://github.com/OvertureMaps/schema/issues/810))


## [2.0.0] - 2026-09-02

### Documentation

- Corrected the README's usage examples, which showed `validate_json` accepting the flat tabular shape rather than GeoJSON. ([#668](https://github.com/OvertureMaps/schema/issues/668))

### Miscellaneous

- Migrated the build backend from hatchling to uv_build and made `overture.schema` a PEP 420 namespace package. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Extracted `validate()` and `validate_json()` into the new `overture-schema-validation` package, off the shared `overture.schema` namespace root. ([#622](https://github.com/OvertureMaps/schema/issues/622))
