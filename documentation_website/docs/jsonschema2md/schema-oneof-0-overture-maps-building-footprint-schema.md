# Overture Maps Building Footprint Schema Schema

```txt
buildings/footprint.yaml#/oneOf/0/then
```

Additive schema for building footprints

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                     |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [schema.yaml\*](../../../../../../../tmp/jsonschema/schema/schema.yaml "open original schema") |

## then Type

`object` ([Overture Maps Building Footprint Schema](schema-oneof-0-overture-maps-building-footprint-schema.md))

# then Properties

| Property                  | Type   | Required | Nullable       | Defined by                                                                                                                      |
| :------------------------ | :----- | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------ |
| [geometry](#geometry)     | Merged | Optional | cannot be null | [Overture Maps Building Footprint Schema](footprint-properties-geometry.md "buildings/footprint.yaml#/properties/geometry")     |
| [properties](#properties) | Merged | Optional | cannot be null | [Overture Maps Building Footprint Schema](footprint-properties-properties.md "buildings/footprint.yaml#/properties/properties") |

## geometry



`geometry`

*   is optional

*   Type: merged type ([Details](footprint-properties-geometry.md))

*   cannot be null

*   defined in: [Overture Maps Building Footprint Schema](footprint-properties-geometry.md "buildings/footprint.yaml#/properties/geometry")

### geometry Type

merged type ([Details](footprint-properties-geometry.md))

one (and only one) of

*   [Untitled undefined type in Overture Maps Building Footprint Schema](footprint-properties-geometry-oneof-0.md "check type definition")

*   [Untitled undefined type in Overture Maps Building Footprint Schema](footprint-properties-geometry-oneof-1.md "check type definition")

## properties



`properties`

*   is optional

*   Type: merged type ([Details](footprint-properties-properties.md))

*   cannot be null

*   defined in: [Overture Maps Building Footprint Schema](footprint-properties-properties.md "buildings/footprint.yaml#/properties/properties")

### properties Type

merged type ([Details](footprint-properties-properties.md))

all of

*   [Untitled object in Overture Maps Building Footprint Schema](defs-defs-propertycontainers-overturefeaturepropertiescontainer.md "check type definition")

*   [Untitled object in Overture Maps Building Footprint Schema](defs-defs-propertycontainers-levelcontainer.md "check type definition")
