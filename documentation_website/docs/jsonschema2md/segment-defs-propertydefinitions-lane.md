# Untitled object in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/lane
```

Properties for a single lane of traffic.

> TODO: HOV lane modeling. TODO: The turns model fails to capture cases where there may be
> a combined maneuver (slightLeft+slideRight). How important
> is this? <https://wiki.openstreetmap.org/wiki/Key:turn>

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## lane Type

`object` ([Details](segment-defs-propertydefinitions-lane.md))

all of

*   one (and only one) of

    *   not

        *   any of

            *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-0-not-anyof-0.md "check type definition")

            *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-0-not-anyof-1.md "check type definition")

    *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-1.md "check type definition")

    *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-2.md "check type definition")

# lane Properties

| Property                | Type     | Required | Nullable       | Defined by                                                                                                                                                                                      |
| :---------------------- | :------- | :------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [direction](#direction) | `string` | Required | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-lane-properties-direction.md "transportation/segment.yaml#/$defs/propertyDefinitions/lane/properties/direction") |
| [turns](#turns)         | `array`  | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-lane-properties-turns.md "transportation/segment.yaml#/$defs/propertyDefinitions/lane/properties/turns")         |

## direction



`direction`

*   is required

*   Type: `string`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-lane-properties-direction.md "transportation/segment.yaml#/$defs/propertyDefinitions/lane/properties/direction")

### direction Type

`string`

### direction Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value           | Explanation |
| :-------------- | :---------- |
| `"forward"`     |             |
| `"backward"`    |             |
| `"bothWays"`    |             |
| `"alternating"` |             |
| `"reversible"`  |             |

## turns



> If turns is omitted, the default turning options for a lane are assumed. The default turning options depend on the lane location. The leftmost lane for a given travel direction has \[left, through] by default. A rightmost lane has \[right, through] by default. Evidently if there is a single lane for a given direction, it is both leftmost and rightmost and consequently has \[left, through, right]. A middle lane has \[through] by default.

`turns`

*   is optional

*   Type: `string[]`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-lane-properties-turns.md "transportation/segment.yaml#/$defs/propertyDefinitions/lane/properties/turns")

### turns Type

`string[]`

### turns Constraints

**minimum number of items**: the minimum number of items for this array is: `1`

**unique items**: all items in this array must be unique. Duplicates are not allowed.
