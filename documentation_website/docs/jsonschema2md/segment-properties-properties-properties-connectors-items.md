# Untitled string in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/properties/properties/properties/connectors/items
```



> Pattern is just a placeholder. Each entry in this array is the GERS ID of a transportation connector feature.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## items Type

`string`

## items Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[a-z]+Connector$
```

[try pattern](https://regexr.com/?expression=%5E%5Ba-z%5D%2BConnector%24 "try regular expression with regexr.com")
