# Schema Conventions and Guidelines
## The Basics
1. [JSON Schema](https://json-schema.org/) is used to define the Overture schema
2. [GeoJSON](https://geojson.org/) is used as a canonical geospatial format
	i.e. GeoJSON provides us a mental model and language to express data constructions, without being the data format in which the Overture data is published
## Schema notation conventions
   - `snake_case` is used for all property names, string enumeration members, and string-valued enumeration equivalents
   - boolean properties have a prefix verb "is" or "has" in a way that grammatically makes sense
      e.g.
	     has_street_lights=true
		 is_accessible=false

## Core Concepts
### Overture Feature Types

all Overture Feature Types are described in the Overture Schema.

Overture Features Types:

1.  Have a type.
2.  Have geometry, where the type of geometry is constrained by the feature type.
3.  Are strongly-typed, _i.e._ the feature type constrains the geometry and properties.
4.  Have properties, which may include a core set of "flat" properties and additional properties with a nested structure.
5.  Have an ID property which is globally unique within the ID-space of the entire Overture data distribution version. For some feature types, the ID is registered with GERS and is a GERS ID.
6.  May have custom user extension properties.

## Feature types

Overture Features Types are strongly-typed. Feature Types are defined by three core properties:

-   `theme` is a mandatory property analogous to "layer".
    -   The term is deliberately chosen to avoid some of the baggage that goes along with the word "layer".
    -   Examples: `transportation`, `buildings`, `places`, `administrative`
-   `type` is a mandatory property representing a feature type within the theme:
    -   Example: `theme=transportation`, `type=segment`
    -   Example: `theme=buildings`, `type=building`
-   `subType` is an optional property which can further refine the feature type within.
    -   Example: `theme=transportation`, `type=segment`, `subType=road`

## Relations
	low-cardinality directed relations are stored as ID references on the source feature

## Quantities and units
### Measurements
	All measurements are expressed in SI units. The exact unit is confirmed in the specification of the property but is not repeated in the data

### Regulations and restrictions
	All quantities that related to posted or ordenance regulations and restrictions are expressed in the same units as as used in the regulation. The unit is explicitly included with the property in the data.

### Opening hours/validity Periods
	Opening Hours and the time frame during which time dependent properties are applicable are indicated following the [OSM Opening Hours specification] (https://wiki.openstreetmap.org/wiki/Key:opening_hours/specification)

## Extensions
Overture allows for add hoc extensions beyond what is described in the schema. All extensions are prefixed with `ext`
Extensions can be provided at the theme level, the type level or the property level.

    -insert example for property, feature and theme-
