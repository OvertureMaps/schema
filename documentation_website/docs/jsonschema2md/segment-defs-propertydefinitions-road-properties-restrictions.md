# Untitled object in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## restrictions Type

`object` ([Details](segment-defs-propertydefinitions-road-properties-restrictions.md))

all of

*   one (and only one) of

    *   not

        *   any of

            *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-0-not-anyof-0.md "check type definition")

            *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-0-not-anyof-1.md "check type definition")

    *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-1.md "check type definition")

    *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-2.md "check type definition")

# restrictions Properties

| Property                                      | Type    | Required | Nullable       | Defined by                                                                                                                                                                                                                                                            |
| :-------------------------------------------- | :------ | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [speedLimits](#speedlimits)                   | `array` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-speedlimits.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits")                   |
| [sizeLimits](#sizelimits)                     | `array` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/sizeLimits")                     |
| [entranceRestrictions](#entrancerestrictions) | `array` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-entrancerestrictions.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/entranceRestrictions") |
| [exitRestrictions](#exitrestrictions)         | `array` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-exitrestrictions.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/exitRestrictions")         |

## speedLimits

Rules governing speed on this road segment

`speedLimits`

*   is optional

*   Type: `object[]` ([Details](segment-defs-propertydefinitions-road-properties-restrictions-properties-speedlimits-items.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-speedlimits.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/speedLimits")

### speedLimits Type

`object[]` ([Details](segment-defs-propertydefinitions-road-properties-restrictions-properties-speedlimits-items.md))

## sizeLimits

Rules governing vehicle size on this road segment

`sizeLimits`

*   is optional

*   Type: `object[]` ([Details](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/sizeLimits")

### sizeLimits Type

`object[]` ([Details](segment-defs-propertydefinitions-road-properties-restrictions-properties-sizelimits-items.md))

## entranceRestrictions

Rules restricting how traffic may enter the road at one of its ends, a.k.a. via restrictions.

> TODO

`entranceRestrictions`

*   is optional

*   Type: `array`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-entrancerestrictions.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/entranceRestrictions")

### entranceRestrictions Type

`array`

## exitRestrictions

Rules restricting how traffic may exit the road at one of its ends, a.k.a. turn restrictions.

> TODO

`exitRestrictions`

*   is optional

*   Type: `array`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions-properties-exitrestrictions.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions/properties/exitRestrictions")

### exitRestrictions Type

`array`
