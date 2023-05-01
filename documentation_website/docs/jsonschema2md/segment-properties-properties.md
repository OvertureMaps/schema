# Untitled undefined type in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/properties/properties
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## properties Type

merged type ([Details](segment-properties-properties.md))

all of

*   [Untitled object in Overture Maps Transportation Segment Schema](defs-defs-propertycontainers-overturefeaturepropertiescontainer.md "check type definition")

*   [Untitled object in Overture Maps Transportation Segment Schema](defs-defs-propertycontainers-levelcontainer.md "check type definition")

*   all of

    *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-properties-properties-allof-2-allof-0.md "check type definition")

# properties Properties

| Property                  | Type     | Required | Nullable       | Defined by                                                                                                                                                                       |
| :------------------------ | :------- | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [subType](#subtype)       | `string` | Required | cannot be null | [Overture Maps Transportation Segment Schema](segment-properties-properties-properties-subtype.md "transportation/segment.yaml#/properties/properties/properties/subType")       |
| [connectors](#connectors) | `array`  | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-properties-properties-properties-connectors.md "transportation/segment.yaml#/properties/properties/properties/connectors") |

## subType

Broad category of transportation segment.

> Should not be confused with a transport mode. A segment kind has an (implied) set of default transport modes.

`subType`

*   is required

*   Type: `string`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-properties-properties-properties-subtype.md "transportation/segment.yaml#/properties/properties/properties/subType")

### subType Type

`string`

### subType Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value     | Explanation |
| :-------- | :---------- |
| `"road"`  |             |
| `"rail"`  |             |
| `"water"` |             |

## connectors

List of connector nodes this segment is physically connected to.

`connectors`

*   is optional

*   Type: `string[]`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-properties-properties-properties-connectors.md "transportation/segment.yaml#/properties/properties/properties/connectors")

### connectors Type

`string[]`

### connectors Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.

### connectors Default Value

The default value is:

```json
[]
```
