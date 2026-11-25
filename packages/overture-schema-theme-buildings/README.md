# Overture Schema Buildings Theme

Feature types for the Overture Maps buildings theme: `Building` and `BuildingPart`, plus the enums and structures they share.

## Installation

```bash
pip install overture-schema-theme-buildings
```

To get every theme at once, install the `overture-schema` metapackage instead.

## Usage

```python
from overture.schema.buildings import Building, BuildingPart
```

This package registers its feature types through entry points, so Overture tools
installed alongside it find them automatically. For example, `overture-schema list-types`
from `overture-schema-cli` lists them, and `overture-schema validate` checks data against
them.

See the [schema guide](https://github.com/OvertureMaps/schema/blob/main/guides/README.md) for working with the models.
