"""
Require at least one condition in a group of conditions to evaluate to `True`.
"""

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict
from pydantic.json_schema import JsonDict
from typing_extensions import override

from .._json_schema import get_static_json_schema_extra, put_any_of
from .model_constraint import Condition, FieldEqCondition, ModelConstraint, apply_alias


def require_any_true(
    *conditions: Condition,
) -> Callable[[type[BaseModel]], type[BaseModel]]:
    """
    Decorate a Pydantic model class with a constraint requiring at least one condition in a group
    of conditions to evaluate to `True`.

    This function is the decorator version of the `RequireAnyTrueConstraint` class.

    Parameters
    ----------
    *conditions : Condition
        Varargs list of one or more conditions.

    Returns
    -------
    Callable
        Decorator factory

    Example
    -------
    >>> from pydantic import BaseModel, ValidationError
    >>> from overture.schema.system.model_constraint import FieldEqCondition
    >>>
    >>> @require_any_true(
    ...     FieldEqCondition("foo", True),
    ...     FieldEqCondition("bar", True),
    ... )
    ... class MyModel(BaseModel):
    ...     foo: bool | None = None
    ...     bar: bool = True
    ...
    >>> MyModel()                       # validates OK
    MyModel(foo=None, bar=True)
    >>> MyModel(foo=True, bar=True)     # validates OK
    MyModel(foo=True, bar=True)
    >>> MyModel(foo=True, bar=False)    # validates OK
    MyModel(foo=True, bar=False)
    >>>
    >>> try:
    ...     MyModel(bar=False)
    ... except ValidationError as e:
    ...    assert (
    ...        "at least one field from the condition group [foo, bar] must be True, "
    ...        "but none is True"
    ...    ) in str(e)
    ...    print("Validation failed")
    Validation failed
    """
    model_constraint = RequireAnyTrueConstraint._create_internal(
        f"@{require_any_true.__name__}", *conditions
    )

    return model_constraint.decorate


class RequireAnyTrueConstraint(ModelConstraint):
    """
    Class implementing the `require_any_true` decorator, which can also be used standalone.
    """

    def __init__(self, *conditions: Condition):
        super().__init__(None)
        self.__set_conditions(conditions)

    @classmethod
    def _create_internal(
        cls, name: str, *conditions: Condition
    ) -> "RequireAnyTrueConstraint":
        instance = cls.__new__(cls)
        super(RequireAnyTrueConstraint, instance).__init__(name)
        instance.__set_conditions(conditions)
        return instance

    @property
    def conditions(self) -> tuple[Condition, ...]:
        return self.__conditions

    def __set_conditions(self, conditions: tuple[Condition, ...]) -> None:
        if len(conditions) == 0:
            raise ValueError(
                "`conditions` must contain at least one item, but it is empty"
            )
        invalid_conditions = [c for c in conditions if not isinstance(c, Condition)]
        if invalid_conditions:
            raise TypeError(
                f"`conditions` must contain only `{Condition.__name__}` values, but {repr(invalid_conditions[0])} has type `{type(invalid_conditions[0]).__name__}` (`{self.name}`)"
            )
        self.__conditions = conditions

    @staticmethod
    def __true_field_name(condition: Condition) -> str | None:
        if (
            isinstance(condition, FieldEqCondition)
            and isinstance(condition.field_name, str)
            and condition.value is True
        ):
            return condition.field_name
        return None

    def __validation_error_message(self) -> str:
        true_field_names = [
            field_name
            for condition in self.conditions
            if (field_name := self.__true_field_name(condition)) is not None
        ]
        if len(true_field_names) == len(self.conditions):
            return (
                "at least one field from the condition group "
                f"[{', '.join(true_field_names)}] must be True, but none is True"
            )
        return (
            "at least one condition from the condition group "
            f"[{', '.join(repr(condition) for condition in self.conditions)}] "
            "must be True, but none is True"
        )

    @staticmethod
    def __condition_json_schema(
        model_class: type[BaseModel], condition: Condition
    ) -> JsonDict:
        json_schema = condition.json_schema(model_class)
        if isinstance(condition, FieldEqCondition):
            alias = apply_alias(model_class, condition.field_name)
            return {"required": [alias], **json_schema}
        return json_schema

    @override
    def validate_class(self, model_class: type[BaseModel]) -> None:
        super().validate_class(model_class)

        for condition in self.conditions:
            condition.validate_class(model_class)

    @override
    def validate_instance(self, model_instance: BaseModel) -> None:
        super().validate_instance(model_instance)

        if any(condition.eval(model_instance) for condition in self.conditions):
            return

        raise ValueError(f"{self.__validation_error_message()} (`{self.name}`)")

    @override
    def edit_config(self, model_class: type[BaseModel], config: ConfigDict) -> None:
        super().edit_config(model_class, config)

        json_schema = get_static_json_schema_extra(config)
        put_any_of(
            json_schema,
            [self.__condition_json_schema(model_class, c) for c in self.conditions],
        )
