"""
Interface for constraints that apply to a single Pydantic field.

- If you are authoring new field-level constraints, this module is for you: you will very likely
  want to derive a subclass of `FieldConstraint` (or of a more specific base class such as
  `CollectionConstraint`).
- If you are looking to reuse existing constraints, this module is too low-level for you. You need
  one of the peer modules that implements a specific constraint type.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, ValidationInfo
from pydantic_core import core_schema


class FieldConstraint(ABC):
    """Base class for field-level constraints."""

    def validate(self, value: Any, info: ValidationInfo) -> None:  # noqa: B027
        """Validate the value and raise `ValidationError` if invalid."""
        pass

    @abstractmethod
    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Generate Pydantic core schema."""
        pass

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        """
        Generate JSON schema.

        Override in subclasses for custom schema.
        """
        return handler(core_schema)
