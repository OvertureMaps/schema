from abc import ABC, abstractmethod
from typing import Any

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, ValidationInfo
from pydantic_core import core_schema


class Constraint(ABC):
    """Base class for all constraints."""

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
        """Generate JSON schema.

        Override in subclasses for custom schema.
        """
        return handler(core_schema)
