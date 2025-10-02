"""
Primitive data types.

This module provides a set of primitive types that can be used as fields in Pydantic models but are
not themselves models. The primitive types include specific numeric types such as int32 and
geometric types including `Geometry` and `BBox`.

Primitives are intended to provide specific, well-defined behavior for a wide range of serialization
targets including not just Pydantic models and JSON, but also a range of other serialization
targets, for example, the Parquet format or Spark dataframes. They come with built-in Pydantic
constraints, but also specific documented behavior expectations so they can be supported by other
serialization targets.
"""

from typing import Annotated, NewType, TypeAlias

from pydantic import Field

from .bbox import BBox
from .geom import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)

uint8: TypeAlias = NewType("uint8", Annotated[int, Field(ge=0, le=255)])  # type: ignore [type-arg]
"""
Portable 8-bit unsigned integer.

This is an `int` at runtime, but using `uint8` for Pydantic model fields instead of `int` makes them
portable across different serialization and validation platforms.
"""

uint16: TypeAlias = NewType("uint16", Annotated[int, Field(ge=0, le=65535)])  # type: ignore[type-arg]
"""
Portable 16-bit unsigned integer.

This is an `int` at runtime, but using `uint16` for Pydantic model fields instead of `int` makes
them portable across different serialization and validation platforms.
"""

uint32: TypeAlias = NewType("uint32", Annotated[int, Field(ge=0, le=4294967295)])  # type: ignore[type-arg]
"""
Portable 32-bit unsigned integer.

This is an `int` at runtime, but using `uint32` for Pydantic model fields instead of `int` makes
them portable across different serialization and validation platforms.
"""

int8: TypeAlias = NewType("int8", Annotated[int, Field(ge=-128, le=127)])  # type: ignore[type-arg]
"""
Portable 8-bit signed integer.

This is an `int` at runtime, but using `int8` for Pydantic model fields instead of `int` makes them
portable across different serialization and validation platforms.
"""

int16: TypeAlias = NewType("int16", Annotated[int, Field(ge=-32768, le=32767)])  # type: ignore[type-arg]
"""
Portable 16-bit signed integer.

This is an `int` at runtime, but using `int16` for Pydantic model fields instead of `int` makes them
portable across different serialization and validation platforms.
"""

int32: TypeAlias = NewType("int32", Annotated[int, Field(ge=-(2**31), le=2**31 - 1)])  # type: ignore[type-arg]
"""
Portable 32-bit signed integer.

This is an `int` at runtime, but using `int32` for Pydantic model fields instead of `int` makes them
portable across different serialization and validation platforms.
"""

int64: TypeAlias = NewType("int64", Annotated[int, Field(ge=-(2**63), le=2**63 - 1)])  # type: ignore[type-arg]
"""
Portable 64-bit signed integer.

This is an `int` at runtime, but using `int64` for Pydantic model fields instead of `int` makes them
portable across different serialization and validation platforms.
"""

float32: TypeAlias = NewType("float32", float)  # type: ignore[type-arg]
"""
Portable IEEE 32-bit floating point number.

This is a `float` at runtime, but using `float32` for Pydantic model fields instead of `float` makes
them portable across different serialization and validation platforms.
"""

float64: TypeAlias = NewType("float64", float)  # type: ignore[type-arg]
"""
Portable IEEE 64-bit floating point number.

This is a `float` at runtime, but using `float64` for Pydantic model fields instead of `float` makes
them portable across different serialization and validation platforms.
"""

pct: TypeAlias = NewType("pct", Annotated[float, Field(ge=0, le=1)])  # type: ignore[type-arg]
"""
Portable percent value in the range [0, 1] where 0 represents 0% and 1 represents 100%.

This is a `float` at runtime, but using `pct` for Pydantic model fields instead of `float` makes
them portable across different serialization and validation platforms.
"""


__all__ = [
    "BBox",
    "Geometry",
    "GeometryType",
    "GeometryTypeConstraint",
    "int8",
    "int16",
    "int32",
    "int64",
    "float32",
    "float64",
    "pct",
    "uint8",
    "uint16",
    "uint32",
]
