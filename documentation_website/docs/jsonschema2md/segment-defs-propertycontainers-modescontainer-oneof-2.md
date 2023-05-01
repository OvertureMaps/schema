# Untitled undefined type in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyContainers/modesContainer/oneOf/2
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## 2 Type

unknown

# 2 Properties

| Property              | Type    | Required | Nullable       | Defined by                                                                                                                                                                                                                      |
| :-------------------- | :------ | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [notModes](#notmodes) | `array` | Required | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-2-properties-notmodes.md "transportation/segment.yaml#/$defs/propertyContainers/modesContainer/oneOf/2/properties/notModes") |

## notModes

Travel modes to which the rule does not apply

`notModes`

*   is required

*   Type: `string[]`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-2-properties-notmodes.md "transportation/segment.yaml#/$defs/propertyContainers/modesContainer/oneOf/2/properties/notModes")

### notModes Type

`string[]`

### notModes Constraints

**minimum length**: the minimum number of characters for this string is: `1`

**unique items**: all items in this array must be unique. Duplicates are not allowed.
