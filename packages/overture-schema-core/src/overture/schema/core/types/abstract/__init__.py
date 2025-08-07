"""Abstract data types for Overture schemas.

This module provides abstract data types with automatic constraint validation
and multi-target serialization support (Scala, Spark, Parquet, JSON Schema).
"""

from .abstract_type import AbstractType, AbstractTypeDefinition, AbstractTypeRegistry
from .types import (
    Float32,
    Float64,
    Int8,
    Int32,
    Int64,
    UInt8,
    UInt16,
    UInt32,
    get_abstract_type,
    get_target_type,
)

__all__ = [
    # Core types
    "AbstractType",
    "AbstractTypeDefinition",
    "AbstractTypeRegistry",
    # Concrete types
    "UInt8",
    "UInt16",
    "UInt32",
    "Int8",
    "Int32",
    "Int64",
    "Float32",
    "Float64",
    # Utilities
    "get_target_type",
    "get_abstract_type",
]
