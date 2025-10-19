from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, cast, final

from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
)
from pydantic.json_schema import JsonDict, to_jsonable_python
from typing_extensions import override

from ..create_model import create_model
from ..metadata import Key, Metadata


class ModelConstraint:
    """
    Interface for constraints that apply to an entire Pydantic model, not just one field.

    Model constraints have two advantages over Pydantic model validators (`@model_validator`).
    First, the model constraints defined in this package work across the Overture schema system's
    code generation targets. This means that they validate the same data the same way in generated
    Java code as they do in Pydantic. Second, model constraints have integrated JSON Schema hooks
    to allow them to describe how the constraint should be applied at the JSON Schema level. The
    model constraints defined in this package all provide applicable JSON Schema enhancements.

    Parameters
    ----------
    name : str | None
        Friendly name of the constraint instance for error messaging purposes. This should be set
        to `None` if a constraint class was instantiated directly, or to the decorator name if the
        constraint was instantiated via decorator function.
    """

    def __init__(self, name: str | None = None):
        if name is None:
            name = type(self).__name__
        elif not isinstance(name, str):
            raise TypeError(
                f"`name` must be a `str`, but {name} has type `{type(name).__name__}`"
            )
        self.__name = name

    def __validate_instance(self, model_instance: BaseModel) -> BaseModel:
        self.validate_instance(model_instance)
        return model_instance

    @property
    def name(self) -> str:
        """Returns the name of the constraint, e.g. "FooConstraint" or "@foo"."""
        return self.__name

    @final
    def decorate(self, model_class: type[BaseModel]) -> type[BaseModel]:
        """
        Decorates a Pydantic model with this constraint, returning a new version of the model that
        has this constraint applied to it.

        This is a final method and should not be overridden by subclasses.

        Parameters
        ----------
        model_class : type[BaseModel]
            Pydantic model to decorate. It is not decorated in-place, rather a new version of the
            model class is returned with this constraint attached to it.

        Returns
        -------
        type[BaseModel]
            New version of `model_class` with this constraint applied to it

        Example
        -------
        As well as simply attaching the constraint to a model, this function can be used to
        implement a reusable `@decorator`.

        >>> from pydantic import BaseModel, ValidationError
        >>>
        >>> # Define a simple model constraint
        >>> class FooConstraint(ModelConstraint):
        ...     def validate_instance(self, model_instance: BaseModel) -> None:
        ...         if getattr(model_instance, "foo", None) != "bar":
        ...             raise ValueError('the `foo` field must equal "bar"')
        ...
        >>> # Define a decorator.
        >>> def foo(model_class: type[BaseModel]) -> type[BaseModel]:
        ...     return FooConstraint().decorate(model_class)
        ...
        >>> # Apply the decorator.
        >>> @foo
        ... class FooModel(BaseModel):
        ...     foo: str = "baz"
        ...
        >>> # Create an instance of the model, triggering the validation.
        >>> try:
        ...     foo = FooModel()
        ... except ValidationError as e:
        ...    assert 'the `foo` field must equal "bar"' in str(e)
        ...    print("Validation failed")
        Validation failed
        """

        if not isinstance(model_class, type):
            raise TypeError(f"`{self.name}` can only be applied to classes")
        if not issubclass(model_class, BaseModel):
            raise TypeError(
                f"`{self.name}` target class must inherit from `{BaseModel.__module__}.{BaseModel.__name__}`, but `{model_class.__name__}` does not"
            )
        self.validate_class(model_class)
        config = deepcopy(model_class.model_config)
        self.edit_config(model_class, config)
        metadata = Metadata.retrieve_from(model_class, Metadata()).copy()  # type: ignore[union-attr]
        model_constraints = (*ModelConstraint.get_model_constraints(model_class), self)
        metadata[_MODEL_CONSTRAINT_KEY] = model_constraints
        new_model_class = create_model(
            model_class.__name__,
            __config__=config,
            __doc__=model_class.__doc__,
            __base__=model_class,
            __module__=model_class.__module__,
            __validators__={
                self.name: cast(
                    Callable[..., Any],
                    model_validator(mode="after")(self.__validate_instance),
                )
            },
            __metadata__=metadata,
        )
        return new_model_class

    def validate_class(self, model_class: type[BaseModel]) -> None:
        """
        Validates that the constraint is appropriate for the model class.

        This method is called by the `decorate` method to ensure this constraint is applicable to
        the class being decorated with it.

        Parameters
        ----------
        model_class : type
            Pydantic model class being validated

        Raises
        ------
        TypeError
            If the model class is invalid.
        """
        pass

    def validate_instance(self, model_instance: BaseModel) -> None:
        """
        Validates the model instance against this constraint.

        Parameters
        ----------
        model_instance : BaseModel
            Pydantic model instance being validated

        Raises
        ------
        ValueError
            If the model is invalid
        """
        pass  # noqa: B027

    def edit_config(self, model_class: type[BaseModel], config: ConfigDict) -> None:
        """
        Makes any changes to an existing config dictionary needed to reflect this constraint's
        validations.

        The existing config dictionary may already have been edited by other model constraints
        applied earlier in the process. Implementations must take care not to make changes that
        overwrite or alter the meaning of earlier changes made by other constraints.

        The `config` should never be in a state that makes applying this constraint impossible,
        because that state should already have been detected by `validate_class`.

        This method will often be used to extend the JSON Schema by amending `json_schema_extra`,
        but other changes can also be made.

        Parameters
        ----------
        model_class : type
            Pydantic model class being validated
        config : ConfigDict
            Config dictionary to edit
        """
        pass  # noqa: B027

    @final
    @classmethod
    def get_model_constraints(
        cls: type["ModelConstraint"], model_class: type[BaseModel]
    ) -> tuple["ModelConstraint", ...]:
        """
        Returns the model constraints that have been applied to the given Pydantic model class.

        This is a final method and should not be overridden by subclasses.

        The purpose of this method is to support code generation: code generators need to know which
        system-level constraints have been applied to the model in order to generate target-specific
        validation code for those constraints.

        Example
        -------
        >>> from pydantic import BaseModel
        >>> from overture.schema.system.model_constraint import require_any_of
        >>> @require_any_of("foo", "bar")
        ... class MyModel(BaseModel):
        ...     foo: int | None = None
        ...     bar: str | None = None
        ...
        >>> [c.name for c in ModelConstraint.get_model_constraints(MyModel)]
        ['@require_any_of']
        """
        return cast(
            tuple[ModelConstraint, ...],
            Metadata.retrieve_from(model_class, Metadata()).get(  # type: ignore[union-attr]
                _MODEL_CONSTRAINT_KEY, ()
            ),
        )


