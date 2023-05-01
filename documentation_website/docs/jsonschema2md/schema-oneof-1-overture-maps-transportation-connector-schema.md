# Overture Maps Transportation Connector Schema Schema

```txt
transportation/connector.yaml#/oneOf/1/then
```

Additive schema for transportation connectors

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                     |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [schema.yaml\*](../../../../../../../tmp/jsonschema/schema/schema.yaml "open original schema") |

## then Type

`object` ([Overture Maps Transportation Connector Schema](schema-oneof-1-overture-maps-transportation-connector-schema.md))

# then Properties

| Property                  | Type   | Required | Nullable       | Defined by                                                                                                                                 |
| :------------------------ | :----- | :------- | :------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| [geometry](#geometry)     | Merged | Optional | cannot be null | [Overture Maps Transportation Connector Schema](connector-properties-geometry.md "transportation/connector.yaml#/properties/geometry")     |
| [properties](#properties) | Merged | Optional | cannot be null | [Overture Maps Transportation Connector Schema](connector-properties-properties.md "transportation/connector.yaml#/properties/properties") |

## geometry



`geometry`

*   is optional

*   Type: merged type ([Details](connector-properties-geometry.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Connector Schema](connector-properties-geometry.md "transportation/connector.yaml#/properties/geometry")

### geometry Type

merged type ([Details](connector-properties-geometry.md))

all of

*   [Untitled undefined type in Overture Maps Transportation Connector Schema](connector-properties-geometry-allof-0.md "check type definition")

## properties



`properties`

*   is optional

*   Type: merged type ([Details](connector-properties-properties.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Connector Schema](connector-properties-properties.md "transportation/connector.yaml#/properties/properties")

### properties Type

merged type ([Details](connector-properties-properties.md))

all of

*   [Untitled object in Overture Maps Transportation Connector Schema](defs-defs-propertycontainers-overturefeaturepropertiescontainer.md "check type definition")

*   [Untitled object in Overture Maps Transportation Connector Schema](defs-defs-propertycontainers-levelcontainer.md "check type definition")
