"""Primitive data types.

This module provides additional, more specific primitive types that come with automatic
constraint validation and are intended to support multi-target serialization support
(where the list of and names for these types vary).
"""

from .numeric import (
    float32,
    float64,
    int8,
    int32,
    int64,
    uint8,
    uint16,
    uint32,
)

__all__ = [
    "uint8",
    "uint16",
    "uint32",
    "int8",
    "int32",
    "int64",
    "float32",
    "float64",
]