# Private: Used to construct the opaque metadata key.
class _ModelKeyClass:
    pass


# Private: Opaque metadata key.
_MODEL_CONSTRAINT_KEY = Key(
    f"{ModelConstraint.__module__}.{ModelConstraint.__qualname__}", _ModelKeyClass
)


class FieldGroupConstraint(ModelConstraint):
    """
    A model constraint that constrains a group of fields in the Pydantic model it decorates.

    Use this constraint as a base class when developing model constraints that affect lists of
    fields. It takes care of validating the list of field names at construction time (checking for
    duplicates, minimum count, and proper types). It then validates the model class being decorated
    (to ensure it contains all the expected fields). Subclasses may want to add additional
    validation, for example to check the types of the constrained fields.

    Use `OptionalFieldGroupConstraint` rather than `FieldGroupConstraint` if it is important that
    the fields in the group are all optional.

    Parameters
    ----------
    name : str | None
        Friendly name of the constraint instance for error messaging purposes. This should be set
        to `None` if a constraint class was instantiated directly, or to the decorator name if the
        constraint was instantiated via decorator function.
    field_names : tuple[str, ...]
        Names of at least two model fields affected by the constraint

    Raises
    ------
    ValueError
        If `field_names` has fewer than two names in it or contains duplicates
    TypeError
        If `field_names` is not a `tuple` of `str`
    """

    def __init__(self, name: str | None, field_names: tuple[str, ...]):
        super().__init__(name)
        self.__set_field_names(field_names)

    @property
    def field_names(self) -> tuple[str, ...]:
        return self.__field_names

    def __set_field_names(self, field_names: tuple[str, ...]) -> None:
        if not isinstance(field_names, tuple):
            raise TypeError(
                f"`field_names` must be a `tuple`, but {field_names} has type `{type(field_names).__name__}`"
            )
        elif len(field_names) == 0:
            raise ValueError("`field_names` cannot be empty, but it is")
        elif not all(isinstance(s, str) for s in field_names):
            raise TypeError(
                f"`field_names` must contain only `str` values, but {field_names} contains at least one non-`str` value"
            )
        dupes = [s for s, count in Counter(field_names).items() if count > 1]
        if dupes:
            raise ValueError(
                f"`field_names` must not contain duplicates, but {field_names} contains at least one repeated value"
            )
        self.__field_names = field_names

    @override
    def validate_class(self, model_class: type[BaseModel]) -> None:
        missing_fields = [
            f for f in self.field_names if f not in model_class.model_fields
        ]
        if missing_fields:
            raise TypeError(
                f"`{self.name}` specifies one or more fields that are not in the model class `{model_class.__name__}`: {', '.join(missing_fields)}"
            )


