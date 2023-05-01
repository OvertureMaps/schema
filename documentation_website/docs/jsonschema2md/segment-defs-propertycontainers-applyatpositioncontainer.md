# Untitled undefined type in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyContainers/applyAtPositionContainer
```

Properties defining the discrete position on the segment where a rule is active.

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## applyAtPositionContainer Type

unknown

# applyAtPositionContainer Properties

| Property            | Type     | Required | Nullable       | Defined by                                                                                                                                                                                                     |
| :------------------ | :------- | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [applyAt](#applyat) | `number` | Optional | cannot be null | [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-linearlyreferencedposition.md "transportation/segment.yaml#/$defs/propertyContainers/applyAtPositionContainer/properties/applyAt") |

## applyAt

Represents a linearly-referenced position between 0% and 100% of the distance along a path such as a road segment or a river center-line segment.

> One possible advantage to using percentages over absolute distances is being able to trivially validate that the position lies "on" its segment (i.e. is between zero and one). Of course, this level of validity doesn't mean the number isn't nonsense.

`applyAt`

*   is optional

*   Type: `number`

*   cannot be null

*   defined in: [Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-linearlyreferencedposition.md "transportation/segment.yaml#/$defs/propertyContainers/applyAtPositionContainer/properties/applyAt")

### applyAt Type

`number`
