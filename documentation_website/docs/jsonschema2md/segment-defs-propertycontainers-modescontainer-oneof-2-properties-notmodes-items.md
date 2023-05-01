# Untitled string in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyContainers/modesContainer/oneOf/2/properties/notModes/items
```

Enumerates possible travel modes. Some modes represent groups of modes.

> motorVehicle includes car, truck and motorcycle

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## items Type

`string`

## items Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value            | Explanation |
| :--------------- | :---------- |
| `"motorVehicle"` |             |
| `"car"`          |             |
| `"truck"`        |             |
| `"motorcycle"`   |             |
| `"foot"`         |             |
| `"bicycle"`      |             |
