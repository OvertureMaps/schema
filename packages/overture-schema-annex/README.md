# Overture Schema Sources

Shared models and validation tools for the data sources catalog used across
Overture Maps themes.

## Contents

- `overture.schema.sources` module, exporting the `Sources` aggregate model
  and related dataset structures.
- CLI helper (`python -m overture.schema.sources`) to validate sources JSON
  files against the schema.
- Reference examples and counterexamples under `schema/reference` illustrating
  valid and invalid source structures.

## Usage

```bash
uv run python -m overture.schema.sources path/to/sources.json
```

This validates the payload and reports schema violations with dataset-level
context. The package also registers an `overture.models` entry point for the
`Sources` model so tools can discover the schema automatically.