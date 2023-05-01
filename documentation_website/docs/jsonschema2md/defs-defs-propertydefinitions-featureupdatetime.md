# Untitled string in Overture Maps Transportation Segment Schema Schema

```txt
defs.yaml#/$defs/propertyContainers/overtureFeaturePropertiesContainer/properties/updateTime
```

Timestamp when the feature was last updated

> Pattern is used as a fallback because not all JSON schema implementations treat "format" as an assertion, for some it is only an annotation.
> A somewhat more compact approach would be to reference the Overture version where the feature last changed instead of the update time, and expect clients to do a lookup if they really care about the time.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                 |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [defs.yaml\*](../../../../../../../tmp/jsonschema/schema/defs.yaml "open original schema") |

## updateTime Type

`string`

## updateTime Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[1-9]\d{3}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[-+]\d{2}:\d{2})$
```

[try pattern](https://regexr.com/?expression=%5E%5B1-9%5D%5Cd%7B3%7D-%5Cd%7B2%7D-%5Cd%7B2%7DT%5Cd%7B2%7D%3A%5Cd%7B2%7D%3A%5Cd%7B2%7D\(Z%7C%5B-%2B%5D%5Cd%7B2%7D%3A%5Cd%7B2%7D\)%24 "try regular expression with regexr.com")

**date time**: the string must be a date time string, according to [RFC 3339, section 5.6](https://tools.ietf.org/html/rfc3339 "check the specification")
