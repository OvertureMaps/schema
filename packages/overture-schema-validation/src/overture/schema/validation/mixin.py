"""Mixin-based constraint validation system with decorators.

This module provides a structured approach to model-level validation with proper JSON
Schema generation.
"""

from abc import ABC, abstractmethod
from typing import Any, cast

from pydantic import BaseModel, model_validator


def resolve_field_names(
    model_class: type[BaseModel], field_names: list[str], by_alias: bool = True
) -> list[str]:
    """Resolve field names to their aliases when generating JSON schema.

    Args:
        model_class: The Pydantic model class to resolve field names for
        field_names: List of field names to resolve
        by_alias: If True, resolve to field aliases; if False, return original names

    Returns:
        List of resolved field names (aliases if by_alias=True, original names otherwise)

    Example:
        Given a model with field `class_` aliased to `class`:
        resolve_field_names(MyModel, ["class_"], by_alias=True) -> ["class"]
        resolve_field_names(MyModel, ["class_"], by_alias=False) -> ["class_"]
    """
    if not by_alias:
        return field_names

    resolved_names = []
    for field_name in field_names:
        resolved_name = _resolve_single_field_name(model_class, field_name)
        resolved_names.append(resolved_name)

    return resolved_names


def _resolve_single_field_name(model_class: type[BaseModel], field_name: str) -> str:
    """Resolve a single field name to its alias if it exists."""
    # Check if the field exists in the model
    if not (
        hasattr(model_class, "model_fields") and field_name in model_class.model_fields
    ):
        return field_name

    field_info = model_class.model_fields[field_name]

    # Return alias if it exists, otherwise return the original field name
    if hasattr(field_info, "alias") and field_info.alias is not None:
        return field_info.alias

    return field_name


class BaseConstraintValidator(ABC):
    """Base class for constraint validators."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    @abstractmethod
    def validate(self, model_instance: BaseModel) -> None:
        """Validate the constraint against the model instance."""
        pass

    @abstractmethod
    def get_metadata(
        self, model_class: type[BaseModel] | None = None, by_alias: bool = True
    ) -> dict[str, Any]:
        """Return plain constraint metadata."""
        pass

    @abstractmethod
    def apply_json_schema_metadata(
        self,
        target_schema: dict[str, Any],
        model_class: type[BaseModel] | None = None,
        by_alias: bool = True,
    ) -> None:
        """Apply this constraint's modifications directly to the target schema."""
        pass


class MinPropertiesValidator(BaseConstraintValidator):
    """Validates that at least N properties are set on a model."""

    def __init__(self, min_count: int):
        super().__init__()
        self.min_count = min_count

    def validate(self, model_instance: BaseModel) -> None:
        # Count all properties that are set (not None)
        set_count = 0

        # Get all field names from the model class
        field_names = getattr(model_instance.__class__, "model_fields", {}).keys()

        for field_name in field_names:
            if hasattr(model_instance, field_name):
                field_value = getattr(model_instance, field_name)
                if field_value is not None:
                    set_count += 1

        if set_count < self.min_count:
            raise ValueError(
                f"At least {self.min_count} properties must be set, but only {set_count} are set"
            )

    def get_metadata(
        self, model_class: type[BaseModel] | None = None, by_alias: bool = True
    ) -> dict[str, Any]:
        return {
            "type": "min_properties",
            "min_count": self.min_count,
        }

    def apply_json_schema_metadata(
        self,
        target_schema: dict[str, Any],
        model_class: type[BaseModel] | None = None,
        by_alias: bool = True,
    ) -> None:
        """Apply minProperties constraint to the schema."""
        metadata = self.get_metadata(model_class, by_alias)

        target_schema["minProperties"] = metadata["min_count"]


def register_constraint(
    model_class: type[BaseModel], constraint: BaseConstraintValidator
) -> None:
    """Register a constraint for a model class."""
    if not hasattr(model_class, "__constraints__"):
        model_class.__constraints__ = []  # type: ignore[attr-defined]
    else:
        # Ensure we have a copy of the constraints list for this class
        # to avoid sharing references between classes
        constraints = getattr(model_class, "__constraints__", [])
        model_class.__constraints__ = constraints.copy()  # type: ignore[attr-defined]
    constraints = model_class.__constraints__  # type: ignore[attr-defined]
    constraints.append(constraint)


def min_properties(min_count: int) -> Any:
    """Decorator to add minimum properties validation."""

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        constraint = MinPropertiesValidator(min_count)
        register_constraint(cls, constraint)
        return cls

    return decorator


# Mixin class with constraint validation
class ConstraintValidatedModel:
    """Mixin class that provides constraint validation capabilities.

    This is a true mixin - it doesn't inherit from BaseModel to avoid MRO issues.
    Use it like: class MyModel(ConstraintValidatedModel, BaseModel)
    """

    @model_validator(mode="after")
    def validate_constraints(self) -> "ConstraintValidatedModel":
        """Run all registered constraints for this model and its parent classes."""
        all_constraints: list[BaseConstraintValidator] = []

        # Collect constraints from this class and all parent classes
        # Use a more sophisticated approach to avoid cross-contamination
        for cls in self.__class__.__mro__:
            # Skip if this class has no constraints of its own
            if not hasattr(cls, "__constraints__"):
                continue

            # Only include constraints that were explicitly added to this class
            # (not inherited from shared base classes)
            class_constraints = getattr(cls, "__constraints__", [])
            if class_constraints:
                all_constraints.extend(class_constraints)

        # Run all constraints
        for constraint in all_constraints:
            # Cast self to BaseModel for the constraint validator
            constraint.validate(self)  # type: ignore[arg-type]
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: Any, handler: Any
    ) -> dict[str, Any]:
        """Generate JSON Schema with constraints applied."""
        # Get the base schema from Pydantic
        schema: dict[str, Any] = handler(core_schema)

        # Apply constraint metadata
        all_constraints: list[BaseConstraintValidator] = []
        class_constraints = getattr(cls, "__constraints__", [])
        if class_constraints:
            all_constraints.extend(class_constraints)

        for constraint in all_constraints:
            # Apply constraint modifications directly to the schema
            # OvertureFeature will handle moving them to the correct GeoJSON structure if needed
            constraint.apply_json_schema_metadata(
                target_schema=schema,
                model_class=cast(type[BaseModel], cls),
                by_alias=True,
            )

        return schema
