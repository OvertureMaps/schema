# Untitled string in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/properties/properties/properties/subType
```

Broad category of transportation segment.

> Should not be confused with a transport mode. A segment kind has an (implied) set of default transport modes.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## subType Type

`string`

## subType Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value     | Explanation |
| :-------- | :---------- |
| `"road"`  |             |
| `"rail"`  |             |
| `"water"` |             |
