# Untitled object in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/sizeLimits/items
```

An individual vehicle size rule

> TODO: Is there a directionality aspect to vehicle size limits, similar to speed limits? Or at that point should we just split into two unidirectional segments?

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## items Type

`object` ([Details](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items.md))

any of

*   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items-anyof-0.md "check type definition")

*   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items-anyof-1.md "check type definition")

*   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items-anyof-2.md "check type definition")

# items Properties

| Property                                  | Type     | Required | Nullable       | Defined by                                                                                                                                                                                                                                                                                                                |
| :---------------------------------------- | :------- | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [maxHeightMeters](#maxheightmeters)       | `number` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items-properties-maxheightmeters.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/sizeLimits/items/properties/maxHeightMeters")       |
| [maxWidthMeters](#maxwidthmeters)         | `number` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items-properties-maxwidthmeters.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/sizeLimits/items/properties/maxWidthMeters")         |
| [maxWeightKilograms](#maxweightkilograms) | `number` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items-properties-maxweightkilograms.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/sizeLimits/items/properties/maxWeightKilograms") |

## maxHeightMeters



`maxHeightMeters`

*   is optional

*   Type: `number`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items-properties-maxheightmeters.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/sizeLimits/items/properties/maxHeightMeters")

### maxHeightMeters Type

`number`

### maxHeightMeters Constraints

**minimum (exclusive)**: the value of this number must be greater than: `0`

## maxWidthMeters



`maxWidthMeters`

*   is optional

*   Type: `number`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items-properties-maxwidthmeters.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/sizeLimits/items/properties/maxWidthMeters")

### maxWidthMeters Type

`number`

### maxWidthMeters Constraints

**minimum (exclusive)**: the value of this number must be greater than: `0`

## maxWeightKilograms



`maxWeightKilograms`

*   is optional

*   Type: `number`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items-properties-maxweightkilograms.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/sizeLimits/items/properties/maxWeightKilograms")

### maxWeightKilograms Type

`number`

### maxWeightKilograms Constraints

**minimum (exclusive)**: the value of this number must be greater than: `0`
