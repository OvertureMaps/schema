# Creating Building Parts from OpenStreetMap Data

## Background
The Overture schema's 3D parts proposal mandates that building parts be explicitly associated with a specific building. While OpenStreetMap (OSM) offers a building relation (relations with `type=building`) to facilitate this association, it is infrequently utilized. Consequently, we must rely on our own processing methods to derive this association. This document outlines the methodology used in overture for processing OSM data to associate building parts with buildings.

## Description
The process involves two primary methods:
- Explicit Assignment using the building relation.
- Implicit Assignment where outlines spatially contain their constituent parts.

### Building Relation Association (explicit assignment plus spatial)
STEPS:
1. Identify Relations: Search for relations with `type=building`.
1. Validate Relations
    1. Allow relations that contain exactly one member with `role=outline`
    1. Allow relations with an outline that is either a way or a multipolygon relation with a valid geometry.
    1. Allow relations with at least one member with `role=part`
1. Identify Outlines: Identify each relation member with the `role=outline` as a building outline.
1. Add Explicit Parts: Add each relation member with the `role=part` as a building part.
1. Add Implicit Parts: Add each `building:part=*` that are spatially within the outline of any valid building relation as a building part.
1. Associate parts to Buildings: Associate building parts with a building using the overture ID of the relation outline.

### Building Way Association (implicit spatial assignment)
STEPS:
1. Exclude Previously Assigned: Ignore any outlines/parts ways/relations that were assigned in the previous step.
1. Identify Potential Buildings: Find all ways or `type=multipolygon` relations tagged with `building` that is not "no".
1. Identify Building Parts: Locate all ways or `type=multipolygon` relations tagged with `building:part` that is not "no".
1. Spatial Join: Perform a spatial join to find all outlines (from step 2) that completely contain a part (from step 3).
1. Associate Buildings to Parts: Successfully contained parts will have their `building_id` assigned to indicate that the part is associated with that building.
1. Exclude Orphaned Parts: Parts not contained by any outline will be omitted, as Overture does not allow orphaned parts without a known parent.

### FILTER ORPHANS
STEPS:
1. Remove Redundant Parts: Eliminate all parts that are the only part associated with a building and share the same geometry as the building. This step helps filter out many OSM buildings tagged with both `building=yes` and `building:part=yes` if no other parts are associated with the building.

## Considerations
 - Geometric Accuracy: Due to discrepancies in how spatial functions interpret containment across different query engines, a small buffer might be applied to the building geometry to ensure parts are appropriately included.
 - Data Integrity: Ensure that all data manipulations preserve the integrity and accuracy of the original OSM data, adhering to both Overture and OSM standards.

This document serves as a guideline for developing a robust system to assign building parts in Overture using OpenStreetMap data, ensuring comprehensive and accurate representation of building structures.

Known Issues:
 - OSM Features tagged with both `building` and `building:part` are considered both an outline and a part, resulting in two separate Overture features (a `type=building` and a `type=building_part`) referring to the same OSM object. Although they are the same OSM object they will be represented in Overture as two separate objects with different IDs.
 - When `building=yes` and `building:part=yes` it is imposible to know what the `height` tag refers to. It may refer to the height of the entire building (the heighest point of all parts) as is stated in the OSM wiki, or in some cases it refers to the height of the part. It is recomended to either remove the `height` from such features or split the features into a building and a separate part feature and assign the proper height to each. In these cases Overture will assume the height is the height of the building as stated in the wiki.
 - When `building=yes` and `building:part=yes` it is imposible to know whether the characteristics tags refer to the building or the building part. It is recomended to either remove the tags from such features or split the features into a building and a separate part feature and assign the proper tags to each. In these cases Overture will assume the each tag refers to both the building and the part.
 - Outlines that are not completely covered by parts will not render very well. Renderers may render the outline using the height of the building and then replace areas where there are parts with the height of the parts. Unfortunately this can cause strange artifacts around the outside of the building if the parts don't completely cover it.
