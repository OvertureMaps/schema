from collections.abc import Callable

from pydantic import BaseModel, ConfigDict
from typing_extensions import override

from .._json_schema import get_static_json_schema
from .model_constraint import ModelConstraint


def min_fields_set(count: int) -> Callable[[type[BaseModel]], type[BaseModel]]:
    """
    Decorates a Pydantic model class with a constraint that requires a minimum number of fields in
    the model to be set to a non-`None` value.

    This function is the decorator version of the `MinFieldsSetConstraint` class.

    Parameters
    ----------
    count : int
        Minimum number of fields that must be set in the model, inclusive of extra fields if they
        are allowed

    Returns
    -------
    type[BaseModel]
        Decorated Pydantic model class

    Example
    -------
    >>> from pydantic import BaseModel, ValidationError
    >>>
    >>> @min_fields_set(1)
    ... class MyModel(BaseModel):
    ...     foo: int | None = None
    ...     bar: str | None = None
    ...
    >>> MyModel(foo=42)                     # validates OK
    MyModel(foo=42, bar=None)
    >>> MyModel(foo=42, bar='baz')          # validates OK
    MyModel(foo=42, bar='baz')
    >>> try:
    ...     MyModel()                       # zero fields are set!
    ... except ValidationError as e:
    ...    print("Validation failed")
    Validation failed
    """
    model_constraint = MinFieldsSetConstraint._create_internal(
        f"@{min_fields_set.__name__}",
        count,
    )

    return model_constraint.decorate


class MinFieldsSetConstraint(ModelConstraint):
    """
    Class implementing the `min_fields_set` decorator, which can also be used standalone.
    """

    def __init__(self, count: int) -> None:
        super().__init__()
        self.__set_count(count)

    @classmethod
    def _create_internal(cls, name: str, count: int) -> "MinFieldsSetConstraint":
        instance = cls.__new__(cls)
        super(MinFieldsSetConstraint, instance).__init__(name)
        instance.__set_count(count)
        return instance

    def __set_count(self, count: int) -> None:
        if not isinstance(count, int):
            raise TypeError(
                f"`count` must be an `int`, but {repr(count)} is a `{type(count).__name__}`"
            )
        elif count < 1:
            raise ValueError(
                f"`count` must be a positive number, but {count} is less than 1"
            )
        self.__count = count

    @property
    def count(self) -> int:
        return self.__count

    @override
    def validate_class(self, model_class: type[BaseModel]) -> None:
        super().validate_class(model_class)

        num_fields = len(model_class.model_fields)
        if num_fields >= self.count:
            return

        extra = model_class.model_config.get("extra", None)
        if not extra == "allow":
            raise TypeError(
                f"`{self.name}` requires a minimum of {self.count} fields to be set, but model "
                f"`{model_class.__name__}` has only {num_fields} explicit fields and does not "
                f"retain extra fields (config 'extra' is to {repr(extra)})"
            )

    @override
    def validate_instance(self, model_instance: BaseModel) -> None:
        super().validate_instance(model_instance)

        num_fields_set = len(model_instance.model_fields_set)
        if num_fields_set < self.count:
            raise ValueError(
                f"only {num_fields_set} fields are explicitly set, but a minimum of {self.count} "
                f"are required (`{self.name})`"
            )

    @override
    def edit_config(self, model_class: type[BaseModel], config: ConfigDict) -> None:
        super().edit_config(model_class, config)

        json_schema = get_static_json_schema(config)

        try:
            prev = json_schema["minProperties"]
            if prev == self.count:
                return
            else:
                raise RuntimeError(
                    f'JSON schema for model class `{model_class.__name__}` has conflicting "minProperties" value {prev}'
                )
        except KeyError:
            pass

        json_schema["minProperties"] = self.count
