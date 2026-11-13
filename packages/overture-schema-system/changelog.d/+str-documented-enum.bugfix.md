Fixed `str()` and `format()` of a `DocumentedEnum` mixed with a data type. A member of a
`str` class now gives its value (`"motorway"`) and a member of an `int` class its number,
as `StrEnum` and `IntEnum` do, instead of `RoadClass.MOTORWAY`; f-strings give the value
again, as on Python 3.10. This covers classes defined outside this repository. A plain
`DocumentedEnum` still gives `Class.MEMBER`.
