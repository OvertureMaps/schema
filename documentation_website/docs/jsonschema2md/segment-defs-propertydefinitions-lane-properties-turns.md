# Untitled array in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/lane/properties/turns
```



> If turns is omitted, the default turning options for a lane are assumed. The default turning options depend on the lane location. The leftmost lane for a given travel direction has \[left, through] by default. A rightmost lane has \[right, through] by default. Evidently if there is a single lane for a given direction, it is both leftmost and rightmost and consequently has \[left, through, right]. A middle lane has \[through] by default.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## turns Type

`string[]`

## turns Constraints

**minimum number of items**: the minimum number of items for this array is: `1`

**unique items**: all items in this array must be unique. Duplicates are not allowed.
