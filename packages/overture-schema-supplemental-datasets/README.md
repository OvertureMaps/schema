# Overture Schema Supplemental Datasets

Supplemental datasets for Overture Maps that extend the core schema with
additional community-recognized geographic features.

## What are Supplemental Datasets?

Supplemental datasets are **not part of the reference map**. They differ from
the core Overture themes (addresses, base, buildings, divisions, places,
transportation) in several ways:

- **Single-source** - Each supplemental dataset comes from one data provider
- **No GERS IDs** - Features don't have Global Entity Reference System identifiers
- **Independent release cadence** - Not tied to monthly reference map updates
- **Additive data** - New rows of map data, not new properties on existing features
- **No reference links** - Don't link to reference map features via GERS IDs
- **No theme property** - Unlike reference map features, supplemental datasets do not use the `theme` property

## Available Datasets

### Colloquial Areas

Represents informally-defined geographic areas known by common names but not
necessarily having official administrative status. Examples include:

- Neighborhoods: SoHo (London), Greenwich Village (NYC), Latin Quarter (Paris)
- Regional areas: East Asia, South Florida, Northern Iran, the Midwest
- Cultural districts: Silicon Valley, the Rust Belt, Wine Country

Colloquial areas complement the official administrative divisions in the
reference map by capturing how people naturally refer to places.

## Usage

```python
from overture.schema.supplemental import ColloquialArea

# Validate and work with colloquial area features
area = ColloquialArea.model_validate(geojson_feature)
print(f"Area: {area.properties.names.primary}")
print(f"Parent: {area.properties.parent_name}")
```

## Data Model

Each colloquial area includes:
- Standard properties (id, geometry, type, version, sources)
- Multi-language names with primary and common translations
- Polygon or MultiPolygon geometry
- Optional properties:
  - Center point for labeling
  - Bounding box (in properties)
  - Parent geographic area name
  - Wikipedia and Wikidata references

**Note:** Supplemental datasets do not have a `theme` property, distinguishing them from reference map features.
