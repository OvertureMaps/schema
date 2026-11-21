Fixed subclasses of a member-less `(str, DocumentedEnum)` base, which failed at class
creation. Members of such a subclass are now built from the base's data type, so
`Deep("a")` is `Deep.A` and an instance of `str`.
