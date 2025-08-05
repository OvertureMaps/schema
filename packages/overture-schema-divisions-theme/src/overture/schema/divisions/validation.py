"""Division-specific validation constraints."""

from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from overture.schema.validation.mixin import (
    BaseConstraintValidator,
    register_constraint,
)

T = TypeVar("T", bound=BaseModel)


class ParentDivisionValidator(BaseConstraintValidator):
    """Validates parent division logic: parent_division_id is required unless field equals exempt value."""

    def __init__(self, field_name: str, exempt_value: str | int | float | bool) -> None:
        super().__init__()
        self.field_name = field_name
        self.exempt_value = exempt_value

    def validate(self, target: BaseModel) -> None:
        if hasattr(target, self.field_name) and hasattr(target, "parent_division_id"):
            field_value = getattr(target, self.field_name)
            parent_division_id = target.parent_division_id

            if field_value == self.exempt_value and parent_division_id is not None:
                raise ValueError(
                    f"parent_division_id must not be present when {self.field_name} is {self.exempt_value}"
                )
            elif field_value != self.exempt_value and parent_division_id is None:
                raise ValueError(
                    f"parent_division_id is required when {self.field_name} is not {self.exempt_value} (current: {field_value})"
                )

    def get_metadata(
        self, model_class: type[BaseModel] | None = None, by_alias: bool = True
    ) -> dict[str, Any]:
        from overture.schema.validation.mixin import resolve_field_names

        # Resolve field names to aliases if needed
        field_name = self.field_name
        parent_division_id = "parent_division_id"

        if model_class is not None:
            resolved_field = resolve_field_names(model_class, [field_name], by_alias)
            resolved_parent = resolve_field_names(
                model_class, [parent_division_id], by_alias
            )
            field_name = resolved_field[0]
            parent_division_id = resolved_parent[0]

        return {
            "type": "parent_division_required_unless",
            "field_name": field_name,
            "exempt_value": self.exempt_value,
            "parent_division_id": parent_division_id,
        }

    def apply_json_schema_metadata(
        self,
        target_schema: dict[str, Any],
        model_class: type[BaseModel] | None = None,
        by_alias: bool = True,
    ) -> None:
        """Apply parent division constraint to the schema."""
        metadata = self.get_metadata(model_class, by_alias)

        conditional_schema = {
            "if": {
                "properties": {
                    metadata["field_name"]: {"const": metadata["exempt_value"]}
                }
            },
            "then": {"not": {"required": [metadata["parent_division_id"]]}},
            "else": {"required": [metadata["parent_division_id"]]},
        }

        target_schema.setdefault("allOf", []).append(conditional_schema)


def parent_division_required_unless(
    field_name: str, exempt_value: str | int | float | bool
) -> Callable[[type[T]], type[T]]:
    """Decorator to add parent division validation: parent_division_id is required unless field equals exempt value."""

    def decorator(cls: type[T]) -> type[T]:
        constraint = ParentDivisionValidator(field_name, exempt_value)
        register_constraint(cls, constraint)
        return cls

    return decorator
