# Untitled number in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/properties/properties/allOf/2/allOf/0/then/properties/widthMeters
```

Edge-to-edge width of the road modeled by this segment, in meters.
Examples: (1) If this segment models a carriageway without sidewalk, this value represents the edge-to-edge width of the carriageway, inclusive of any shoulder. (2) If this segment models a sidewalk by itself, this value represents the edge-to-edge width of the sidewalk. (3) If this segment models a combined sidewalk and carriageway, this value represents the edge-to-edge width inclusive of sidewalk.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## widthMeters Type

`number`

## widthMeters Constraints

**minimum (exclusive)**: the value of this number must be greater than: `0`
