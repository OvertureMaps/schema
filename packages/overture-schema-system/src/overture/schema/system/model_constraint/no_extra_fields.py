from pydantic import BaseModel, ConfigDict
from typing_extensions import override

from .model_constraint import ModelConstraint


def no_extra_fields(model_class: type[BaseModel]) -> type[BaseModel]:
    """
    Decorates a Pydantic model class with a constraint that forbids extra fields that aren't
    explicitly part of the model.

    This function is the decorator version of the `NoExtraFieldsConstraint` class. It is syntax
    sugar for, and entirely equivalent to, setting `extra='forbid'` in a model's `ConfigDict`.

    Parameters
    ----------
    model_class: type[BaseModel]
        Pydantic model class being decorated

    Returns
    -------
    type[BaseModel]
        Decorated Pydantic model class

    Example
    -------
    >>> from pydantic import BaseModel, ValidationError
    >>>
    >>> @no_extra_fields
    ... class MyModel(BaseModel):
    ...     foo: int
    ...
    >>> MyModel(foo=42)                     # validates OK
    MyModel(foo=42)
    >>> try:
    ...     MyModel(foo=42, bar="hello")    # extra field `bar` not allowed
    ... except ValidationError as e:
    ...    print("Validation failed")
    Validation failed
    """
    model_constraint = NoExtraFieldsConstraint._create_internal(
        f"@{no_extra_fields.__name__}"
    )

    return model_constraint.attach(model_class)


class NoExtraFieldsConstraint(ModelConstraint):
    """
    Class implementing the `no_extra_fields` decorator, which can also be used standalone.
    """

    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def _create_internal(
        cls, name: str, *field_names: str
    ) -> "NoExtraFieldsConstraint":
        instance = cls.__new__(cls)
        super(NoExtraFieldsConstraint, instance).__init__(name)
        return instance

    @override
    def validate_class(self, model_class: type[BaseModel]) -> None:
        config = model_class.model_config
        extra = config.get("extra", None)
        if extra and extra != "forbid":
            raise TypeError(
                f'can\'t apply `{self.name}` to model class `{model_class.__name__}: existing `model_config["extra"]` is already set to {repr(extra)}'
            )

    @override
    def edit_config(self, model_class: type[BaseModel], config: ConfigDict) -> None:
        config["extra"] = "forbid"
