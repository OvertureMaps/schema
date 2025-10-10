from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel


# Temporarily copied in from validation package.
class BaseConstraintValidator(ABC):
    """Base class for constraint validators."""

    def __init__(self, *args: object, **kwargs: object) -> None:
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


# Temporarily copied in from validation package.
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


def allow_extension_fields() -> Callable:
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

    def get_metadata(
        self, model_class: type[BaseModel] | None = None, by_alias: bool = True
    ) -> dict[str, Any]:
        """Return plain constraint metadata."""
        return {
            "type": "extension_prefix",
            "pattern": "^ext_.*$",
            "description": "Additional top-level properties must be prefixed with `ext_`.",
            "additional_properties": False,
        }

    def apply_json_schema_metadata(
        self,
        target_schema: dict[str, Any],
        model_class: type[BaseModel] | None = None,
        by_alias: bool = True,
    ) -> None:
        """Apply extension prefix constraint to the schema."""
        metadata = self.get_metadata(model_class, by_alias)

        target_schema["patternProperties"] = {
            metadata["pattern"]: {"description": metadata["description"]}
        }
        if metadata["additional_properties"] is False:
            target_schema["additionalProperties"] = False
