# Untitled array in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits/items/properties/lanes
```

Optionally specifies the lanes to which the speed limit rule applies. If omitted, the rule applies to all lanes.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## lanes Type

`integer[]`

## lanes Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.
