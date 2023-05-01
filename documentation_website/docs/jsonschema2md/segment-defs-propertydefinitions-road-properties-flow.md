# Untitled array in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/flow
```

Rules for how traffic flows along a road segment. Each rule may optionally apply along a linearly referenced range, during a specific set of opening hours, or both. Each rule must fully specify the traffic flow for the part of the segment to which it applies (i.e. there are no partial rules).

> Because lane ordering follows the physical layout of the road, there is no default flow rule, since even a simple bidirectional setup with two lanes would only be applicable to the part of the world which shares the same driving direction.
> A possible alternative would be to make the default a one-way flow with a single lane in the forward direction, but given how few roads on the planet it would match, this choice would reveal a very poor understanding of "default".
> It may be that the "flows" concept is general enough to lift up out of "road" and put at the top level. We would have to be convinced that it also applies to water/ferry and rail, however.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## flow Type

`object[]` ([Details](segment-defs-propertydefinitions-road-properties-flow-items.md))

## flow Constraints

**minimum number of items**: the minimum number of items for this array is: `1`

**unique items**: all items in this array must be unique. Duplicates are not allowed.
