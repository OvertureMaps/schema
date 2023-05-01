# Untitled undefined type in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/properties/properties/allOf/2/allOf/0/then
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## then Type

unknown

# then Properties

| Property                    | Type     | Required | Nullable       | Defined by                                                                                                                                                                                                                   |
| :-------------------------- | :------- | :------- | :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [road](#road)               | `object` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road.md "transportation/segment.yaml#/properties/properties/allOf/2/allOf/0/then/properties/road")                                            |
| [widthMeters](#widthmeters) | `number` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-properties-properties-allof-2-allof-0-then-properties-widthmeters.md "transportation/segment.yaml#/properties/properties/allOf/2/allOf/0/then/properties/widthMeters") |

## road

Properties for segments whose segment subType is road. The road subType includes any variety of road, street, or path, including dedicated paths for walking and cycling.

`road`

*   is optional

*   Type: `object` ([Details](segment-defs-propertydefinitions-road.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road.md "transportation/segment.yaml#/properties/properties/allOf/2/allOf/0/then/properties/road")

### road Type

`object` ([Details](segment-defs-propertydefinitions-road.md))

### road Default Value

The default value is:

```json
{}
```

## widthMeters

Edge-to-edge width of the road modeled by this segment, in meters.
Examples: (1) If this segment models a carriageway without sidewalk, this value represents the edge-to-edge width of the carriageway, inclusive of any shoulder. (2) If this segment models a sidewalk by itself, this value represents the edge-to-edge width of the sidewalk. (3) If this segment models a combined sidewalk and carriageway, this value represents the edge-to-edge width inclusive of sidewalk.

`widthMeters`

*   is optional

*   Type: `number`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-properties-properties-allof-2-allof-0-then-properties-widthmeters.md "transportation/segment.yaml#/properties/properties/allOf/2/allOf/0/then/properties/widthMeters")

### widthMeters Type

`number`

### widthMeters Constraints

**minimum (exclusive)**: the value of this number must be greater than: `0`
