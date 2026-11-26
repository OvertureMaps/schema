## [2.0.1] - 2026-11-10

### Bug Fixes

- Export `Feature` from the `overture.schema.system` package root, so `from overture.schema.system import Feature` resolves the way `from overture.schema.common import OvertureFeature` already does. ([#737](https://github.com/OvertureMaps/schema/issues/737))
- Typed the model-constraint decorators to return the class they decorate, so pyright and ty keep a decorated model's fields instead of reducing it to `BaseModel`. ([#760](https://github.com/OvertureMaps/schema/issues/760))
- Fixed Pydantic validation enforcing only the last of several model constraints of the same kind (`@require_if`, `@forbid_if`, and the others): each replaced the previous one's validator, including a constraint a subclass adds to those it inherits. All of them are now enforced; generated JSON Schema already included every constraint. ([#784](https://github.com/OvertureMaps/schema/issues/784))
- Fixed the `TypeError` raised for a mismatched operand in the JSON Schema helpers (`put_required`, `put_all_of`, and siblings) printing `{target.__name__}` and `{mismatches}` literally instead of the expected type and the offending values. ([#790](https://github.com/OvertureMaps/schema/issues/790))

### Documentation

- Wrote the types of documented parameters and return values in numpydoc form, matching their annotations. ([#804](https://github.com/OvertureMaps/schema/issues/804))

### Miscellaneous

- Typed the functions that take a type as an argument with `TypeForm`, [PEP 747](https://peps.python.org/pep-0747/)'s type for a type expression: `json_schema` and `assert_json_schema_golden` take `TypeForm[BaseModel]`, `collect_types` takes `TypeForm[object]`, and `create_model`'s field definitions match pydantic 2.14's; mypy now rejects a value there that it cannot read as a type expression, which `TypeForm(...)` around the value fixes. ([#794](https://github.com/OvertureMaps/schema/issues/794))
- Raised the minimum pydantic version to 2.14, and imported `MISSING` from `pydantic` instead of `pydantic.experimental.missing_sentinel`, so importing `Omitable` no longer emits `PydanticDeprecatedSince214`. ([#810](https://github.com/OvertureMaps/schema/issues/810))


## [2.0.0] - 2026-09-02

### Features

- Ensured the `json_schema()` function includes the JSON Schema dialect (`$schema`). ([#671](https://github.com/OvertureMaps/schema/issues/671))

### Miscellaneous

- Raised the minimum pydantic version to 2.13.0. ([#593](https://github.com/OvertureMaps/schema/issues/593))
- Migrated the build backend from hatchling to uv_build and made `overture.schema` a PEP 420 namespace package. ([#618](https://github.com/OvertureMaps/schema/issues/618))
- Reserved the plain `overture` tag to `overture-schema-common` and documented its provider in the README. ([#668](https://github.com/OvertureMaps/schema/issues/668))
