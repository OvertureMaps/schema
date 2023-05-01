# Untitled array in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flow/items/properties/dividers
```

How the lanes are divided within this flow rule. There must be exactly one divider for each lane, so a flow rule with N lanes must have N-1 dividers. For two consecutive lane items (lanes\[i], lanes\[i+1]), the divider between them is given by dividers\[i].

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## dividers Type

`string[]`

## dividers Default Value

The default value is:

```json
[]
```