class OptionalFieldGroupConstraint(FieldGroupConstraint):
    """
    A model constraint that constrains a group of *optional* fields in the Pydantic model it
    decorates.

    Inherits all field validation behavior from FieldGroupConstraint and adds an additional check
    that all specified fields are optional.

    Parameters
    ----------
    name : str | None
        Friendly name of the constraint instance for error messaging purposes. This should be set
        to `None` if a constraint class was instantiated directly, or to the decorator name if the
        constraint was instantiated via decorator function.
    field_names : tuple[str, ...]
        Names of at least two model fields affected by the constraint
    """

    def __init__(self, name: str | None, field_names: tuple[str, ...]):
        super().__init__(name, field_names)

    @override
    def validate_class(self, model_class: type[BaseModel]) -> None:
        super().validate_class(model_class)

        required_fields = [
            f for f in self.field_names if model_class.model_fields[f].is_required()
        ]
        if required_fields:
            raise TypeError(
                f"`{self.name}` expects all the fields to be optional, but at least one is required in the model class `{model_class.__name__}`: {', '.join(required_fields)}"
            )


class Condition(ABC):
    @final
    def __invert__(self) -> "Condition":
        return self.negate()

    @abstractmethod
    def validate_class(self, model_class: type[BaseModel]) -> None:
        """
        Validates that the constraint is appropriate for the model class.

        Parameters
        ----------
        model_class : type[BaseModel]
            Pydantic model class being validated

        Raises
        ------
        TypeError
            If the model class is invalid.
        """
        raise NotImplementedError()

    @abstractmethod
    def eval(self, model_instance: BaseModel) -> bool:
        """
        Evaluates the condition against a Pydantic model instance.

        This method must only be called on model instances where `validate_class` does not raise
        an exception on the instance's model class.

        Parameters
        ----------
        model_instance : BaseModel
            Model to evaluate the condition against

        Returns
        -------
        bool
            Whether the condition evaluated `true` or not
        """
        raise NotImplementedError()

    def negate(self) -> "Condition":
        """
        Returns a condition that represents the logical negation of this condition.

        Examples
        --------
        >>> FieldEqCondition('foo', 'bar').negate()
        Not(FieldEqCondition(field_name='foo', value='bar'))

        The `~` operator can be used as shorthand.

        >>> ~FieldEqCondition('foo', 'bar')
        Not(FieldEqCondition(field_name='foo', value='bar'))
        """
        return Not(self)

    def json_schema(self, model_class: type[BaseModel]) -> JsonDict:
        """
        Returns a JSON Schema that models the condition value with respect to a Pydantic model
        class.

        This method must only be called on model classes for which `validate_class` does not raise
        an exception.

        Parameters
        ----------
        model_class : type[BaseModel]
            Pydantic model class being this condition is being evaluated against

        Returns
        -------
        JsonDict
            JSON Schema for this condition with respect to `model_class`
        """
        raise NotImplementedError()


