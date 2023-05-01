# Untitled undefined type in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/roadName/oneOf/1/items/allOf/0
```

Properties defining the range of positions on the segment where a rule is active.

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## 0 Type

unknown

# 0 Properties

| Property            | Type    | Required | Nullable       | Defined by                                                                                                                                                                                               |
| :------------------ | :------ | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [applyAt](#applyat) | `array` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-linearlyreferencedrange.md "transportation/segment.yaml#/$defs/propertyContainers/applyAtRangeContainer/properties/applyAt") |

## applyAt

Represents a non-empty range of positions along a path as a pair linearly-referenced positions. For example, the pair \[0.25, 0.5] represents the range beginning 25% of the distance from the start of the path and ending 50% oof the distance from the path start.

> Ideally we would enforce sorted order of this pair, but sorting assertions aren't (yet?) supported by JSON schema.

`applyAt`

*   is optional

*   Type: `number[]`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-linearlyreferencedrange.md "transportation/segment.yaml#/$defs/propertyContainers/applyAtRangeContainer/properties/applyAt")

### applyAt Type

`number[]`

### applyAt Constraints

**maximum number of items**: the maximum number of items for this array is: `2`

**minimum number of items**: the minimum number of items for this array is: `2`

**unique items**: all items in this array must be unique. Duplicates are not allowed.
