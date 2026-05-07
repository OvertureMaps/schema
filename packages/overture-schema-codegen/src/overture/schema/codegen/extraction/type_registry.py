"""Type registry mapping Python types to target representations."""

from dataclasses import dataclass
from typing import Literal

from .field import FieldShape
from .field_walk import newtype_name, terminal_primitive

__all__ = [
    "SparkCategory",
    "TypeMapping",
    "PRIMITIVE_TYPES",
    "get_type_mapping",
    "is_semantic_newtype",
    "primitive_spark_category",
    "resolve_type_name",
]

SparkCategory = Literal["string", "int", "float", "bool", "other"]


@dataclass(frozen=True)
class TypeMapping:
    """Maps a type to its representation in different targets."""

    markdown: str
    spark: str | None = None


PRIMITIVE_TYPES: dict[str, TypeMapping] = {
    # Signed integers
    "int8": TypeMapping(markdown="int8", spark="IntegerType()"),
    "int16": TypeMapping(markdown="int16", spark="IntegerType()"),
    "int32": TypeMapping(markdown="int32", spark="IntegerType()"),
    "int64": TypeMapping(markdown="int64", spark="LongType()"),
    # Unsigned integers
    "uint8": TypeMapping(markdown="uint8", spark="IntegerType()"),
    "uint16": TypeMapping(markdown="uint16", spark="IntegerType()"),
    "uint32": TypeMapping(markdown="uint32", spark="IntegerType()"),
    # Floating point
    "float32": TypeMapping(markdown="float32", spark="FloatType()"),
    "float64": TypeMapping(markdown="float64", spark="DoubleType()"),
    # Basic types
    "str": TypeMapping(markdown="string", spark="StringType()"),
    "bool": TypeMapping(markdown="boolean", spark="BooleanType()"),
    # Python builtins (aliases to their portable equivalents)
    "int": TypeMapping(markdown="int64", spark="LongType()"),
    "float": TypeMapping(markdown="float64", spark="DoubleType()"),
    # Geometry types
    "Geometry": TypeMapping(markdown="geometry", spark="BinaryType()"),
    "BBox": TypeMapping(markdown="bbox"),
}


def is_semantic_newtype(shape: FieldShape) -> bool:
    """Whether a shape's outermost NewType should be displayed by name.

    Returns True for unregistered NewTypes (HexColor, Sources) and
    NewTypes that wrap a different base type (FeatureVersion wrapping
    int32, Id wrapping NoWhitespaceString). Returns False for
    registered primitives (int32, Geometry).
    """
    nt_name = newtype_name(shape)
    if nt_name is None:
        return False
    terminal = terminal_primitive(shape)
    if terminal is None:
        return True
    if nt_name != terminal.base_type:
        return True
    return get_type_mapping(terminal.base_type) is None


def get_type_mapping(type_name: str) -> TypeMapping | None:
    """Look up a type mapping by name.

    Accepts portable type names (`int32`, `str`, `Geometry`) and Python
    builtin names (`int` -> int64, `float` -> float64).
    """
    return PRIMITIVE_TYPES.get(type_name)


# BinaryType() is intentionally absent: geometry maps to BinaryType() in
# PRIMITIVE_TYPES but falls through to "other" here, not a numeric/string/bool scalar.
_SPARK_TYPE_CATEGORIES: dict[str, SparkCategory] = {
    "StringType()": "string",
    "IntegerType()": "int",
    "LongType()": "int",
    "FloatType()": "float",
    "DoubleType()": "float",
    "BooleanType()": "bool",
}


def primitive_spark_category(base_type: str) -> SparkCategory:
    """Return the Spark category for a primitive base type name.

    Parameters
    ----------
    base_type
        A primitive type name (`"int32"`, `"float64"`, `"bool"`, `"str"`, ...).

    Returns
    -------
    SparkCategory
        `"string"` for string-valued types, `"int"` for integer types,
        `"float"` for floating-point types, `"bool"` for boolean types,
        `"other"` for binary, geometry, or unregistered types. Unknown
        types fall back to `"other"`, preserving string-default behavior
        for any future unregistered type.
    """
    mapping = get_type_mapping(base_type)
    if mapping is None or mapping.spark is None:
        return "other"
    return _SPARK_TYPE_CATEGORIES.get(mapping.spark, "other")


def resolve_type_name(shape: FieldShape) -> str:
    """Resolve a shape to its markdown base type name string.

    Looks up the terminal scalar's `base_type` in the registry first,
    falling back to `source_type.__name__`. Semantic NewTypes wrapping
    unregistered types resolve to the underlying class name (e.g.
    `Sources` wrapping `SourceItem` -> `SourceItem`).
    """
    terminal = terminal_primitive(shape)
    if terminal is None:
        return "?"
    mapping = get_type_mapping(terminal.base_type)
    if mapping is None and terminal.source_type is not None:
        mapping = get_type_mapping(terminal.source_type.__name__)
    if mapping is not None:
        return mapping.markdown

    if newtype_name(shape) and terminal.source_type is not None:
        return terminal.source_type.__name__
    return terminal.base_type
