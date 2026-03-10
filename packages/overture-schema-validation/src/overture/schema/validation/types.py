"""Type aliases for CLI module."""

from typing import TypeAlias

from pydantic_core import ErrorDetails

# Pydantic validation error dictionary structure
# In Pydantic v2, ValidationError.errors() returns list[ErrorDetails]
ValidationErrorDict: TypeAlias = ErrorDetails

# Error location tuple (mix of field names and list indices)
ErrorLocation: TypeAlias = tuple[str | int, ...]
