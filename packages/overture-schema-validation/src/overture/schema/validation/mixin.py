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
    def get_json_schema_metadata(
        self, model_class: type[BaseModel] | None = None, by_alias: bool = True
    ) -> dict[str, Any]:
        """Return JSON Schema metadata for this constraint."""
        pass


class RequiredIfValidator(BaseConstraintValidator):
    """Validates conditional field requirements."""

    def __init__(
        self, condition_field: str, condition_value: Any, required_fields: list[str]
    ):
        super().__init__()
        self.condition_field = condition_field
        self.condition_value = condition_value
        self.required_fields = required_fields

    def validate(self, model_instance: BaseModel) -> None:
        if hasattr(model_instance, self.condition_field):
            condition_value = getattr(model_instance, self.condition_field)
            if condition_value == self.condition_value:
                for field_name in self.required_fields:
                    if (
                        not hasattr(model_instance, field_name)
                        or getattr(model_instance, field_name) is None
                    ):
                        raise ValueError(
                            f"Field '{field_name}' is required when "
                            f"{self.condition_field} = {self.condition_value}"
                        )

    def get_json_schema_metadata(
        self, model_class: type[BaseModel] | None = None, by_alias: bool = True
    ) -> dict[str, Any]:
        # Resolve field names to aliases if needed
        condition_field = self.condition_field
        required_fields = self.required_fields

        if model_class is not None:
            resolved_condition = resolve_field_names(
                model_class, [condition_field], by_alias
            )
            resolved_required = resolve_field_names(
                model_class, required_fields, by_alias
            )
            condition_field = resolved_condition[0]
            required_fields = resolved_required

        condition_value = self.condition_value

        return {
            "type": "required_if",
            "condition_field": condition_field,
            "condition_value": condition_value,
            "required_fields": required_fields,
            "if": {"properties": {condition_field: {"const": condition_value}}},
            "then": {"required": required_fields},
        }


class NotRequiredIfValidator(BaseConstraintValidator):
    """Validates conditional field NOT requirements (field should be None when condition
    is met)."""

    def __init__(
        self, condition_field: str, condition_value: Any, not_required_fields: list[str]
    ):
        super().__init__()
        self.condition_field = condition_field
        self.condition_value = condition_value
        self.not_required_fields = not_required_fields

    def validate(self, model_instance: BaseModel) -> None:
        if hasattr(model_instance, self.condition_field):
            condition_value = getattr(model_instance, self.condition_field)
            if condition_value != self.condition_value:
                for field_name in self.not_required_fields:
                    if (
                        not hasattr(model_instance, field_name)
                        or getattr(model_instance, field_name) is None
                    ):
                        raise ValueError(
                            f"Field '{field_name}' is required when "
                            f"{self.condition_field} != {self.condition_value}"
                        )

    def get_json_schema_metadata(
        self, model_class: type[BaseModel] | None = None, by_alias: bool = True
    ) -> dict[str, Any]:
        # Resolve field names to aliases if needed
        condition_field = self.condition_field
        not_required_fields = self.not_required_fields

        if model_class is not None:
            resolved_condition = resolve_field_names(
                model_class, [condition_field], by_alias
            )
            resolved_not_required = resolve_field_names(
                model_class, not_required_fields, by_alias
            )
            condition_field = resolved_condition[0]
            not_required_fields = resolved_not_required

        condition_value = self.condition_value

        return {
            "type": "not_required_if",
            "condition_field": condition_field,
            "condition_value": condition_value,
            "not_required_fields": not_required_fields,
            "if": {
                "properties": {condition_field: {"not": {"const": condition_value}}}
            },
            "then": {"required": not_required_fields},
        }


class AnyOfValidator(BaseConstraintValidator):
    """Validates that any of a set of fields is present."""

    def __init__(self, *field_names: str):
        super().__init__()
        self.field_names = field_names

    def validate(self, model_instance: BaseModel) -> None:
        present_fields = []
        for field_name in self.field_names:
            if (
                hasattr(model_instance, field_name)
                and getattr(model_instance, field_name) is not None
            ):
                present_fields.append(field_name)

        if not present_fields:
            raise ValueError(
                f"At least one of {', '.join(self.field_names)} must be present"
            )

    def get_json_schema_metadata(
        self, model_class: type[BaseModel] | None = None, by_alias: bool = True
    ) -> dict[str, Any]:
        # Resolve field names to aliases if needed
        field_names = list(self.field_names)
        if model_class is not None:
            field_names = resolve_field_names(model_class, field_names, by_alias)

        return {
            "anyOf": [{"required": [field]} for field in field_names],
        }


class ExactlyOneOfValidator(BaseConstraintValidator):
    """Validates that exactly one of multiple boolean fields is true."""

    def __init__(self, *field_names: str):
        super().__init__()
        self.field_names = field_names

    def validate(self, model_instance: BaseModel) -> None:
        true_fields = []
        missing_fields = []

        for field_name in self.field_names:
            if hasattr(model_instance, field_name):
                field_value = getattr(model_instance, field_name)
                if field_value is True:
                    true_fields.append(field_name)
            else:
                missing_fields.append(field_name)

        # If all fields are missing, gracefully handle it (don't validate)
        if len(missing_fields) == len(self.field_names):
            return

        if len(true_fields) != 1:
            if len(true_fields) == 0:
                raise ValueError(
                    f"Exactly one of {', '.join(self.field_names)} must be true"
                )
            else:
                raise ValueError(
                    f"Exactly one field must be true, but found {len(true_fields)}: {', '.join(true_fields)}"
                )

    def get_json_schema_metadata(
        self, model_class: type[BaseModel] | None = None, by_alias: bool = True
    ) -> dict[str, Any]:
        # Resolve field names to aliases if needed
        field_names = list(self.field_names)
        if model_class is not None:
            field_names = resolve_field_names(model_class, field_names, by_alias)

        # Generate oneOf constraint where exactly one field is true
        # This matches the reference schema format
        one_of_clauses = []
        for field in field_names:
            clause = {"properties": {field: {"const": True}}}
            one_of_clauses.append(clause)

        return {
            "type": "exactly_one_of",
            "fields": field_names,
            "oneOf": one_of_clauses,
        }


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

    def get_json_schema_metadata(
        self, model_class: type[BaseModel] | None = None, by_alias: bool = True
    ) -> dict[str, Any]:
        return {
            "type": "min_properties",
            "minProperties": self.min_count,
        }


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


