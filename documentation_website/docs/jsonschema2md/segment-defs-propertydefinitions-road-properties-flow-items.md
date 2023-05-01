# Untitled object in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flow/items
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## items Type

`object` ([Details](segment-defs-propertydefinitions-road-properties-flow-items.md))

all of

*   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-applyatrangecontainer.md "check type definition")

*   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-applyduringcontainer.md "check type definition")

# items Properties

| Property              | Type    | Required | Nullable       | Defined by                                                                                                                                                                                                                                |
| :-------------------- | :------ | :------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [dividers](#dividers) | `array` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-flow-items-properties-dividers.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flow/items/properties/dividers") |
| [lanes](#lanes)       | `array` | Required | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-flow-items-properties-lanes.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flow/items/properties/lanes")       |

## dividers

How the lanes are divided within this flow rule. There must be exactly one divider for each lane, so a flow rule with N lanes must have N-1 dividers. For two consecutive lane items (lanes\[i], lanes\[i+1]), the divider between them is given by dividers\[i].

`dividers`

*   is optional

*   Type: `string[]`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-flow-items-properties-dividers.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flow/items/properties/dividers")

### dividers Type

`string[]`

### dividers Default Value

The default value is:

```json
[]
```

## lanes

The lanes existing within this flow rule. Lanes are specified from left to right from the perspective of a person standing on the segment facing in the forward direction.

`lanes`

*   is required

*   Type: `object[]` ([Details](segment-defs-propertydefinitions-lane.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-flow-items-properties-lanes.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flow/items/properties/lanes")

### lanes Type

`object[]` ([Details](segment-defs-propertydefinitions-lane.md))

### lanes Constraints

**minimum number of items**: the minimum number of items for this array is: `1`
