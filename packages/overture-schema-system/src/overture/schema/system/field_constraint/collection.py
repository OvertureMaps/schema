from collections.abc import Collection
from typing import Any, get_origin

from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    ValidationError,
    ValidationInfo,
)
from pydantic_core import InitErrorDetails, core_schema

from .field_constraint import FieldConstraint


class CollectionConstraint(FieldConstraint):
    """Base class for collection-based constraints."""

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        # Let the handler generate the proper schema for the collection type
        python_schema = handler(source)

        def validate_collection(value: Any, info: ValidationInfo) -> Any:
            self.validate(value, info)
            return value

        return core_schema.with_info_after_validator_function(
            validate_collection, python_schema
        )

    @staticmethod
    def _is_collection_type(source: type[Any]) -> bool:
        origin = get_origin(source)
        if origin is not None:
            return issubclass(origin, Collection)
        else:
            return issubclass(source, Collection)


class UniqueItemsConstraint(CollectionConstraint):
    """Ensures all items in a collection are unique."""

    def validate(self, value: list[Any] | None, info: ValidationInfo) -> None:
        # Skip validation for None values (used with optional fields)
        if value is None:
            return

        # First try the fast path for hashable items
        try:
            if len(value) != len(set(value)):
                self._raise_duplicate_error(value, info)
        except TypeError:
            # Fallback for unhashable items (like lists)
            if self._has_duplicates_unhashable(value):
                self._raise_duplicate_error(value, info)

    def _has_duplicates_unhashable(self, value: list[Any]) -> bool:
        """Check for duplicates when items are not hashable."""
        for i, item1 in enumerate(value):
            for item2 in value[i + 1 :]:
                if item1 == item2:
                    return True
        return False

    def _raise_duplicate_error(self, value: list[Any], info: ValidationInfo) -> None:
        """Raise validation error for duplicate items."""
        context = info.context or {}
        loc = context.get("loc_prefix", ()) + ("value",)
        raise ValidationError.from_exception_data(
            title=self.__class__.__name__,
            line_errors=[
                InitErrorDetails(
                    type="value_error",
                    loc=loc,
                    input=value,
                    ctx={"error": "All items must be unique"},
                )
            ],
        )

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        json_schema = handler(core_schema)
        json_schema["uniqueItems"] = True
        return json_schema