@dataclass(frozen=True, slots=True)
class Not(Condition):
    inner: Condition

    def __repr__(self) -> str:
        return f"Not({repr(self.inner)})"

    @override
    def validate_class(self, model_class: type[BaseModel]) -> None:
        return self.inner.validate_class(model_class)

    @override
    def eval(self, model_instance: BaseModel) -> bool:
        return not self.inner.eval(model_instance)

    @override
    def negate(self) -> Condition:
        return self.inner

    @override
    def json_schema(self, model_class: type[BaseModel]) -> JsonDict:
        return {"not": self.inner.json_schema(model_class)}


@dataclass(frozen=True, slots=True)
class __FieldCondition(Condition):
    field_name: str
    value: object

    def __post_init__(self) -> None:
        if not isinstance(self.field_name, str):
            raise TypeError(
                f"`field_name` must be a `str`, but {repr(self.field_name)} is a {type(self.field_name).__name__}"
            )

    @override
    def validate_class(self, model_class: type[BaseModel]) -> None:
        """
        Validates that the constraint is appropriate for the model class.

        Parameters
        ----------
        model_class : type[BaseModel]
            Pydantic model class being validated

        Raises
        ------
        TypeError
            If the model class is invalid.
        """
        if self.field_name not in model_class.model_fields:
            raise TypeError(
                f"model class `{model_class.__name__}` must contain the condition field {repr(self.field_name)}, but it does not"
            )


class FieldEqCondition(__FieldCondition):
    """
    Represents a condition that is true when a Pydantic field is set to a specific value.

    Attributes
    ----------
    field_name : str
        Name of the model field to check as part of the condition
    value : object
        Value the field must have for the condition to be true

    Examples
    --------
    >>> from pydantic import BaseModel
    >>>
    >>> class MyModel(BaseModel):
    ...    foo: str
    ...
    >>> condition = FieldEqCondition('foo', 'baz')
    >>> condition.validate_class(MyModel)
    >>>
    >>> condition.eval(MyModel(foo='bar'))
    False
    >>> condition.eval(MyModel(foo='baz'))
    True
    >>> condition.negate().eval(MyModel(foo='baz'))
    False
    >>> (~condition).eval(MyModel(foo='bar'))           # ~ is shorthand for `.negate()`
    True
    """

    @override
    def eval(self, model_instance: BaseModel) -> bool:
        actual_value = getattr(model_instance, self.field_name)
        return bool(actual_value == self.value)

    @override
    def json_schema(self, model_class: type[BaseModel]) -> JsonDict:
        property_name = apply_alias(model_class, self.field_name)
        return {
            "properties": {property_name: {"const": to_jsonable_python(self.value)}}
        }


def apply_alias(model_class: type[BaseModel], field_name: str) -> str:
    """
    Resolve a field name to its alias if it has one.

    Parameters
    ----------
    model_class : type
        Base model class that contains the field
    field_name : str
        Field name

    Returns
    -------
    str
        The alias, if the field has one, or the field name otherwise.

    Raises
    ------
    ValueError
        If the base model doesn't have a field with the given name.

    Example
    -------
    >>> from pydantic import BaseModel, Field
    >>> class Foo(BaseModel):
    ...     bar: str
    ...     baz: str = Field(alias = "qux")
    ...
    >>> print(f"applied alias for bar ➜ {apply_alias(Foo, 'bar')}")
    applied alias for bar ➜ bar
    >>> print(f"applied alias for baz ➜ {apply_alias(Foo, 'baz')}")
    applied alias for baz ➜ qux
    """
    try:
        field_info = model_class.model_fields[field_name]
    except KeyError as e:
        raise ValueError(
            f"model class `{model_class.__name__}` does not contain a field named {repr(field_name)}"
        ) from e
    if field_info.alias is not None:
        return field_info.alias
    return field_name
