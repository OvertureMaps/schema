"""
Numeric types.

This module provides a set of portable numeric types that can be used as fields in Pydantic models
but are not themselves models: unsigned and signed integers of specific bit widths, and 32- and
64-bit floating point numbers.

These types are `int` or `float` at runtime, but using them for Pydantic model fields instead of the
bare Python types makes them portable across different serialization and validation targets,
including not just Pydantic models and JSON, but also a range of other serialization targets, for
example, the Parquet format or Spark dataframes. They come with built-in Pydantic constraints, but
also specific documented behavior expectations so they can be supported by other serialization
targets.
"""

from typing import Annotated, NewType

from pydantic import Field

uint8 = NewType("uint8", Annotated[int, Field(ge=0, le=255)])  # type: ignore [type-arg]
uint8.__doc__ = """
Portable 8-bit unsigned integer.

This is an `int` at runtime, but using `uint8` for Pydantic model fields instead of `int` makes them
portable across different serialization and validation platforms.
"""

uint16 = NewType("uint16", Annotated[int, Field(ge=0, le=65535)])  # type: ignore[type-arg]
uint16.__doc__ = """
Portable 16-bit unsigned integer.

This is an `int` at runtime, but using `uint16` for Pydantic model fields instead of `int` makes
them portable across different serialization and validation platforms.
"""

uint32 = NewType("uint32", Annotated[int, Field(ge=0, le=4294967295)])  # type: ignore[type-arg]
uint32.__doc__ = """
Portable 32-bit unsigned integer.

This is an `int` at runtime, but using `uint32` for Pydantic model fields instead of `int` makes
them portable across different serialization and validation platforms.
"""

int8 = NewType("int8", Annotated[int, Field(ge=-128, le=127)])  # type: ignore[type-arg]
int8.__doc__ = """
Portable 8-bit signed integer.

This is an `int` at runtime, but using `int8` for Pydantic model fields instead of `int` makes them
portable across different serialization and validation platforms.
"""

int16 = NewType("int16", Annotated[int, Field(ge=-32768, le=32767)])  # type: ignore[type-arg]
int16.__doc__ = """
Portable 16-bit signed integer.

This is an `int` at runtime, but using `int16` for Pydantic model fields instead of `int` makes them
portable across different serialization and validation platforms.
"""

int32 = NewType("int32", Annotated[int, Field(ge=-(2**31), le=2**31 - 1)])  # type: ignore[type-arg]
int32.__doc__ = """
Portable 32-bit signed integer.

This is an `int` at runtime, but using `int32` for Pydantic model fields instead of `int` makes them
portable across different serialization and validation platforms.
"""

int64 = NewType("int64", Annotated[int, Field(ge=-(2**63), le=2**63 - 1)])  # type: ignore[type-arg]
int64.__doc__ = """
Portable 64-bit signed integer.

This is an `int` at runtime, but using `int64` for Pydantic model fields instead of `int` makes them
portable across different serialization and validation platforms.
"""

float32 = NewType("float32", float)  # type: ignore[type-arg]
float32.__doc__ = """
Portable IEEE 32-bit floating point number.

This is a `float` at runtime, but using `float32` for Pydantic model fields instead of `float` makes
them portable across different serialization and validation platforms.
"""

float64 = NewType("float64", float)  # type: ignore[type-arg]
float64.__doc__ = """
Portable IEEE 64-bit floating point number.

This is a `float` at runtime, but using `float64` for Pydantic model fields instead of `float` makes
them portable across different serialization and validation platforms.
"""


__all__ = [
    "float32",
    "float64",
    "int8",
    "int16",
    "int32",
    "int64",
    "uint8",
    "uint16",
    "uint32",
]
