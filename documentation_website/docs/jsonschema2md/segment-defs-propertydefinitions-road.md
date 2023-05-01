# Untitled object in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road
```

Properties for segments whose segment subType is road. The road subType includes any variety of road, street, or path, including dedicated paths for walking and cycling.

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## road Type

`object` ([Details](segment-defs-propertydefinitions-road.md))

## road Default Value

The default value is:

```json
{}
```

# road Properties

| Property                      | Type     | Required | Nullable       | Defined by                                                                                                                                                                                            |
| :---------------------------- | :------- | :------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [class](#class)               | `string` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-class.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/class")               |
| [roadName](#roadname)         | Merged   | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-roadname.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/roadName")         |
| [surface](#surface)           | Merged   | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-surface.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/surface")           |
| [flags](#flags)               | `array`  | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-flags.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flags")               |
| [flow](#flow)                 | `array`  | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-flow.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flow")                 |
| [restrictions](#restrictions) | Merged   | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions") |

## class

Captures the kind of road and its position in the road network hierarchy.

`class`

*   is optional

*   Type: `string`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-class.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/class")

### class Type

`string`

### class Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value            | Explanation |
| :--------------- | :---------- |
| `"unknown"`      |             |
| `"primary"`      |             |
| `"secondary"`    |             |
| `"tertiary"`     |             |
| `"residential"`  |             |
| `"parkingAisle"` |             |
| `"driveway"`     |             |
| `"footway"`      |             |
| `"cycleway"`     |             |

### class Default Value

The default value is:

```json
{
  "enum": [
    "unknown"
  ]
}
```

## roadName



`roadName`

*   is optional

*   Type: merged type ([Details](segment-defs-propertydefinitions-road-properties-roadname.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-roadname.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/roadName")

### roadName Type

merged type ([Details](segment-defs-propertydefinitions-road-properties-roadname.md))

one (and only one) of

*   all of

    *   [Untitled object in Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-name.md "check type definition")

*   [Untitled array in Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-roadname-oneof-1.md "check type definition")

## surface

Physical surface of the road. May either be specified as a single global value for the segment, or as an array of surface rules.

> We should likely restrict the available surface types to the subset of the common OSM surface=\* tag values that are useful both for routing and for map tile rendering.

`surface`

*   is optional

*   Type: merged type ([Details](segment-defs-propertydefinitions-road-properties-surface.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-surface.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/surface")

### surface Type

merged type ([Details](segment-defs-propertydefinitions-road-properties-surface.md))

one (and only one) of

*   [Untitled string in Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-surface-oneof-0.md "check type definition")

*   [Untitled array in Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-surface-oneof-1.md "check type definition")

### surface Default Value

The default value is:

```json
{
  "enum": [
    "unknown"
  ]
}
```

## flags

Set of boolean attributes applicable to roads. May be specified either as a single flag array of flag values, or as an array of flag rules.

`flags`

*   is optional

*   Type: an array of merged types ([Details](segment-defs-propertydefinitions-road-properties-flags-items.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-flags.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flags")

### flags Type

an array of merged types ([Details](segment-defs-propertydefinitions-road-properties-flags-items.md))

### flags Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.

## flow

Rules for how traffic flows along a road segment. Each rule may optionally apply along a linearly referenced range, during a specific set of opening hours, or both. Each rule must fully specify the traffic flow for the part of the segment to which it applies (i.e. there are no partial rules).

> Because lane ordering follows the physical layout of the road, there is no default flow rule, since even a simple bidirectional setup with two lanes would only be applicable to the part of the world which shares the same driving direction.
> A possible alternative would be to make the default a one-way flow with a single lane in the forward direction, but given how few roads on the planet it would match, this choice would reveal a very poor understanding of "default".
> It may be that the "flows" concept is general enough to lift up out of "road" and put at the top level. We would have to be convinced that it also applies to water/ferry and rail, however.

`flow`

*   is optional

*   Type: `object[]` ([Details](segment-defs-propertydefinitions-road-properties-flow-items.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-flow.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flow")

### flow Type

`object[]` ([Details](segment-defs-propertydefinitions-road-properties-flow-items.md))

### flow Constraints

**minimum number of items**: the minimum number of items for this array is: `1`

**unique items**: all items in this array must be unique. Duplicates are not allowed.

## restrictions



`restrictions`

*   is optional

*   Type: `object` ([Details](segment-defs-propertydefinitions-road-properties-restrictions.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-restrictions.md "transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/restrictions")

### restrictions Type

`object` ([Details](segment-defs-propertydefinitions-road-properties-restrictions.md))

all of

*   one (and only one) of

    *   not

        *   any of

            *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-0-not-anyof-0.md "check type definition")

            *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-0-not-anyof-1.md "check type definition")

    *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-1.md "check type definition")

    *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-defs-propertycontainers-modescontainer-oneof-2.md "check type definition")
