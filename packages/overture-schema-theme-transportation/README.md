# Overture Schema Transportation Theme

Feature types for the Overture Maps transportation theme: `Connector` and `Segment`, plus the enums and structures they share.

## Installation

```bash
pip install overture-schema-theme-transportation
```

To get every theme at once, install the `overture-schema` metapackage instead.

## Usage

```python
from overture.schema.transportation import Connector, Segment
```

`Segment` is a discriminated union of `RoadSegment`, `RailSegment`, and `WaterSegment`,
not a class. Validate it through a Pydantic `TypeAdapter`:

```python
from pydantic import TypeAdapter
from overture.schema.transportation import Segment

segment = TypeAdapter(Segment).validate_json(geojson_text)
```

This package registers its feature types through entry points, so Overture tools
installed alongside it find them automatically. For example, `overture-schema list-types`
from `overture-schema-cli` lists them, and `overture-schema validate` checks data against
them.

See the [schema guide](https://github.com/OvertureMaps/schema/blob/main/guides/README.md) for working with the models.
