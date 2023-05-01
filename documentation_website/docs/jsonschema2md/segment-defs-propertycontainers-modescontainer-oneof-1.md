# Untitled undefined type in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyContainers/modesContainer/oneOf/1
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## 1 Type

unknown

# 1 Properties

| Property        | Type    | Required | Nullable       | Defined by                                                                                                                                                                                                                |
| :-------------- | :------ | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [modes](#modes) | `array` | Required | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-1-properties-modes.md "transportation/segment.yaml#/$defs/propertyContainers/modesContainer/oneOf/1/properties/modes") |

## modes

Travel modes to which the rule applies

`modes`

*   is required

*   Type: `string[]`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-1-properties-modes.md "transportation/segment.yaml#/$defs/propertyContainers/modesContainer/oneOf/1/properties/modes")

### modes Type

`string[]`

### modes Constraints

**minimum length**: the minimum number of characters for this string is: `1`

**unique items**: all items in this array must be unique. Duplicates are not allowed.
