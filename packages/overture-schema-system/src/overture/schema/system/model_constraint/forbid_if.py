"""
Prohibit every field in a group of fields from having a non-null value, but only if a condition
is true.
"""

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict
from typing_extensions import override

from .._json_schema import get_static_json_schema_extra, put_if, required_non_null
from .model_constraint import (
    Condition,
    OptionalFieldGroupConstraint,
    apply_alias,
)


def forbid_if(
    field_names: list[str] | tuple[str, ...],
    condition: Condition,
) -> Callable[[type[BaseModel]], type[BaseModel]]:
    """
    Decorate a Pydantic model class with a constraint forbidding any of the named fields from
    holding a non-null value, but only if a field value condition is true.

    To ensure parity between Python and JSON Schema validation, a field's value must be explicitly
    set to a non-null value to violate the constraint. This means in particular that fields whose
    value was set by Pydantic using a default value do not count as violating the prohibition, and
    fields containing the value `None`, even if explicitly set, do not count as violating the
    prohibition.

    Parameters
    ----------
    field_names : list[str] | tuple[str, ...]
        List or tuple containing at least one unique field name to be conditionally forbidden.
    condition : Condition
        Condition that must be true to forbid the named fields

    Returns
    -------
    Callable
        Decorator factory

    Example
    -------
    >>> from pydantic import BaseModel, ValidationError
    >>> from overture.schema.system.model_constraint import FieldEqCondition
    >>>
    >>> @forbid_if(['bar', 'baz'], FieldEqCondition('foo', 'special value'))
    ... class MyModel(BaseModel):
    ...     foo: str
    ...     bar: int | None = None
    ...     baz: str | None = None
    ...
    >>> MyModel(foo='something', bar=42, baz='qux')     # validates OK
    MyModel(foo='something', bar=42, baz='qux')
    >>> MyModel(foo='special value')                    # validates OK because bar/baz are omitted
    MyModel(foo='special value', bar=None, baz=None)
    >>> MyModel(foo='special value', bar=None)          # validates OK because None doesn't violate
    MyModel(foo='special value', bar=None, baz=None)
    >>>
    >>> try:
    ...     MyModel(foo='special value', bar=42)
    ... except ValidationError as e:
    ...     assert 'at least one field has a non-null value when it should not: bar' in str(e)
    ...     print('Validation failed')
    Validation failed
    """
    model_constraint = ForbidIfConstraint._create_internal(
        f"@{forbid_if.__name__}",
        field_names,
        condition,
    )

    return model_constraint.decorate


class ForbidIfConstraint(OptionalFieldGroupConstraint):
    """
    Class implementing the `forbid_if` decorator, which can also be used standalone.
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
    ) -> "ForbidIfConstraint":
        instance = cls.__new__(cls)
        super(ForbidIfConstraint, instance).__init__(name, tuple(field_names))
        instance.__set_condition(condition)
        return instance

    def __set_condition(self, condition: Condition) -> None:
        if not isinstance(condition, Condition):
            raise TypeError(
                f"`condition` must be a `{Condition.__name__}`, but {repr(condition)} has type `{type(condition).__name__}` (`{self.name}`)"
            )
        self.__condition = condition

    @property
    def condition(self) -> Condition:
        return self.__condition

    @override
    def validate_class(self, model_class: type[BaseModel]) -> None:
        super().validate_class(model_class)

        self.__condition.validate_class(model_class)

    @override
    def validate_instance(self, model_instance: BaseModel) -> None:
        super().validate_instance(model_instance)

        if not self.__condition.eval(model_instance):
            return

        present_fields = [
            f
            for f in self.field_names
            if self._field_has_non_null_value(model_instance, f)
        ]

        if present_fields:
            raise ValueError(
                f"at least one field has a non-null value when it should not: {', '.join(present_fields)} - "
                f"these field value(s) are forbidden because {self.__condition} is true "
                f"(`{self.name}`)"
            )

    @override
    def edit_config(self, model_class: type[BaseModel], config: ConfigDict) -> None:
        super().edit_config(model_class, config)

        json_schema = get_static_json_schema_extra(config)

        aliases = [apply_alias(model_class, f) for f in self.field_names]
        put_if(
            json_schema,
            self.__condition.json_schema(model_class),
            {"not": required_non_null(aliases)},
        )
