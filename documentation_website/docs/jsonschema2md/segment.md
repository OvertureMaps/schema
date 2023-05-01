# Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml
```

Additive schema for transportation segments

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                    |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## Overture Maps Transportation Segment Schema Type

`object` ([Overture Maps Transportation Segment Schema](segment.md))

# Overture Maps Transportation Segment Schema Properties

| Property                  | Type   | Required | Nullable       | Defined by                                                                                                                           |
| :------------------------ | :----- | :------- | :------------- | :----------------------------------------------------------------------------------------------------------------------------------- |
| [geometry](#geometry)     | Merged | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-properties-geometry.md "transportation/segment.yaml#/properties/geometry")     |
| [properties](#properties) | Merged | Optional | cannot be null | [Overture Maps Transportation Segment Schema](segment-properties-properties.md "transportation/segment.yaml#/properties/properties") |

## geometry



`geometry`

*   is optional

*   Type: merged type ([Details](segment-properties-geometry.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-properties-geometry.md "transportation/segment.yaml#/properties/geometry")

### geometry Type

merged type ([Details](segment-properties-geometry.md))

all of

*   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-properties-geometry-allof-0.md "check type definition")

## properties



`properties`

*   is optional

*   Type: merged type ([Details](segment-properties-properties.md))

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](segment-properties-properties.md "transportation/segment.yaml#/properties/properties")

### properties Type

merged type ([Details](segment-properties-properties.md))

all of

*   [Untitled object in Overture Maps Transportation Segment Schema](defs-defs-propertycontainers-overturefeaturepropertiescontainer.md "check type definition")

*   [Untitled object in Overture Maps Transportation Segment Schema](defs-defs-propertycontainers-levelcontainer.md "check type definition")

*   all of

    *   [Untitled undefined type in Overture Maps Transportation Segment Schema](segment-properties-properties-allof-2-allof-0.md "check type definition")

# Overture Maps Transportation Segment Schema Definitions

## Definitions group propertyDefinitions

Reference this group by using

```json
{"$ref":"transportation/segment.yaml#/$defs/propertyDefinitions"}
```

| Property | Type | Required | Nullable | Defined by |
| :------- | :--- | :------- | :------- | :--------- |

## Definitions group propertyContainers

Reference this group by using

```json
{"$ref":"transportation/segment.yaml#/$defs/propertyContainers"}
```

| Property | Type | Required | Nullable | Defined by |
| :------- | :--- | :------- | :------- | :--------- |
