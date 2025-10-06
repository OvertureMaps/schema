from enum import Enum
from typing import (
    Annotated,
    Any,
    Collection,
    Optional,
    Type,
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
    def _field_name(self):
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
):
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
                f"for `@scoped`, at least one scope must be allowed, but `allowed` is empty"
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

    new_fields = _make_scoped_fields(allowed, required)

    def decorator(cls):
        if not isinstance(cls, type):
            raise TypeError(f"`@scoped` can only be applied to classes")
        if not issubclass(cls, BaseModel):
            raise TypeError(
                f"`@scoped` target class must inherit from `{BaseModel.__module__}.{BaseModel.__name__}`"
            )
        base_model: Type[BaseModel] = cls
        conflict_fields = sorted(
            [f for f in base_model.model_fields.keys() if f in new_fields]
        )
        if conflict_fields:
            raise TypeError(
                f"can't apply `@scoped` to model {base_model.__name__}: the following model fields conflict with fields `@scoped` needs to create: {conflict_fields.join(', ')})"
            )
        return create_model(base_model.__name__, __base__=base_model, **new_fields)

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
) -> dict[str, tuple[Type, Any]]:
    scoped_fields: dict[str, tuple[Type, Any]] = {}

    if Scope.GEOMETRIC_POINT in allowed:
        _put_scoped_field(
            Scope.GEOMETRIC_POINT, required, "at", GeometricPoint, scoped_fields
        )

    if Scope.GEOMETRIC_RANGE in allowed:
        _put_scoped_field(
            Scope.GEOMETRIC_RANGE, required, "between", GeometricRange, scoped_fields
        )

    when_fields: dict[str, tuple[Type, Any]] = {}

    if Scope.HEADING in allowed:
        _put_scoped_field(Scope.HEADING, required, "heading", Heading, when_fields)

    # TODO: Put other when-wrapped scopes here.

    if when_fields:
        has_required = any(_is_required_type(pair[0]) for pair in when_fields.values())
        if has_required:
            scoped_fields["when"] = (_make_when(when_fields), ...)
        elif len(when_fields) == 1:
            ((field_name, field_type),) = when_fields.items()
            field_type = (_unpack_optional_inner_type(field_type[0]), ...)
            scoped_fields["when"] = _make_when({field_name: field_type})
        else:
            when = _make_when(when_fields)
            _require_at_least_one_field_set(when)
            scoped_fields["when"] = (Optional[when], None)

    return scoped_fields


def _put_scoped_field(
    scope: Scope,
    required: frozenset[Scope],
    field_name: str,
    field_type: Type,
    into: dict[str, tuple[Type, Any]],
):
    if scope in required:
        into[field_name] = (field_type, ...)
    else:
        into[field_name] = (Optional[field_type], None)


def _is_optional_type(t: Type) -> bool:
    return get_origin(t) is Union and type(None) in get_args(t)


def _is_required_type(t: Type) -> bool:
    return not _is_optional_type(t)


def _unpack_optional_inner_type(t: Type) -> Type:
    assert _is_optional_type(t)
    non_none_types = [arg for arg in get_args(t) if arg is not type(None)]
    assert len(non_none_types) == 1
    return non_none_types[0]


def _make_when(when_fields: dict[str, tuple[Any, Any]]):
    return create_model("When", **when_fields, __config__=ConfigDict(extra="forbid"))


def _require_at_least_one_field_set(
    model_type: Type[BaseModel], required_field_names: list[str]
):
    # Wrap the base Pydantic model validation with an added validation to ensure at least one of the
    # required fields is set.

    orig_validate = model_type.validate

    @classmethod
    def validate(cls, data, *args, **kwargs):
        model = orig_validate.__func__(cls, data, *args, **kwargs)
        actual_field_names = model.model_dump().keys()
        if not any(f in actual_field_names for f in required_field_names):
            field_names = ", ".join(
                f"`{field_name}`" for field_name in required_field_names.keys()
            )
            raise ValueError(f"at least one of {field_names} must be set")
        return model

    model_type.validate = validate

    # Set the Pydantic-generated JSON Schema to require at least one property to be set. It is safe
    # to do this, because we created `model_type`, `json_schema_extra` is a user field, and we`know
    # we didn't previously set it.

    assert model_type.model_config["json_schema_extra]"] is None
    model_type.model_config["json_schema_extra]"] = {"minProperties": 1}
