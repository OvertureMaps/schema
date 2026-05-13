"""Type aliases for CLI module."""

from typing import Any, TypeAlias

from pydantic import BaseModel
from pydantic_core import ErrorDetails

# Type alias for union types created from Pydantic models
# This represents either a single model or a discriminated union of models
UnionType: TypeAlias = type[BaseModel] | Any

# Pydantic validation error dictionary structure
# In Pydantic v2, ValidationError.errors() returns list[ErrorDetails]
ValidationErrorDict: TypeAlias = ErrorDetails

# Error location tuple (mix of field names and list indices)
ErrorLocation: TypeAlias = tuple[str | int, ...]
