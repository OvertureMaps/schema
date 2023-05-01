# Untitled array in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/properties/properties/properties/connectors
```

List of connector nodes this segment is physically connected to.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## connectors Type

`string[]`

## connectors Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.

## connectors Default Value

The default value is:

```json
[]
```
