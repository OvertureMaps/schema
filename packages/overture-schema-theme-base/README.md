# Overture Schema Base Theme

Feature types for the Overture Maps base theme: `Bathymetry`, `Infrastructure`, `Land`, `LandCover`, `LandUse`, and `Water`, plus the enums and structures they share.

## Installation

```bash
pip install overture-schema-theme-base
```

To get every theme at once, install the `overture-schema` metapackage instead.

## Usage

```python
from overture.schema.base import Land, Water
```

This package registers its feature types through entry points, so Overture tools
installed alongside it find them automatically. For example, `overture-schema list-types`
from `overture-schema-cli` lists them, and `overture-schema validate` checks data against
them.

See the [schema guide](https://github.com/OvertureMaps/schema/blob/main/guides/README.md) for working with the models.
