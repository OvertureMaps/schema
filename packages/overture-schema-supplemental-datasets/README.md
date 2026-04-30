# Overture Schema Supplemental Datasets

Supplemental datasets for Overture Maps that extend the core schema with
additional community-recognized geographic features not part of the reference map.

## What are Supplemental Datasets?

Supplemental datasets are **not part of the reference map**. They differ from
the core Overture themes (addresses, base, buildings, divisions, places,
transportation) in several key ways:

- **Single-source** - Each supplemental dataset comes from one data provider, not conflated from multiple sources
- **No GERS IDs** - Features don't have Global Entity Reference System identifiers used for entity resolution
- **Independent release cadence** - Not tied to monthly reference map updates
- **Additive data** - New rows of map data, not new properties on existing features
- **No reference links** - Don't link to reference map features via GERS IDs
- **No theme property** - Unlike reference map features, supplemental datasets do not include a `theme` property

Supplemental datasets are identified only by their `type` property, not by theme.

## Available Datasets

### Colloquial Areas

Represents informal, culturally defined, or commonly referenced areas that do not
correspond to official administrative boundaries. Unlike countries, states, counties,
or cities whose boundaries are legally defined, colloquial areas evolve from cultural,
historical, economic, or linguistic identity. These areas have no official ISO codes,
no fixed administrative definitions, and frequently overlap existing divisions.

**Examples:**

- **South Florida**: A cultural and economic region typically understood to include Miami, Fort Lauderdale, and West Palm Beach. It does not match any administrative boundary.
- **East Asia**: A macro-region defined primarily by cultural and geographic context, comprising countries such as Japan, South Korea, China, Mongolia, etc.
- **Northern Italy**: Often used to refer to Italian regions north of the Po River; widely used in climate, economic, and tourism contexts.

**Colloquial areas vs. reference map themes:**
- **vs. divisions**: Lack official administrative boundaries, legal status, or government recognition—they are culturally or socially recognized regions
- **vs. places**: Represent regions and areas (polygons), not point-based business or venue locations
- **vs. addresses/buildings/transportation**: Informal geographic regions, not physical infrastructure or postal entities

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
- **Required**: id, geometry (Polygon or MultiPolygon), type, version, names, sources
- **Optional**: bbox, center_point, parent_name, wikipedia_url, wikidata

Multi-language names support primary and common translations following BCP-47 language tags.

**Note:** Supplemental datasets do not have a `theme` property, distinguishing them from reference map features.
