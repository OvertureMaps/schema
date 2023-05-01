# Untitled string in Overture Maps Transportation Segment Schema Schema

```txt
defs.yaml#/$defs/propertyDefinitions/language/oneOf/1
```



> The "pattern" is mostly a placeholder. It captures the language\[-script]\[-region] variation of BCP47 but not the "grandfathered" values and other variants and extensions.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                 |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [defs.yaml\*](../../../../../../../tmp/jsonschema/schema/defs.yaml "open original schema") |

## 1 Type

`string`

## 1 Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[a-zA-Z]{2,3}(-[a-zA-Z]{4})?(-[a-zA-Z]{2})?$
```

[try pattern](https://regexr.com/?expression=%5E%5Ba-zA-Z%5D%7B2%2C3%7D\(-%5Ba-zA-Z%5D%7B4%7D\)%3F\(-%5Ba-zA-Z%5D%7B2%7D\)%3F%24 "try regular expression with regexr.com")
