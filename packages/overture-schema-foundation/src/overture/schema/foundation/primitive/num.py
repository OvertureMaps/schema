from typing import Annotated, NewType

from pydantic import Field

uint8 = NewType("uint8", Annotated[int, Field(ge=0, le=255)])  # type: ignore [type-arg]
uint8.__doc__ = """
uint8 : NewType
    Portable 8-bit unsigned integer.

    This is an int at runtime, but using uint8 for fields instead of int makes them portable across
    different serialization and validation platforms.
"""

uint16 = NewType("uint16", Annotated[int, Field(ge=0, le=65535)])  # type: ignore[type-arg]
uint16.__doc__ = """
uint16 : NewType
    Portable 16-bit unsigned integer.

    This is an int at runtime, but using uint16 for fields instead of int makes them portable across
    different serialization and validation platforms.
"""

uint32 = NewType("uint32", Annotated[int, Field(ge=0, le=4294967295)])  # type: ignore[type-arg]
uint32.__doc__ = """
uint32 : NewType
    Portable 32-bit unsigned integer.

    This is an int at runtime, but using uint32 for fields instead of int makes them portable across
    different serialization and validation platforms.
"""

int8 = NewType("int8", Annotated[int, Field(ge=-128, le=127)])  # type: ignore[type-arg]
int8.__doc__ = """
int8 : NewType
    Portable 8-bit signed integer.

    This is an int at runtime, but using int8 for fields instead of int makes them portable across
    different serialization and validation platforms.
"""

int16 = NewType("int16", Annotated[int, Field(ge=-32768, le=32767)])  # type: ignore[type-arg]
int16.__doc__ = """
int16 : NewType
    Portable 16-bit signed integer.

    This is an int at runtime, but using int16 for fields instead of int makes them portable across
    different serialization and validation platforms.
"""

int32 = NewType("int32", Annotated[int, Field(ge=-(2**31), le=2**31 - 1)])  # type: ignore[type-arg]
int32.__doc__ = """
int32 : NewType
    Portable 32-bit signed integer.

    This is an int at runtime, but using int32 for fields instead of int makes them portable across
    different serialization and validation platforms.
"""

int64 = NewType("int64", Annotated[int, Field(ge=-(2**63), le=2**63 - 1)])  # type: ignore[type-arg]
int64.__doc__ = """
int64 : NewType
    Portable 64-bit signed integer.

    This is an int at runtime, but using int64 for fields instead of int makes them portable across
    different serialization and validation platforms.
"""

float32 = NewType("float32", float)
float32.__doc__ = """
float32 : NewType
    Portable IEEE 32-bit floating point number.

    This is a float at runtime, but using float32 for fields instead of float makes them portable
    across different serialization and validation platforms.
"""

float64 = NewType("float64", float)
float64.__doc__ = """
float64 : NewType
    Portable IEEE 64-bit floating point number.

    This is a float at runtime, but using float64 for fields instead of float makes them portable
    across different serialization and validation platforms.
"""

pct = NewType("pct", Annotated[float, Field(ge=0, le=1)])
pct.__doc__ = """
pct : NewType
    Portable percent value in the range [0, 1] where 0 represents 0% and 1 represents 100%.

    This is a float at runtime, but using pct for fields instead of float makes them portable
    across different serialization and validation platforms.
"""
