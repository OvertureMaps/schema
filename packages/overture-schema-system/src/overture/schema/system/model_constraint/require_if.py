from collections.abc import Callable

from pydantic import BaseModel, ConfigDict
from typing_extensions import override

from .json_schema import get_static_json_schema, put_if
from .model_constraint import (
    Condition,
    OptionalFieldGroupConstraint,
    apply_alias,
)


def require_if(
    field_names: list[str] | tuple[str, ...],
    condition: Condition,
) -> Callable[[type[BaseModel]], type[BaseModel]]:
    """
    Decorates a Pydantic model class with a constraint requiring all of the named fields to have a
    value, but only if a field value condition is true.

    Parameters
    ----------
    field_names : list[str] | tuple[str, ...]
        List or tuple containing at least one unique field name to be conditionally required.
    condition : Condition
        Condition that must be true to require the named fields

    Returns
    -------
    Callable
        Decorator factory

    Example
    -------
    >>> from pydantic import BaseModel, ValidationError
    >>> from overture.schema.system.model_constraint import FieldEqCondition
    >>>
    >>> @require_if(['bar', 'baz'], FieldEqCondition('foo', 'special value'))
    ... class MyModel(BaseModel):
    ...     foo: str
    ...     bar: int | None = None
    ...     baz: str | None = None
    ...
    >>> MyModel(foo='something')                        # validates OK
    MyModel(foo='something', bar=None, baz=None)
    >>> MyModel(foo='special value', bar=42, baz='qux') # validates OK because bar/baz are provided
    MyModel(foo='special value', bar=42, baz='qux')
    >>>
    >>> try:
    ...     MyModel(foo='special value')
    ... except ValidationError as e:
    ...     assert 'at least one field is missing a value when it should have one: bar, baz' in str(e)
    ...     print('Validation failed')
    Validation failed
    """

    model_constraint = RequireIfConstraint._create_internal(
        f"@{require_if.__name__}",
        field_names,
        condition,
    )

    return model_constraint.decorate


class RequireIfConstraint(OptionalFieldGroupConstraint):
    """
    Class implementing the `require_if` decorator, which can also be used standalone.
    """

    def __init__(
        self,
        field_names: list[str] | tuple[str, ...],
        condition: Condition,
    ):
        super().__init__(None, tuple(field_names))
        self.__set_condition(condition)

    @classmethod
    def _create_internal(
        cls,
        name: str,
        field_names: list[str] | tuple[str, ...],
        condition: Condition,
    ) -> "RequireIfConstraint":
        instance = cls.__new__(cls)
        super(RequireIfConstraint, instance).__init__(name, tuple(field_names))
        instance.__set_condition(condition)
        return instance

    def __set_condition(self, condition: Condition) -> None:
        if not isinstance(condition, Condition):
            raise TypeError(
                f"`condition` must be a `{Condition.__name__}`, but {repr(condition)} is a {type(condition).__name__} (`{self.name}`)"
            )
        self.__condition = condition

    @override
    def validate_instance(self, model_instance: BaseModel) -> None:
        super().validate_instance(model_instance)

        if not self.__condition.eval(model_instance):
            return

        missing_fields = [
            f for f in self.field_names if getattr(model_instance, f) is None
        ]

        if missing_fields:
            raise ValueError(
                f"at least one field is missing a value when it should have one: {', '.join(missing_fields)} - "
                f"these field value(s) are required because {self.__condition} is true`)"
            )

    @override
    def validate_class(self, model_class: type[BaseModel]) -> None:
        super().validate_class(model_class)

        self.__condition.validate_class(model_class)

    @override
    def edit_config(self, model_class: type[BaseModel], config: ConfigDict) -> None:
        super().edit_config(model_class, config)

        json_schema = get_static_json_schema(config)

        put_if(
            json_schema,
            self.__condition.json_schema(model_class),
            {"required": [apply_alias(model_class, f) for f in self.field_names]},
        )
