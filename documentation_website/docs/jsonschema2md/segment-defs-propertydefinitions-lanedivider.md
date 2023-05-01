# Untitled string in Overture Maps Transportation Segment Schema Schema

```txt
transportation/segment.yaml#/$defs/propertyDefinitions/laneDivider
```

Enumerates possible methods of dividing two lanes on a road segment.

> The lane divider concept models ability to change lanes from a navigation standpoint (equivalent to OSM "change" tags) and from a visual standpoint (equivalent to OSM "divider" tags) because abstract values such as "mayChange" can be mapped to the appropriate line markings. Judging by fact that OSM has orders of magnitude more "change" tags, the navigation function is thought to be more important.
> References:
> o <https://taginfo.openstreetmap.org/keys/change> (7K entities)
> o <https://taginfo.openstreetmap.org/keys/change:lanes> (50K entities)
> o <https://taginfo.openstreetmap.org/keys/divider> (4K entities)
> o <https://taginfo.openstreetmap.org/keys/divider:lanes> (0 entities)

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [segment.yaml\*](../../../../../../../tmp/jsonschema/schema/transportation/segment.yaml "open original schema") |

## laneDivider Type

`string`

## laneDivider Constraints

**enum**: the value of this property must be equal to one of the following values:

| Value           | Explanation |
| :-------------- | :---------- |
| `"unknown"`     |             |
| `"barrier"`     |             |
| `"curb"`        |             |
| `"mayChange"`   |             |
| `"mayNotCross"` |             |
| `"mayPass"`     |             |
| `"signal"`      |             |
