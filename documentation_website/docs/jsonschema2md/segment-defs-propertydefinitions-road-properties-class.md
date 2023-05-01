# Untitled string in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/class
```

Captures the kind of road and its position in the road network hierarchy.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## class Type

`string`

## class Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value            | Explanation |
| :--------------- | :---------- |
| `"unknown"`      |             |
| `"primary"`      |             |
| `"secondary"`    |             |
| `"tertiary"`     |             |
| `"residential"`  |             |
| `"parkingAisle"` |             |
| `"driveway"`     |             |
| `"footway"`      |             |
| `"cycleway"`     |             |

## class Default Value

The default value is:

```json
{
  "enum": [
    "unknown"
  ]
}
```
