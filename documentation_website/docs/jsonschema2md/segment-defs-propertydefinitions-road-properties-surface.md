# Untitled undefined type in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/road/properties/surface
```

Physical surface of the road. May either be specified as a single global value for the segment, or as an array of surface rules.

> We should likely restrict the available surface types to the subset of the common OSM surface=\* tag values that are useful both for routing and for map tile rendering.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## surface Type

merged type ([Details](segment-defs-propertydefinitions-road-properties-surface.md))

one (and only one) of

*   [Untitled string in Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-surface-oneof-0.md "check type definition")

*   [Untitled array in Overture Maps Transportation Segment Schema](segment-defs-propertydefinitions-road-properties-surface-oneof-1.md "check type definition")

## surface Default Value

The default value is:

```json
{
  "enum": [
    "unknown"
  ]
}
```
