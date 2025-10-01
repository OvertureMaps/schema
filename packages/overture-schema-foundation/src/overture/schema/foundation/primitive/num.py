from typing import Annotated, NewType

from pydantic import Field

uint8 = NewType("uint8", Annotated[int, Field(ge=0, le=255)])  # type: ignore [type-arg]
uint16 = NewType("uint16", Annotated[int, Field(ge=0, le=65535)])  # type: ignore[type-arg]
uint32 = NewType("uint32", Annotated[int, Field(ge=0, le=4294967295)])  # type: ignore[type-arg]
int8 = NewType("int8", Annotated[int, Field(ge=-128, le=127)])  # type: ignore[type-arg]
int32 = NewType("int32", Annotated[int, Field(ge=-(2**31), le=2**31 - 1)])  # type: ignore[type-arg]
int64 = NewType("int64", Annotated[int, Field(ge=-(2**63), le=2**63 - 1)])  # type: ignore[type-arg]
float32 = NewType("float32", float)
float64 = NewType("float64", float)
