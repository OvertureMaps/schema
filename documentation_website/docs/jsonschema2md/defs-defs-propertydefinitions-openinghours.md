# Untitled string in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyContainers/applyDuringContainer/properties/applyDuring
```

Time span or time spans during which something is open or active, specified in the OSM opening hours specification:
<https://wiki.openstreetmap.org/wiki/Key:opening_hours/specification>

> The "pattern" is just a placeholder. We assume we can specify a regular expression to give *some* degree of initial lexical validation, but higher-level validation will have to be done outside of JSON schema.
> Reasons for using the OSM opening hours specification for transportation rule time restrictions are documented in <https://github.com/OvertureMaps/schema-wg/pull/10>

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## applyDuring Type

`string`

## applyDuring Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^Mo-Sa 09:00-12:00( closed)?, We 15:00-18:00( closed)?$
```

[try pattern](https://regexr.com/?expression=%5EMo-Sa%2009%3A00-12%3A00\(%20closed\)%3F%2C%20We%2015%3A00-18%3A00\(%20closed\)%3F%24 "try regular expression with regexr.com")
