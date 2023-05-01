# Untitled object in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/roadName/oneOf/1/items/allOf/1
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## 1 Type

`object` ([Details](defs-defs-propertydefinitions-name.md))

# 1 Properties

| Property                | Type    | Required | Nullable       | Defined by                                                                                                                                                                 |
| :---------------------- | :------ | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [common](#common)       | `array` | Required | cannot be null | [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-name-properties-common.md "defs.yaml#/$defs/propertyDefinitions/name/properties/common")       |
| [official](#official)   | `array` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-name-properties-official.md "defs.yaml#/$defs/propertyDefinitions/name/properties/official")   |
| [alternate](#alternate) | `array` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-name-properties-alternate.md "defs.yaml#/$defs/propertyDefinitions/name/properties/alternate") |
| [short](#short)         | `array` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-name-properties-short.md "defs.yaml#/$defs/propertyDefinitions/name/properties/short")         |

## common

The most commonly used name when referring to a feature.  The first entry in the array of common names must have a language of "local" making it the easiest, default name to use among all options.

`common`

*   is required

*   Type: `object[]` ([Details](defs-defs-propertydefinitions-nameproperty.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-name-properties-common.md "defs.yaml#/$defs/propertyDefinitions/name/properties/common")

### common Type

`object[]` ([Details](defs-defs-propertydefinitions-nameproperty.md))

### common Constraints

**minimum number of items**: the minimum number of items for this array is: `1`

## official

An official name which is often a longer and more verbose version of the common name. For example, the official name of the United Kingdom is "United Kingdom of Great Britain and Northern Ireland" whereas the common name would be "United Kingdom"

`official`

*   is optional

*   Type: `object[]` ([Details](defs-defs-propertydefinitions-nameproperty.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-name-properties-official.md "defs.yaml#/$defs/propertyDefinitions/name/properties/official")

### official Type

`object[]` ([Details](defs-defs-propertydefinitions-nameproperty.md))

### official Constraints

**minimum number of items**: the minimum number of items for this array is: `1`

## alternate

Alternative names used to refer to the feature that may not fit into other categories.

`alternate`

*   is optional

*   Type: `object[]` ([Details](defs-defs-propertydefinitions-nameproperty.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-name-properties-alternate.md "defs.yaml#/$defs/propertyDefinitions/name/properties/alternate")

### alternate Type

`object[]` ([Details](defs-defs-propertydefinitions-nameproperty.md))

### alternate Constraints

**minimum number of items**: the minimum number of items for this array is: `1`

## short

Short names are often abbreviations or other shorthand forms of a name. The short name of the United Kingdom is UK.

`short`

*   is optional

*   Type: `object[]` ([Details](defs-defs-propertydefinitions-nameproperty.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-name-properties-short.md "defs.yaml#/$defs/propertyDefinitions/name/properties/short")

### short Type

`object[]` ([Details](defs-defs-propertydefinitions-nameproperty.md))

### short Constraints

**minimum number of items**: the minimum number of items for this array is: `1`
