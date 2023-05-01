# Untitled object in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/properties/properties/allOf/0
```

Top-level properties shared by all Overture features

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## 0 Type

`object` ([Details](defs-defs-propertycontainers-overturefeaturepropertiescontainer.md))

# 0 Properties

| Property                  | Type          | Required | Nullable       | Defined by                                                                                                                                                                                       |
| :------------------------ | :------------ | :------- | :------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [theme](#theme)           | `string`      | Required | cannot be null | [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-theme.md "defs.yaml#/$defs/propertyContainers/overtureFeaturePropertiesContainer/properties/theme")                  |
| [type](#type)             | `string`      | Required | cannot be null | [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-featuretype.md "defs.yaml#/$defs/propertyContainers/overtureFeaturePropertiesContainer/properties/type")             |
| [version](#version)       | `integer`     | Required | cannot be null | [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-featureversion.md "defs.yaml#/$defs/propertyContainers/overtureFeaturePropertiesContainer/properties/version")       |
| [updateTime](#updatetime) | `string`      | Required | cannot be null | [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-featureupdatetime.md "defs.yaml#/$defs/propertyContainers/overtureFeaturePropertiesContainer/properties/updateTime") |
| `^ext.*$`                 | Not specified | Optional | cannot be null | [Untitled schema](undefined.md "undefined#undefined")                                                                                                                                            |

## theme

Top-level Overture theme this feature belongs to

`theme`

*   is required

*   Type: `string`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-theme.md "defs.yaml#/$defs/propertyContainers/overtureFeaturePropertiesContainer/properties/theme")

### theme Type

`string`

### theme Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value              | Explanation |
| :----------------- | :---------- |
| `"buildings"`      |             |
| `"transportation"` |             |

## type

Specific feature type within the theme

`type`

*   is required

*   Type: `string`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-featuretype.md "defs.yaml#/$defs/propertyContainers/overtureFeaturePropertiesContainer/properties/type")

### type Type

`string`

### type Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value         | Explanation |
| :------------ | :---------- |
| `"connector"` |             |
| `"footprint"` |             |
| `"segment"`   |             |

## version

Version number of the feature, incremented in each Overture release where the geometry or attributes of this feature changed.

> It might be reasonable to combine "updateTime" and "version" in a single "updateVersion" field which gives the last Overture version number in which the feature changed. The downside to doing this is that the number would cease to be indicative of the "rate of change" of the feature.

`version`

*   is required

*   Type: `integer`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-featureversion.md "defs.yaml#/$defs/propertyContainers/overtureFeaturePropertiesContainer/properties/version")

### version Type

`integer`

## updateTime

Timestamp when the feature was last updated

> Pattern is used as a fallback because not all JSON schema implementations treat "format" as an assertion, for some it is only an annotation.
> A somewhat more compact approach would be to reference the Overture version where the feature last changed instead of the update time, and expect clients to do a lookup if they really care about the time.

`updateTime`

*   is required

*   Type: `string`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-featureupdatetime.md "defs.yaml#/$defs/propertyContainers/overtureFeaturePropertiesContainer/properties/updateTime")

### updateTime Type

`string`

### updateTime Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[1-9]\d{3}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[-+]\d{2}:\d{2})$
```

[try pattern](https://regexr.com/?expression=%5E%5B1-9%5D%5Cd%7B3%7D-%5Cd%7B2%7D-%5Cd%7B2%7DT%5Cd%7B2%7D%3A%5Cd%7B2%7D%3A%5Cd%7B2%7D\(Z%7C%5B-%2B%5D%5Cd%7B2%7D%3A%5Cd%7B2%7D\)%24 "try regular expression with regexr.com")

**date time**: the string must be a date time string, according to [RFC 3339, section 5.6](https://tools.ietf.org/html/rfc3339 "check the specification")

## Pattern: `^ext.*$`

no description

`^ext.*$`

*   is optional

*   Type: unknown

*   cannot be null

*   defined in: [Untitled schema](undefined.md "undefined#undefined")

### Untitled schema Type

unknown
