# Untitled object in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/surface/oneOf/1/items
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## items Type

`object` ([Details](segment-defs-propertydefinitions-road-properties-surface-oneof-1-items.md))

all of

*   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-applyatrangecontainer.md "check type definition")

# items Properties

| Property        | Type     | Required | Nullable       | Defined by                                                                                                                                                                                                                                                |
| :-------------- | :------- | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [value](#value) | `string` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-surface-oneof-1-items-properties-value.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/surface/oneOf/1/items/properties/value") |

## value

Physical surface of the road

`value`

*   is optional

*   Type: `string`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-surface-oneof-1-items-properties-value.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/surface/oneOf/1/items/properties/value")

### value Type

`string`

### value Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value            | Explanation |
| :--------------- | :---------- |
| `"unknown"`      |             |
| `"paved"`        |             |
| `"unpaved"`      |             |
| `"gravel"`       |             |
| `"dirt"`         |             |
| `"pavingStones"` |             |
| `"metal"`        |             |
