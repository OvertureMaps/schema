# Supplemental Datasets

**Supplemental datasets** extend Overture Maps with additional geographic data that is not part of the core reference map. They provide valuable map data from single sources that complement—but remain separate from—the multi-source, conflated reference map.

## Characteristics

- **Not part of the reference map corpus** - Supplemental datasets add new rows of map data rather than new properties to existing features
- **Single-source** - Each supplemental dataset comes from a single data provider, not conflated from multiple sources
- **No GERS IDs** - Features do not have Global Entity Reference System (GERS) identifiers used for entity resolution
- **Independent release cadence** - Updates follow their own schedule, not tied to monthly reference map releases
- **No reference map links** - Features do not link to reference map features via GERS IDs
- **No theme property** - Unlike reference map features, supplemental datasets do not include a `theme` property

## Supplemental vs. Reference Map

Supplemental datasets are distinguished from reference map themes by the **absence of the `theme` property**:

**Current reference map themes** (with `theme` property):
- addresses
- buildings
- divisions
- places
- transportation
- base (may transition to supplemental datasets in the future—see Future Direction below)

**Supplemental datasets** (no `theme` property):
- Identified only by their `type` property
- Do not belong to any theme
- Single-source data that extends the map without entity resolution

## Current Supplemental Datasets

### colloquial_area

Represents informal, culturally defined, or commonly referenced areas that do not correspond to official administrative boundaries. Unlike countries, states, counties, or cities whose boundaries are legally defined, colloquial areas evolve from cultural, historical, economic, or linguistic identity. These areas have no official ISO codes, no fixed administrative definitions, and frequently overlap existing divisions. They are nonetheless highly important for search, mapping, analytics, and user experience, particularly when users expect them to behave like meaningful geographic entities.

**Examples:**
- **South Florida**: A cultural and economic region typically understood to include Miami, Fort Lauderdale, and West Palm Beach. It does not match any administrative boundary.
- **East Asia**: A macro-region defined primarily by cultural and geographic context, comprising countries such as Japan, South Korea, China, Mongolia, etc.
- **Northern Italy**: Often used to refer to Italian regions north of the Po River; widely used in climate, economic, and tourism contexts.

**Properties:**
- `type` (required) - Always `colloquial_area`
- `version` (required) - Feature version number
- `names` (required) - Multi-language names with primary and common translations
- `sources` (required) - Source attribution
- `bbox` (optional) - Bounding box as [west, south, east, north]
- `center_point` (optional) - Representative point for labeling/geocoding
- `parent_name` (optional) - Name of containing geographic area
- `wikipedia_url` (optional) - Wikipedia article URL
- `wikidata` (optional) - Wikidata identifier

**Geometry:** Polygon or MultiPolygon

## How Supplemental Datasets Complement the Reference Map

Supplemental datasets fill gaps in the reference map by providing recognized geographic data that doesn't fit standard entity-based themes:

**Colloquial areas vs. core reference map themes:**
- **vs. divisions**: Colloquial areas lack official administrative boundaries, legal status, or government recognition—they are culturally or socially recognized regions
- **vs. places**: Colloquial areas represent regions and areas (polygons), not point-based business or venue locations
- **vs. addresses/buildings/transportation**: Colloquial areas are informal geographic regions, not physical infrastructure or postal entities

Supplemental datasets provide valuable geographic data that users recognize, reference, and search for—even when these features don't meet the strict criteria for inclusion in the multi-source, conflated reference map.

## Future Direction

The supplemental datasets model may expand to reorganize base data. Currently listed as a reference map theme, base data could transition to six clearly-labeled supplemental datasets. This would:

- **Clarify purpose**: Distinguish base data as foundational geographic data layers, not a "basemap" in the cartographic sense
- **Separate from reference map**: Move base out of the core entity-focused reference map (addresses, buildings, divisions, places, transportation)
- **Improve organization**: Split into six clearly-labeled datasets for better discoverability

**Proposed OSM-sourced datasets** (4):
- Infrastructure
- Land
- Land Use
- Water

**Proposed cartographic datasets** (2):
- Bathymetry
- Land Cover

This reorganization would maintain the same quality standards and data while reducing user confusion, particularly around feature identification, entity resolution, and the role of GERS IDs.

## Adding New Supplemental Datasets

The supplemental-datasets directory can accommodate additional feature types for community-contributed datasets that provide value beyond the core Overture schema, as long as they meet the supplemental dataset criteria above.
