# Untitled string in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/turnOption
```

Option for turning at a junction between segments

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## turnOption Type

`string`

## turnOption Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value           | Explanation |
| :-------------- | :---------- |
| `"mergeLeft"`   |             |
| `"slightLeft"`  |             |
| `"left"`        |             |
| `"sharpLeft"`   |             |
| `"through"`     |             |
| `"mergeRight"`  |             |
| `"slightRight"` |             |
| `"right"`       |             |
| `"sharpRight"`  |             |
| `"reverse"`     |             |
