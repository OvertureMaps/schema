# Untitled integer in Overture Maps Transportation Segment Schema Schema

```txt
defs.yaml#/$defs/propertyContainers/overtureFeaturePropertiesContainer/properties/version
```

Version number of the feature, incremented in each Overture release where the geometry or attributes of this feature changed.

> It might be reasonable to combine "updateTime" and "version" in a single "updateVersion" field which gives the last Overture version number in which the feature changed. The downside to doing this is that the number would cease to be indicative of the "rate of change" of the feature.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                 |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [defs.yaml\*](../../../../../../../tmp/jsonschema/schema/defs.yaml "open original schema") |

## version Type

`integer`
