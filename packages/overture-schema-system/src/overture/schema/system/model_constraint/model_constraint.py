from collections.abc import Callable
from copy import deepcopy
from typing import Any, cast, final

from pydantic import (
    BaseModel,
    ConfigDict,
    create_model,
    model_validator,
)


class ModelConstraint:
    """
    Interface for constraints that apply to an entire Pydantic model, not just one field.

    Model constraints have two advantages over Pydantic model validators (`@model_validator`).
    First, the model constraints defined in this package work across the Overture schema system's
    code generation targets. This means that they validate the same data the same way in generated
    Java code as they do in Pydantic. Second, model constraints have integrated JSON Schema hooks
    to allow them to describe how the contraint should be applied at the JSON Schema level. The
    model constraints defined in this package all provide applicable JSON Schema enhancements.
    """

    def __init__(self, name: str | None = None):
        if name is None:
            name = type(self).__name__
        elif not isinstance(name, str):
            raise TypeError(
                f"`name` must be a str, but {name} is a `{type(name).__name__}`"
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
    def attach(self, model_class: type[BaseModel]) -> type[BaseModel]:
        """
        Attaches this constraint to a Pydantic model, returning a new version of the model.

        This is a final method and should not be overridden by subclasses.

        Example
        -------
        As well as simply attaching the contraint to a model, this function can be used to implement
        a reusable `@decorator`.

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
        ...     return FooConstraint().attach(model_class)
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
        )
        model_constraints = (*ModelConstraint.get_model_constraints(model_class), self)
        setattr(new_model_class, _MODEL_CONSTRAINT_PRIVATE_LIST_NAME, model_constraints)
        return new_model_class

    def validate_class(self, model_class: type[BaseModel]) -> None:
        """
        Validates that the constraint is appropriate for the model class.

        This method is called by the `get_decorator` method to ensure this constraint is applicable
        to the class being decorated with it.

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
        overwrite or alter the meaning of earlier changes made by other constraints. A
        `RuntimeError` should be raised if the constraint can't apply its changes because the config
        has already been put into a state that makes this impossible.

        This method will often be used to extend the JSON Schema by amending `json_schema_extra`,
        but other changes can also be made.

        Parameters
        ----------
        model_class : type
            Pydantic model class being validated
        config : ConfigDict
            Config dictionary to edit

        Raises
        ------
        RuntimeError
            If the config is in an unacceptable state
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
        validation code for those constraint.

        Example
        -------
        >>> from pydantic import BaseModel
        >>> from overture.schema.system.model_constraint import require_any_of
        >>> @require_any_of("foo", "bar")
        ... class MyModel(BaseModel):
        ...     foo: int | None
        ...     bar: str | None
        ...
        >>> [c.name for c in ModelConstraint.get_model_constraints(MyModel)]
        ['@require_any_of']
        """

        maybe_tuple = getattr(model_class, _MODEL_CONSTRAINT_PRIVATE_LIST_NAME, None)
        if not maybe_tuple:
            return ()
        elif not isinstance(maybe_tuple, tuple):
            raise TypeError(
                f"attribute {_MODEL_CONSTRAINT_PRIVATE_LIST_NAME} must be a tuple, but {maybe_tuple} is a `{type(maybe_tuple).__name__}`"
            )
        elif not all(isinstance(x, ModelConstraint) for x in maybe_tuple):
            raise TypeError(
                f"attribute {_MODEL_CONSTRAINT_PRIVATE_LIST_NAME} may only contain `{str.__name__}` values"
            )
        else:
            return maybe_tuple


_MODEL_CONSTRAINT_PRIVATE_LIST_NAME = "_ModelConstraint__private_list"


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
