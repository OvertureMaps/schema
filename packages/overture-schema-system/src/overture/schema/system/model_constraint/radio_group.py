"""
Require at least one field in a group of `bool` fields to have the value `True`.
"""

from collections.abc import Callable
from types import NoneType, UnionType
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict
from pydantic.json_schema import JsonDict
from typing_extensions import override

from .._json_schema import get_static_json_schema_extra, put_one_of
from .model_constraint import FieldGroupConstraint, apply_alias


def radio_group(*field_names: str) -> Callable[[type[BaseModel]], type[BaseModel]]:
    """
    Decorate a Pydantic model class with a constraint requiring that exactly one field in a group of
    `bool` fields has the value `True`.

    This function is the decorator version of the `RadioGroupConstraint` class.

    Historical node for nerds: the term radio group, meaning a group of radio buttons, was first
    used in software user interfaces design as an analogy to the mechanical push buttons on the
    physical home and automobile radio sets of the 1950s-1970s. These radio sets had preset station
    buttons where pushing one button would physically pop out any other buttons, ensuring only one
    station could be selected at a time.

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
    >>> @radio_group("foo", "bar")
    ... class MyModel(BaseModel):
    ...     foo: bool | None = None
    ...     bar: bool = True
    ...
    >>> MyModel()                       # validates OK
    MyModel(foo=None, bar=True)
    >>> MyModel(foo=False)              # validates OK
    MyModel(foo=False, bar=True)
    >>> MyModel(foo=True, bar=False)    # validates OK
    MyModel(foo=True, bar=False)
    >>>
    >>> try:
    ...     MyModel(bar=False)
    ... except ValidationError as e:
    ...    assert (
    ...        "exactly one field from the `bool` field group [foo, bar] must be True, "
    ...        "but none is True"
    ...    ) in str(e)
    ...    print("Validation failed")
    Validation failed
    """
    model_constraint = RadioGroupConstraint._create_internal(
        f"@{radio_group.__name__}", *field_names
    )

    return model_constraint.decorate


class RadioGroupConstraint(FieldGroupConstraint):
    """
    Class implementing the `radio_group` decorator, which can also be used standalone.
    """

    def __init__(self, *field_names: str):
        super().__init__(None, RadioGroupConstraint.__validate_field_names(field_names))

    @classmethod
    def _create_internal(cls, name: str, *field_names: str) -> "RadioGroupConstraint":
        instance = cls.__new__(cls)
        super(RadioGroupConstraint, instance).__init__(
            name, RadioGroupConstraint.__validate_field_names(field_names)
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
    def validate_class(self, model_class: type[BaseModel]) -> None:
        super().validate_class(model_class)

        def is_bool(annotation: type[Any] | None) -> bool:
            if annotation is bool:
                return True
            origin = get_origin(annotation)
            if origin is Annotated:
                return is_bool(get_args(annotation)[0])
            elif get_origin(annotation) in (Union, UnionType):
                args = get_args(annotation)
                return any(is_bool(a) for a in args) and all(
                    is_bool(a) or a in (None, NoneType) for a in args
                )
            else:
                return False

        non_bool_fields = [
            f
            for f in self.field_names
            if not is_bool(model_class.model_fields[f].annotation)
        ]
        if non_bool_fields:
            raise TypeError(
                f"`{self.name}` specifies fields that are have a non-`bool` type in the model class `{model_class.__name__}`: {', '.join(non_bool_fields)}  "
            )

    @override
    def validate_instance(self, model_instance: BaseModel) -> None:
        super().validate_instance(model_instance)

        true_fields = [
            f for f in self.field_names if getattr(model_instance, f) is True
        ]

        if len(true_fields) == 1:
            return
        elif len(true_fields) == 0:
            msg = "none is True"
        elif len(true_fields) == 2:
            msg = (
                f"both of these fields are True: {true_fields[0]} and {true_fields[1]}"
            )
        else:
            msg = f"all of these fields are True: {', '.join(true_fields)}"
        raise ValueError(
            f"exactly one field from the `bool` field group [{', '.join(self.field_names)}] "
            f"must be True, but {msg} (`{self.name}`)"
        )

    @override
    def edit_config(self, model_class: type[BaseModel], config: ConfigDict) -> None:
        super().edit_config(model_class, config)

        json_schema = get_static_json_schema_extra(config)

        def has_true_value(field_name: str) -> JsonDict:
            return {
                "properties": {apply_alias(model_class, field_name): {"const": True}}
            }

        put_one_of(json_schema, [has_true_value(f) for f in self.field_names])
