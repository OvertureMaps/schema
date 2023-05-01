# Untitled object in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits/items
```

An individual speed limit rule

> TODO: Speed limits probably have directionality, so should factor out a directionContainer for this purpose and use it to introduce an optional direction property in each rule.

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## items Type

`object` ([Details](segment-defs-propertydefinitions-road-properties-restrictions-properties-speedlimits-items.md))

any of

*   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-speedlimits-items-anyof-0.md "check type definition")

*   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-speedlimits-items-anyof-1.md "check type definition")

# items Properties

| Property                                  | Type      | Required | Nullable       | Defined by                                                                                                                                                                                                                                                                                                                  |
| :---------------------------------------- | :-------- | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [minSpeed](#minspeed)                     | `array`   | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-speed.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits/items/properties/minSpeed")                                                                                             |
| [maxSpeed](#maxspeed)                     | `array`   | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-speed.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits/items/properties/maxSpeed")                                                                                             |
| [isMaxSpeedVariable](#ismaxspeedvariable) | `boolean` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-speedlimits-items-properties-ismaxspeedvariable.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits/items/properties/isMaxSpeedVariable") |
| [lanes](#lanes)                           | `array`   | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-speedlimits-items-properties-lanes.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits/items/properties/lanes")                           |

## minSpeed

A speed value, i.e. a certain number of distance units travelled per unit time.

`minSpeed`

*   is optional

*   Type: `array`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-speed.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits/items/properties/minSpeed")

### minSpeed Type

`array`

## maxSpeed

A speed value, i.e. a certain number of distance units travelled per unit time.

`maxSpeed`

*   is optional

*   Type: `array`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-speed.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits/items/properties/maxSpeed")

### maxSpeed Type

`array`

## isMaxSpeedVariable

Indicates a variable speed corridor

`isMaxSpeedVariable`

*   is optional

*   Type: `boolean`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-speedlimits-items-properties-ismaxspeedvariable.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits/items/properties/isMaxSpeedVariable")

### isMaxSpeedVariable Type

`boolean`

## lanes

Optionally specifies the lanes to which the speed limit rule applies. If omitted, the rule applies to all lanes.

`lanes`

*   is optional

*   Type: `integer[]`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-speedlimits-items-properties-lanes.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits/items/properties/lanes")

### lanes Type

`integer[]`

### lanes Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.
