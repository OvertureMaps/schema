"""Type registry mapping Python types to target representations."""

from dataclasses import dataclass

from .type_analyzer import TypeInfo

__all__ = [
    "TypeMapping",
    "PRIMITIVE_TYPES",
    "get_type_mapping",
    "is_semantic_newtype",
    "resolve_type_name",
]


@dataclass(frozen=True)
class TypeMapping:
    """Maps a type to its representation in different targets."""

    markdown: str
    arrow: str | None = None

    def for_target(self, target: str) -> str | None:
        """Get the type representation for a named target.

        Returns None for targets where this type has no mapping.
        """
        if target == "markdown":
            return self.markdown
        if target == "arrow":
            return self.arrow
        raise ValueError(f"Unknown target {target!r}")


PRIMITIVE_TYPES: dict[str, TypeMapping] = {
    # Signed integers
    "int8": TypeMapping(markdown="int8", arrow="int8"),
    "int16": TypeMapping(markdown="int16", arrow="int16"),
    "int32": TypeMapping(markdown="int32", arrow="int32"),
    "int64": TypeMapping(markdown="int64", arrow="int64"),
    # Unsigned integers
    "uint8": TypeMapping(markdown="uint8", arrow="uint8"),
    "uint16": TypeMapping(markdown="uint16", arrow="uint16"),
    "uint32": TypeMapping(markdown="uint32", arrow="uint32"),
    # Floating point
    "float32": TypeMapping(markdown="float32", arrow="float32"),
    "float64": TypeMapping(markdown="float64", arrow="float64"),
    # Basic types
    "str": TypeMapping(markdown="string", arrow="utf8"),
    "bool": TypeMapping(markdown="boolean", arrow="bool_"),
    # Python builtins (aliases to their portable equivalents)
    "int": TypeMapping(markdown="int64", arrow="int64"),
    "float": TypeMapping(markdown="float64", arrow="float64"),
    # Geometry types
    "Geometry": TypeMapping(markdown="geometry", arrow="binary"),
    "BBox": TypeMapping(markdown="bbox"),
}


def is_semantic_newtype(type_info: TypeInfo) -> bool:
    """Whether a type represents a semantic NewType that should be displayed by name.

    Returns True for unregistered NewTypes (HexColor, Sources) and NewTypes
    that wrap a different base type (FeatureVersion wrapping int32, Id wrapping
    NoWhitespaceString). Returns False for registered primitives (int32, Geometry).
    """
    if type_info.newtype_name is None:
        return False
    if type_info.newtype_name != type_info.base_type:
        return True
    return get_type_mapping(type_info.base_type) is None


def get_type_mapping(type_name: str) -> TypeMapping | None:
    """Look up a type mapping by name.

    Parameters
    ----------
    type_name : str
        The type name to look up (e.g., "int32", "str", "Geometry").
        Also accepts Python builtin names ("int" -> int64, "float" -> float64).

    Returns
    -------
    TypeMapping or None
        The TypeMapping for the type, or None if not found.
    """
    return PRIMITIVE_TYPES.get(type_name)


def resolve_type_name(type_info: TypeInfo, target: str) -> str:
    """Resolve a TypeInfo to the base type string for a given target.

    Looks up the type in the registry first (trying source_type if base_type
    has no mapping). Falls back to the base_type name as-is.

    Parameters
    ----------
    type_info : TypeInfo
        The analyzed type information.
    target : str
        The output target ("markdown" or "arrow").

    Returns
    -------
    str
        The resolved base type name string for the target.
    """
    mapping = get_type_mapping(type_info.base_type)
    if mapping is None and type_info.source_type is not None:
        mapping = get_type_mapping(type_info.source_type.__name__)
    if mapping is not None:
        result = mapping.for_target(target)
        if result is not None:
            return result

    # Semantic NewType wrapping an unregistered type (e.g., Sources wrapping
    # SourceItem): use the underlying class name rather than the NewType alias.
    if type_info.newtype_name and type_info.source_type is not None:
        return type_info.source_type.__name__
    return type_info.base_type
