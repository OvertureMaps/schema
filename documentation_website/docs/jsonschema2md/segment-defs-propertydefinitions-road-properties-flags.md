# Untitled array in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flags
```

Set of boolean attributes applicable to roads. May be specified either as a single flag array of flag values, or as an array of flag rules.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## flags Type

an array of merged types ([Details](segment-defs-propertydefinitions-road-properties-flags-items.md))

## flags Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.
