from collections import Counter
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict
from pydantic.json_schema import JsonDict
from typing_extensions import override

from .json_schema import get_static_json_schema, put_any_of
from .model_constraint import ModelConstraint, apply_alias


def require_any_of(*field_names: str) -> Callable[[type[BaseModel]], type[BaseModel]]:
    """
    Decorates a Pydantic model class with a constraint requiring that at least one of the named
    fields has a value.

    This function is the decorator version of the `RequireAnyOf` class.

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
    ...     foo: int | None
    ...     bar: str | None
    ...
    >>> MyModel(foo=42, bar="hello")    # validates OK
    MyModel(foo=42, bar='hello')
    >>> MyModel(foo=42, bar=None)       # validates OK
    MyModel(foo=42, bar=None)
    >>> MyModel(foo=None, bar="hello")  # validates OK
    MyModel(foo=None, bar='hello')
    >>>
    >>> try:
    ...     MyModel(foo=None, bar=None)
    ... except ValidationError as e:
    ...    assert "at least one of these fields must have a value, but none do: bar, foo" in str(e)
    ...    print("Validation failed")
    Validation failed
    """
    model_constraint = RequireAnyOfConstraint._create_internal(
        f"@{require_any_of.__name__}", *field_names
    )

    return model_constraint.attach


class RequireAnyOfConstraint(ModelConstraint):
    """
    Class implementing the `require_any_of` decorator, which can also be used standalone.
    """

    def __init__(self, *field_names: str):
        super().__init__()
        self.__set_field_names(field_names)

    @classmethod
    def _create_internal(cls, name: str, *field_names: str) -> "RequireAnyOfConstraint":
        instance = cls.__new__(cls)
        super(RequireAnyOfConstraint, instance).__init__(name)
        instance.__set_field_names(field_names)
        return instance

    def __set_field_names(self, field_names: tuple[str, ...]) -> None:
        if not isinstance(field_names, tuple):
            raise TypeError(
                f"`field_names` must be a `tuple`, but {field_names} is a `{type(field_names).__name__}"
            )
        elif (
            len(field_names) < 2
        ):  # Minimum 2 field names: a field constraint is more appropriate if only 1 field.
            raise ValueError(
                f"`field_names` must contain at least two items, {field_names} does not"
            )
        elif not all(isinstance(s, str) for s in field_names):
            raise TypeError(
                f"`field_names` must contain only `str` values, but {field_names} contains at least one non-string"
            )
        dupes = [s for s, count in Counter(field_names).items() if count > 1]
        if dupes:
            raise ValueError(
                f"`field_names` must not contain duplicates, but {field_names} contains at least one repeated value"
            )
        self.__field_names = tuple(sorted(field_names))

    @property
    def field_names(self) -> tuple[str, ...]:
        return self.__field_names

    @override
    def validate_class(self, model_class: type[BaseModel]) -> None:
        missing_fields = [
            f for f in self.field_names if f not in model_class.model_fields
        ]
        if missing_fields:
            raise TypeError(
                f"`{self.name}` specifies fields that are not in the model class `{model_class.__name__}`: {', '.join(missing_fields)}  "
            )

    @override
    def validate_instance(self, model_instance: BaseModel) -> None:
        if not (any(getattr(model_instance, f) is not None for f in self.field_names)):
            raise ValueError(
                f"at least one of these fields must have a value, but none do: {', '.join(self.field_names)} (`{self.name}`)"
            )

    @override
    def edit_config(self, model_class: type[BaseModel], config: ConfigDict) -> None:
        json_schema = get_static_json_schema(config)

        def required(field_name: str) -> JsonDict:
            return {"required": [apply_alias(model_class, field_name)]}

        put_any_of(json_schema, [required(f) for f in self.field_names])
