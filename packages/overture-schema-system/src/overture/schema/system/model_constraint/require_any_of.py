from collections.abc import Callable

from pydantic import BaseModel, ConfigDict
from pydantic.json_schema import JsonDict
from typing_extensions import override

from .json_schema import get_static_json_schema, put_any_of
from .model_constraint import OptionalFieldGroupConstraint, apply_alias


def require_any_of(*field_names: str) -> Callable[[type[BaseModel]], type[BaseModel]]:
    """
    Decorates a Pydantic model class with a constraint requiring that at least one of the named
    fields has a value.

    This function is the decorator version of the `RequireAnyOfConstraint` class.

    Parameters
    ----------
    *field_names : str
        Varargs list of at least two unique field names.

    Returns
    -------
    Callable
        Decorator factory

    Example
    -------
    >>> from pydantic import BaseModel, ValidationError
    >>>
    >>> @require_any_of("foo", "bar")
    ... class MyModel(BaseModel):
    ...     foo: int | None = None
    ...     bar: str | None = None
    ...
    >>> MyModel(foo=42, bar="hello")    # validates OK
    MyModel(foo=42, bar='hello')
    >>> MyModel(foo=42)                 # validates OK
    MyModel(foo=42, bar=None)
    >>> MyModel(bar="hello")            # validates OK
    MyModel(foo=None, bar='hello')
    >>>
    >>> try:
    ...     MyModel(foo=None, bar=None)
    ... except ValidationError as e:
    ...    assert "at least one of these fields must have a value, but none do: foo, bar" in str(e)
    ...    print("Validation failed")
    Validation failed
    """
    model_constraint = RequireAnyOfConstraint._create_internal(
        f"@{require_any_of.__name__}", *field_names
    )

    return model_constraint.decorate


class RequireAnyOfConstraint(OptionalFieldGroupConstraint):
    """
    Class implementing the `require_any_of` decorator, which can also be used standalone.
    """

    def __init__(self, *field_names: str):
        super().__init__(
            None, RequireAnyOfConstraint.__validate_field_names(field_names)
        )

    @classmethod
    def _create_internal(cls, name: str, *field_names: str) -> "RequireAnyOfConstraint":
        instance = cls.__new__(cls)
        super(RequireAnyOfConstraint, instance).__init__(
            name, RequireAnyOfConstraint.__validate_field_names(field_names)
        )
        return instance

    @staticmethod
    def __validate_field_names(field_names: tuple[str, ...]) -> tuple[str, ...]:
        if len(field_names) < 2:
            raise ValueError(
                f"`field_names` must contain at least two items, but {field_names} has only {len(field_names)}"
            )
        return field_names

    @override
    def validate_instance(self, model_instance: BaseModel) -> None:
        super().validate_instance(model_instance)

        if not (any(getattr(model_instance, f) is not None for f in self.field_names)):
            raise ValueError(
                f"at least one of these fields must have a value, but none do: {', '.join(self.field_names)} (`{self.name}`)"
            )

    @override
    def edit_config(self, model_class: type[BaseModel], config: ConfigDict) -> None:
        super().edit_config(model_class, config)

        json_schema = get_static_json_schema(config)

        def required(field_name: str) -> JsonDict:
            return {"required": [apply_alias(model_class, field_name)]}

        put_any_of(json_schema, [required(f) for f in self.field_names])
