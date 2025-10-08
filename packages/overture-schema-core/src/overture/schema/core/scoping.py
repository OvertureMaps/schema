# TODO: vic: Ensure the system model constraints have the following capabilities:
#
#       Require at least one field from a set, where the JSON Schema should be implemented like
#       this (but currently in this file it just uses minProperties):
#
#       ```json
#       {
#           "type": "object",
#           "anyOf": [
#               {"required": ["field1"]},
#               {"required": ["field2"]},
#               {"required": ["field3"]}
#           ],
#           "properties": {
#               "field1": {"type": "string"},
#               "field2": {"type": "string"},
#               "field3": {"type": "string"}
#           }
#       }
#       ```

from collections.abc import (
    Callable,
    Collection,
)
from enum import Enum
from typing import (
    Annotated,
    Any,
    Union,
    get_args,
    get_origin,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    create_model,
)

from overture.schema.system.model_constraint import RequireAnyOfConstraint


class Scope(Enum):
    GEOMETRIC_POINT = (1,)
    GEOMETRIC_RANGE = (2,)
    HEADING = (3,)
    TEMPORAL = (4,)
    TRAVEL_MODE = (5,)
    PURPOSE_OF_USE = (6,)
    RECOGNIZED_STATUS = (7,)
    SIDE = (8,)
    VEHICLE = (9,)

    @property
    def _field_name(self) -> str:
        match self:
            case Scope.GEOMETRIC_POINT:
                return "at"
            case Scope.GEOMETRIC_RANGE:
                return "between"
            case Scope.HEADING:
                return "heading"
            case Scope.TEMPORAL:
                return "during"
            case Scope.TRAVEL_MODE:
                return "mode"
            case Scope.PURPOSE_OF_USE:
                return "using"
            case Scope.RECOGNIZED_STATUS:
                return "recognized"
            case Scope.SIDE:
                return "side"
            case Scope.VEHICLE:
                return "vehicle"
            case _:
                raise RuntimeError(f"unexpected scope: {self}")


def scoped(
    allowed: Scope | Collection[Scope],
    required: Scope | Collection[Scope] | None = None,
) -> Callable:
    def collect_scopes(
        context: str, scopes: Scope | Collection[Scope]
    ) -> frozenset[Scope]:
        if isinstance(scopes, Scope):
            return frozenset({scopes})
        elif not isinstance(scopes, Collection):
            raise TypeError(
                f"for `@scoped`, {context} must be a `Scope` or a collection of `Scope` values but given value of type {type(scopes).__name__} is neither"
            )
        elif not all(isinstance(s, Scope) for s in scopes):
            raise TypeError(
                f"for `@scoped`, all members of the {context} collection must be a `Scope`, but at least one value is not"
            )
        elif not scopes:
            raise ValueError(
                "for `@scoped`, at least one scope must be allowed, but `allowed` is empty"
            )
        else:
            return frozenset(scopes)

    allowed = collect_scopes("allowed", allowed)

    if required is None:
        required = frozenset()
    else:
        required = collect_scopes("required", required)
        not_in_allowed = [s for s in required if s not in allowed]
        if not_in_allowed:
            raise ValueError(
                f"for `@scoped`, all required values must be allowed; but {not_in_allowed} are required but not allowed"
            )

    from typing import cast

    new_fields = cast(dict[str, Any], _make_scoped_fields(allowed, required))

    def decorator(model_class: type[BaseModel]) -> type[BaseModel]:
        if not isinstance(model_class, type):
            raise TypeError("`@scoped` can only be applied to classes")
        if not issubclass(model_class, BaseModel):
            raise TypeError(
                f"`@scoped` target class must inherit from `{BaseModel.__module__}.{BaseModel.__name__}`"
            )
        conflict_fields = sorted(
            [f for f in model_class.model_fields.keys() if f in new_fields]
        )
        if conflict_fields:
            raise TypeError(
                f"can't apply `@scoped` to model {model_class.__name__}: the following model fields conflict with fields `@scoped` needs to create: {', '.join(conflict_fields)})"
            )
        return create_model(
            model_class.__name__,
            __doc__=model_class.__doc__,
            __base__=model_class,
            __module__=model_class.__module__,
            **new_fields,
        )

    return decorator


# This is a value type and can be exported for reuse.
GeometricPoint = Annotated[float, Field(ge=0, le=1)]


# This is a value type and can be exported for reuse.
GeometricRange = Annotated[list[GeometricPoint], Field(min_length=2, max_length=2)]


# This is a value type and can be exported for reuse.
class Heading(str, Enum):
    FORWARD = "forward"
    BACKWARD = "backward"


def _make_scoped_fields(
    allowed: frozenset[Scope], required: frozenset[Scope]
) -> dict[str, tuple[type[Any], Any]]:
    scoped_fields: dict[str, tuple[type[Any], Any]] = {}

    if Scope.GEOMETRIC_POINT in allowed:
        _put_scoped_field(
            Scope.GEOMETRIC_POINT, required, "at", GeometricPoint, scoped_fields
        )

    if Scope.GEOMETRIC_RANGE in allowed:
        _put_scoped_field(
            Scope.GEOMETRIC_RANGE, required, "between", GeometricRange, scoped_fields
        )

    when_fields: dict[str, tuple[type[Any], Any]] = {}

    if Scope.HEADING in allowed:
        _put_scoped_field(Scope.HEADING, required, "heading", Heading, when_fields)

    # TODO: Put other when-wrapped scopes here.

    if when_fields:
        has_required = any(_is_required_type(pair[0]) for pair in when_fields.values())
        if has_required:
            scoped_fields["when"] = (_make_when(when_fields), ...)  # type: ignore
        elif len(when_fields) == 1:
            ((field_name, field_type),) = when_fields.items()
            field_type = (_unpack_optional_inner_type(field_type[0]), ...)
            scoped_fields["when"] = _make_when({field_name: field_type})  # type: ignore
        else:
            when = _make_when(when_fields)
            when = RequireAnyOfConstraint(*when_fields.keys()).attach(when)
            scoped_fields["when"] = (when.__class__ | None, None)  #  type: ignore

    return scoped_fields


def _put_scoped_field(
    scope: Scope,
    required: frozenset[Scope],
    field_name: str,
    field_type: type[Any],
    into: dict[str, tuple[type[Any], Any]],
) -> None:
    if scope in required:
        into[field_name] = (field_type, ...)
    else:
        into[field_name] = (field_type | None, None)  # type: ignore


def _is_optional_type(t: type[Any]) -> bool:
    return get_origin(t) is Union and type(None) in get_args(t)


def _is_required_type(t: type[Any]) -> bool:
    return not _is_optional_type(t)


def _unpack_optional_inner_type(t: type[Any]) -> type[Any]:
    assert _is_optional_type(t)
    non_none_types = [
        arg for arg in get_args(t) if isinstance(arg, type) and arg is not type(None)
    ]
    assert len(non_none_types) == 1
    return non_none_types[0]


def _make_when(when_fields: dict[str, tuple[Any, Any]]) -> type[BaseModel]:
    return create_model("When", __config__=ConfigDict(extra="forbid"), **when_fields)  # type: ignore