def required_if(
    condition_field: str, condition_value: Any, required_fields: list[str]
) -> Any:
    """Decorator to add conditional required field validation."""

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        constraint = RequiredIfValidator(
            condition_field, condition_value, required_fields
        )
        register_constraint(cls, constraint)
        return cls

    return decorator


def any_of(*field_names: str) -> Any:
    """Decorator to add anyOf validation."""

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        constraint = AnyOfValidator(*field_names)
        register_constraint(cls, constraint)
        return cls

    return decorator


def exactly_one_of(*field_names: str) -> Any:
    """Decorator to add exactly-one-of validation where fields must be true."""

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        constraint = ExactlyOneOfValidator(*field_names)
        register_constraint(cls, constraint)
        return cls

    return decorator


def not_required_if(
    condition_field: str, condition_value: Any, not_required_fields: list[str]
) -> Any:
    """Decorator to add conditional not-required field validation."""

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        constraint = NotRequiredIfValidator(
            condition_field, condition_value, not_required_fields
        )
        register_constraint(cls, constraint)
        return cls

    return decorator


def min_properties(min_count: int) -> Any:
    """Decorator to add minimum properties validation."""

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        constraint = MinPropertiesValidator(min_count)
        register_constraint(cls, constraint)
        return cls

    return decorator


def allow_extension_fields() -> Any:
    """Decorator to allow only ext_* prefixed extension fields."""

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        constraint = ExtensionPrefixValidator()
        register_constraint(cls, constraint)
        return cls

    return decorator


class ExtensionPrefixValidator(BaseConstraintValidator):
    """Validates that extra fields use ext_ prefix only."""

    def validate(self, model_instance: BaseModel) -> None:
        """Validate that extra fields use allowed prefixes."""
        if (
            hasattr(model_instance, "__pydantic_extra__")
            and model_instance.__pydantic_extra__
        ):
            for field_name in model_instance.__pydantic_extra__.keys():
                if not field_name.startswith("ext_"):
                    raise ValueError(
                        f"Unrecognized field '{field_name}' must use ext_ prefix"
                    )

    def get_json_schema_metadata(
        self, model_class: type[BaseModel] | None = None, by_alias: bool = True
    ) -> dict[str, Any]:
        """Return JSON Schema metadata for extension prefix constraint."""
        return {
            "type": "extension_prefix",
            "patternProperties": {
                "^ext_.*$": {
                    "description": "Additional top-level properties must be prefixed with `ext_`."
                }
            },
            "additionalProperties": False,
        }


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
            constraint_metadata = constraint.get_json_schema_metadata(
                model_class=cast(type[BaseModel], cls), by_alias=True
            )
            if not constraint_metadata:
                continue

            # Apply constraints to the current schema
            # OvertureFeature will handle moving them to the correct GeoJSON structure if needed
            target_schema = schema

            # Handle extension prefix constraint
            if constraint_metadata.get("type") == "extension_prefix":
                if constraint_metadata.get("patternProperties"):
                    target_schema["patternProperties"] = constraint_metadata[
                        "patternProperties"
                    ]
                if constraint_metadata.get("additionalProperties") is False:
                    target_schema["additionalProperties"] = False
                continue

            # Handle min_properties constraint
            if constraint_metadata.get("type") == "min_properties":
                if constraint_metadata.get("minProperties"):
                    target_schema["minProperties"] = constraint_metadata[
                        "minProperties"
                    ]
                continue

            # Handle parent_division_required_unless constraint
            if constraint_metadata.get("type") == "parent_division_required_unless":
                conditional_schema = {"if": constraint_metadata["if"]}
                if constraint_metadata.get("then"):
                    conditional_schema["then"] = constraint_metadata["then"]
                if constraint_metadata.get("else"):
                    conditional_schema["else"] = constraint_metadata["else"]

                target_schema.setdefault("allOf", []).append(conditional_schema)
                continue

            # Handle conditional constraints
            if constraint_metadata.get("if"):
                conditional_schema = {"if": constraint_metadata["if"]}
                if constraint_metadata.get("then"):
                    conditional_schema["then"] = constraint_metadata["then"]
                if constraint_metadata.get("else"):
                    conditional_schema["else"] = constraint_metadata["else"]

                target_schema.setdefault("allOf", []).append(conditional_schema)

            if constraint_metadata.get("anyOf"):
                target_schema.setdefault("anyOf", []).extend(
                    constraint_metadata["anyOf"]
                )

            if constraint_metadata.get("oneOf"):
                target_schema.setdefault("oneOf", []).extend(
                    constraint_metadata["oneOf"]
                )

            if constraint_metadata.get("allOf"):
                target_schema.setdefault("allOf", []).extend(
                    constraint_metadata["allOf"]
                )

            if constraint_metadata.get("not"):
                target_schema.setdefault("allOf", []).append(
                    {"not": constraint_metadata["not"]}
                )

        return schema
