"""Type registry mapping Python types to target representations."""

from dataclasses import dataclass

from .type_analyzer import TypeInfo

__all__ = [
    "TypeMapping",
    "PRIMITIVE_TYPES",
    "get_type_mapping",
    "is_semantic_newtype",
    "is_storage_primitive_source",
    "resolve_type_name",
]


@dataclass(frozen=True)
class TypeMapping:
    """Maps a type to its representation in different targets."""

    markdown: str

    def for_target(self, target: str) -> str:
        """Get the type representation for a named target."""
        if target != "markdown":
            raise ValueError(f"Unknown target {target!r}, expected 'markdown'")
        return self.markdown


PRIMITIVE_TYPES: dict[str, TypeMapping] = {
    # Signed integers
    "int8": TypeMapping(markdown="int8"),
    "int16": TypeMapping(markdown="int16"),
    "int32": TypeMapping(markdown="int32"),
    "int64": TypeMapping(markdown="int64"),
    # Unsigned integers
    "uint8": TypeMapping(markdown="uint8"),
    "uint16": TypeMapping(markdown="uint16"),
    "uint32": TypeMapping(markdown="uint32"),
    # Floating point
    "float32": TypeMapping(markdown="float32"),
    "float64": TypeMapping(markdown="float64"),
    # Basic types
    "str": TypeMapping(markdown="string"),
    "bool": TypeMapping(markdown="boolean"),
    # Python builtins (aliases to their portable equivalents)
    "int": TypeMapping(markdown="int64"),
    "float": TypeMapping(markdown="float64"),
    # Geometry types
    "Geometry": TypeMapping(markdown="geometry"),
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


def is_storage_primitive_source(source_name: str | None) -> bool:
    """Whether a ConstraintSource name refers to a registered storage primitive.

    Used by validation renderers to filter out storage-level constraints
    (e.g., int32 range) in favor of domain-level constraints.

    Parameters
    ----------
    source_name
        The NewType or primitive name to check, or None.

    Returns
    -------
    bool
        True if source_name is a key in PRIMITIVE_TYPES.
    """
    if source_name is None:
        return False
    return source_name in PRIMITIVE_TYPES


def resolve_type_name(type_info: TypeInfo, target: str) -> str:
    """Resolve a TypeInfo to the base type string for a given target.

    Looks up the type in the registry first (trying source_type if base_type
    has no mapping). Falls back to the base_type name as-is.

    Parameters
    ----------
    type_info : TypeInfo
        The analyzed type information.
    target : str
        The output target ("markdown").

    Returns
    -------
    str
        The resolved base type name string for the target.
    """
    mapping = get_type_mapping(type_info.base_type)
    if mapping is None and type_info.source_type is not None:
        mapping = get_type_mapping(type_info.source_type.__name__)
    if mapping is not None:
        return mapping.for_target(target)

    # Semantic NewType wrapping an unregistered type (e.g., Sources wrapping
    # SourceItem): use the underlying class name rather than the NewType alias.
    if type_info.newtype_name and type_info.source_type is not None:
        return type_info.source_type.__name__
    return type_info.base_type
