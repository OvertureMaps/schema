from collections.abc import Callable

from pydantic import BaseModel, ConfigDict
from pydantic.json_schema import to_jsonable_python
from typing_extensions import override

from .json_schema import get_static_json_schema, put_if
from .model_constraint import OptionalFieldGroupConstraint, apply_alias


def forbid_fields_if(
    field_names: list[str] | tuple[str, ...],
    condition_field_name: str,
    condition_value: object,
) -> Callable[[type[BaseModel]], type[BaseModel]]:
    """
    Decorates a Pydantic model class with a constraint forbidding any of the named fields from
    a value, but only if the named condition field has a specific value.

    Parameters
    ----------
    field_names : list[str] | tuple[str, ...]
        List or tuple containing at least two unique field names to be conditionally forbidden.
    condition_field_name :
        Name of the field whose value determines whether to forbid the other named fields.
    condition_field_value :
        Value of the conditional field that caused the other named fields to be forbidden.

    Returns
    -------
    Callable
        Decorator factory

    Example
    -------
    >>> from pydantic import BaseModel, ValidationError
    >>>
    >>> @forbid_fields_if(['bar', 'baz'], 'foo', 'special value')
    ... class MyModel(BaseModel):
    ...     foo: str
    ...     bar: int | None = None
    ...     baz: str | None = None
    ...
    >>> MyModel(foo='something', bar=42, baz='qux')     # validates OK
    MyModel(foo='something', bar=42, baz='qux')
    >>> MyModel(foo='special value')                    # validates OK because bar/baz are omitted
    MyModel(foo='special value', bar=None, baz=None)
    >>>
    >>> try:
    ...     MyModel(foo='special value', bar=42)
    ... except ValidationError as e:
    ...     assert (
    ...         "at least one field has a value when it should not: bar - these field value(s) "
    ...         "are forbidden because field foo has value 'special value'"
    ...     ) in str(e)
    ...     print('Validation failed')
    Validation failed
    """

    model_constraint = ForbidFieldsIfConstraint._create_internal(
        f"@{forbid_fields_if.__name__}",
        field_names,
        condition_field_name,
        condition_value,
    )

    return model_constraint.decorate


class ForbidFieldsIfConstraint(OptionalFieldGroupConstraint):
    """
    Class implementing the `forbid_fields_if` decorator, which can also be used standalone.
    """

    def __init__(
        self,
        field_names: list[str] | tuple[str, ...],
        condition_field_name: str,
        condition_value: object,
    ):
        super().__init__(None, tuple(field_names))
        self.__set_condition(condition_field_name, condition_value)

    @classmethod
    def _create_internal(
        cls,
        name: str,
        field_names: list[str] | tuple[str, ...],
        condition_field_name: str,
        condition_value: object,
    ) -> "ForbidFieldsIfConstraint":
        instance = cls.__new__(cls)
        super(ForbidFieldsIfConstraint, instance).__init__(name, tuple(field_names))
        instance.__set_condition(condition_field_name, condition_value)
        return instance

    def __set_condition(
        self, condition_field_name: str, condition_value: object
    ) -> None:
        if not isinstance(condition_field_name, str):
            raise TypeError(
                f"`condition_field_name` must be a `str`, but {condition_field_name} is a {type(condition_field_name).__name__} (`{self.name}`)"
            )
        self.__condition_field_name = condition_field_name
        self.__condition_value = condition_value

    @override
    def validate_instance(self, model_instance: BaseModel) -> None:
        super().validate_instance(model_instance)

        actual_value = getattr(model_instance, self.__condition_field_name)
        if actual_value != self.__condition_value:
            return

        present_fields = [
            f for f in self.field_names if getattr(model_instance, f) is not None
        ]
        if present_fields:
            raise ValueError(
                f"at least one field has a value when it should not: {', '.join(present_fields)} - "
                f"these field value(s) are forbidden because field {self.__condition_field_name} "
                f"has value {repr(self.__condition_value)} (`{self.name}`)"
            )

    @override
    def validate_class(self, model_class: type[BaseModel]) -> None:
        super().validate_class(model_class)

        if self.__condition_field_name not in model_class.model_fields:
            raise TypeError(
                f"`{self.name}` expects the model class `{model_class.__name__}` to contain the condition field {repr(self.__condition_field_name)}, but it does not"
            )

    @override
    def edit_config(self, model_class: type[BaseModel], config: ConfigDict) -> None:
        super().edit_config(model_class, config)

        json_schema = get_static_json_schema(config)

        put_if(
            json_schema,
            {
                "properties": {
                    self.__condition_field_name: {
                        "not": {"const": to_jsonable_python(self.__condition_value)}
                    }
                }
            },
            {"required": [apply_alias(model_class, f) for f in self.field_names]},
        )
