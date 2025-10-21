from collections.abc import (
    Callable,
    Iterable,
)
from enum import Enum
from typing import (
    Annotated,
    Any,
    TypedDict,
    cast,
    get_origin,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from overture.schema.core.scoping.heading import Heading
from overture.schema.system import create_model
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import (
    NoExtraFieldsConstraint,
    RequireAnyOfConstraint,
)

from .lr import LinearlyReferencedPosition, LinearlyReferencedRange
from .opening_hours import OpeningHours
from .purpose_of_use import PurposeOfUse
from .recognized_status import RecognizedStatus
from .side import Side
from .travel_mode import TravelMode
from .vehicle import VehicleSelector


class Scope(str, Enum):
    """
    A scope type supported by the `scoped` decorator.
    """

    GEOMETRIC_POSITION = "geometric_position"
    """
    Geometric position scope. (Point linear referencing.)

    This scope type adds an `at` field of type `LinearlyReferencedPosition` to the decorated model.
    Use it to build models to capture linearly-referenced point events.
    """

    GEOMETRIC_RANGE = "geometric_range"
    """
    Geometric range scope. (Range linear referencing.)

    This scope type adds a `between` field of type `LinearlyReferencedRange` to the decorated model.
    Use it to build models to capture linearly-referenced range events.
    """

    HEADING = "heading"
    """
    Heading scope. (Direction of facing or travel along a path.)

    This scope adds a `when.heading` field of type `Heading` onto the decorated model. Use it to
    build models that apply only when facing or travelling in a certain direction along a path.

    In order to add `when.heading`, this scope will place it into a containing `when` field in the
    model it decorates. The type of the `when` field will be a new model class named `When` that
    will be added as a nested class of the decorated model.  Consequently, the decorated model must
    not aready have a `when` field or a nested class named `When`.
    """

    TEMPORAL = "temporal"
    """
    Temporal scope. (Applying only at particular times.)

    This scope adds a `when.during` field of type `OpeningHours` to the decorated model. Use it to
    build models that apply only during designated times rather than all the time.

    In order to add `when.during`, this scope will place it into a containing `when` field in the
    model it decorates. The type of the `when` field will be a new model class named `When` that
    will be added as a nested class of the decorated model.  Consequently, the decorated model must
    not aready have a `when` field or a nested class named `When`.
    """

    TRAVEL_MODE = "travel_mode"
    """
    Travel mode scope. (Applying only when travelling a particular way, such as on foot or by car.)

    This scope adds a `when.mode` field of type `list[TravelMode]` to the decorated model. Use it to
    build models that apply only to actors who are traveling using one of the listed travel modes.

    In order to add `when.mode`, this scope will add a containing `when` field to the model it
    decorates, and then add the `mode` field to the `when` field. Consequently, the decorated
    model must not already have a `when` field.
    """

    PURPOSE_OF_USE = "purpose_of_use"
    """
    Purpose of use scope. (Applying only when using a something for a specific purpose, such as to
    deliver goods, or be a customer.)

    This scope adds a `when.using` field of type `list[PurposeOfUse]` to the decorated model. Use it
    to build models that apply only to actors who are doing something for an approved reason.

    In order to add `when.using`, this scope will place it into a containing `when` field in the
    model it decorates. The type of the `when` field will be a new model class named `When` that
    will be added as a nested class of the decorated model.  Consequently, the decorated model must
    not aready have a `when` field or a nested class named `When`.
    """

    RECOGNIZED_STATUS = "recognized_status"
    """
    Recognized status scope. (Applying only to persons who have an officially recognized status,
    such as student or employee.)

    This scope adds a `when.recognized` field of type `list[RecognizedStatus]` to the decorated
    model. Use it to build models that apply only to actors who have an approved status.

    In order to add `when.recognized`, this scope will place it into a containing `when` field in
    the model it decorates. The type of the `when` field will be a new model class named `When` that
    will be added as a nested class of the decorated model.  Consequently, the decorated model must
    not aready have a `when` field or a nested class named `When`.
    """

    SIDE = "side"
    """
    Side scope. (Applying to the left or right side of something, but not both.)

    This scope adds a `side` field of type `Side` to the decorated mode. Use it to build models that
    apply exclusively to the left or right side of something.

    Note that for linear features such as roads, the side is based on the geometry orientation: to
    an actor facing in the direction of the geometry's orientation, the left side appears on the
    actor's left and the right side on the actor's right.
    """

    VEHICLE = "vehicle"
    """
    Vehicle scope. (Applying to vehicles with specific characteristics.)

    This scope adds a `when.vehicle` field of type of type `list[VehicleRule]` to the decorated
    model. Use it to build models that apply only to certain vehicles based on the listed vehicle
    characteristics.

    In order to add `when.vehicle`, this scope will place it into a containing `when` field in the
    model it decorates. The type of the `when` field will be a new model class named `When` that
    will be added as a nested class of the decorated model.  Consequently, the decorated model must
    not aready have a `when` field or a nested class named `When`.
    """

    def _field(self, parent: str, required: bool) -> object:
        class FieldArgs(TypedDict):
            default: object
            description: str
            min_length: int

        field_args = FieldArgs(description=self._field_description(parent))  # type: ignore[typeddict-item]

        base_type: type[Any] = self._field_type
        final_type: Any = self._field_type

        if not required:
            final_type = base_type | None
            field_args["default"] = None

        annotations: list[object] = []
        is_list_type: bool = (
            isinstance(base_type, list) or get_origin(base_type) is list
        )
        if is_list_type:
            field_args["min_length"] = 1

        annotations.append(Field(**field_args))

        if is_list_type:
            annotations.append(UniqueItemsConstraint())

        args = (final_type, *annotations)

        return Annotated[args]

    @property
    def _field_name(self) -> str:
        match self:
            case Scope.GEOMETRIC_POSITION:
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
                raise self._unexpected_scope()

    @property
    def _field_type(self) -> type[Any]:
        match self:
            case Scope.GEOMETRIC_POSITION:
                return LinearlyReferencedPosition
            case Scope.GEOMETRIC_RANGE:
                return LinearlyReferencedRange
            case Scope.HEADING:
                return Heading
            case Scope.TEMPORAL:
                return OpeningHours
            case Scope.TRAVEL_MODE:
                return list[TravelMode]
            case Scope.PURPOSE_OF_USE:
                return list[PurposeOfUse]
            case Scope.RECOGNIZED_STATUS:
                return list[RecognizedStatus]
            case Scope.SIDE:
                return Side
            case Scope.VEHICLE:
                return list[VehicleSelector]
            case _:
                raise self._unexpected_scope()

    def _field_description(self, parent: str) -> str:
        match self:
            case Scope.GEOMETRIC_POSITION:
                return (
                    "The linearly-referenced position on the geometry, "
                    "specified as a percentage displacement from the start "
                    f"of the geometry, that the containing {parent} applies to."
                )
            case Scope.GEOMETRIC_RANGE:
                return (
                    "The linearly-referenced sub-segment of the geometry, "
                    "specified as a range (pair) of percentage displacements "
                    "from the start of the geometry, that the containing "
                    f"{parent} applies to."
                )
            case Scope.HEADING:
                return (
                    "The heading, either forward or backward, that the "
                    f"containing {parent} applies to."
                )
            case Scope.TEMPORAL:
                return (
                    "The recurring time span, in the OpenStreetMap opening "
                    f"hours format, that the containing {parent} applies to. "
                    "For the OSM opening hours specification, see "
                    "https://wiki.openstreetmap.org/wiki/Key:opening_hours/specification."
                )
            case Scope.TRAVEL_MODE:
                return (
                    "A list of one or more travel modes, such as car, truck, "
                    f"or foot, that the containing {parent} applies to."
                )
            case Scope.PURPOSE_OF_USE:
                return (
                    "A list of one or more usage purposes, such as delivery or "
                    "arrival at final destination, that the containing "
                    f"{parent} applies to."
                )
            case Scope.RECOGNIZED_STATUS:
                return (
                    "A list of one or more recognized status values, such as "
                    f"employee or student, that the containing {parent} "
                    "applies to."
                )
            case Scope.SIDE:
                return (
                    "The side, either left or right, that the containing "
                    f"{parent} applies to."
                )
            case Scope.VEHICLE:
                return (
                    "A list of one or more vehicle parameters that limit the "
                    f"vehicles the containing {parent} applies to."
                )
            case _:
                raise self._unexpected_scope()

    def _unexpected_scope(self) -> RuntimeError:
        return RuntimeError(f"unexpected scope: {self}")

    @staticmethod
    def _top_level_scopes() -> tuple["Scope", ...]:
        return (Scope.GEOMETRIC_POSITION, Scope.GEOMETRIC_RANGE, Scope.SIDE)

    @staticmethod
    def _when_scopes() -> tuple["Scope", ...]:
        return (
            Scope.HEADING,
            Scope.TEMPORAL,
            Scope.TRAVEL_MODE,
            Scope.PURPOSE_OF_USE,
            Scope.RECOGNIZED_STATUS,
            Scope.VEHICLE,
        )


def scoped(
    *optional: Scope,
    required: Scope | Iterable[Scope] | None = None,
) -> Callable:
    """
    Returns a decorator to decorate a Pydantic model class with one or more scoping attributes.

    At least one `Scope` must be given either in `optional` or `required` or both. A scope may be
    optional or required, but not both.

    Parameters
    ----------
    *optional : Scope
        Scopes that are allowed, but not required, on the decorated Pydantic model.
    required : Scope | Iterable[Scope] | None
        Scopes that are required on the decorated Pydantic model.

    Returns
    -------
    Callable
        Decorator

    Examples
    --------
    >>> from pydantic import BaseModel
    >>> @scoped(Scope.GEOMETRIC_RANGE, required=Scope.HEADING)
    ... class MyModel(BaseModel):
    ...     pass
    >>> MyModel(between=[0.25, 0.75], when=MyModel.When(heading=Heading.FORWARD))
    MyModel(between=[0.25, 0.75], when=MyModel.When(heading=<Heading.FORWARD: 'forward'>))
    """

    def collect_scopes(
        context: str, scopes: Scope | Iterable[Scope]
    ) -> frozenset[Scope]:
        if isinstance(scopes, Scope):
            return frozenset({scopes})
        elif not isinstance(scopes, Iterable):
            raise TypeError(
                f"for `@scoped`, {context} must be a `Scope`, or an `Iterable[Scope]` (such as a `list` or `tuple`), but the given value of type {type(scopes).__name__} is none of these"
            )
        elif not all(isinstance(s, Scope) for s in scopes):
            raise TypeError(
                f"for `@scoped`, all elements of `{context}` must be a `Scope`, but at least one value in {repr(scopes)} is not"
            )
        else:
            return frozenset(cast(Iterable[Scope], scopes))

    optional_set = collect_scopes("optional", optional)
    required_set = collect_scopes("required", required) if required else frozenset()

    if not optional_set and not required_set:
        raise ValueError(
            "for `@scoped`, at least one scope must be specified, but both `optional` and "
            "`required` are empty"
        )
    elif optional_set & required_set:
        raise ValueError(
            "for `@scoped`, `required` must not repeat any values from `optional`, but it has the "
            "following repeat values: "
            f"{', '.join(sorted(optional_set & required_set))}"
        )

    def decorator(model_class: type[BaseModel]) -> type[BaseModel]:
        if not isinstance(model_class, type):
            raise TypeError("`@scoped` can only be applied to classes")
        if not issubclass(model_class, BaseModel):
            raise TypeError(
                f"`@scoped` target class must inherit from `{BaseModel.__module__}.{BaseModel.__name__}`"
            )
        (new_fields, when_class) = _make_scoped_fields(
            model_class, optional_set | required_set, required_set
        )
        conflict_fields = sorted(
            [f for f in model_class.model_fields.keys() if f in new_fields]
        )
        if conflict_fields:
            raise TypeError(
                f"can't apply `@scoped` to model `{model_class.__name__}`: the following model fields conflict with fields `@scoped` needs to create: {', '.join(conflict_fields)})"
            )
        scoped_class = create_model(
            model_class.__name__,
            __doc__=model_class.__doc__,
            __base__=model_class,
            __module__=model_class.__module__,
            **new_fields,
        )
        if when_class:
            if hasattr(scoped_class, "When"):
                raise TypeError(
                    f"can't apply `@scoped` to model class `{scoped_class.__name__}`: there is already a class attribute `When` (of type `{type(scoped_class.When).__name__}`)"
                )
            scoped_class.When = when_class  # type: ignore[attr-defined]

        return scoped_class

    return decorator


def _make_scoped_fields(
    model_class: type[BaseModel],
    allowed: frozenset[Scope],
    required: frozenset[Scope],
) -> tuple[dict[str, Any], type[BaseModel] | None]:
    parent: str = _model_name(model_class)

    scoped_fields: dict[str, Any] = {
        s._field_name: s._field(parent, s in required)
        for s in Scope._top_level_scopes()
        if s in allowed
    }

    when_class: type[BaseModel] | None = None
    when_scopes = [s for s in Scope._when_scopes() if s in allowed]

    if when_scopes:
        has_required = any(s in required for s in when_scopes)
        description = _describe_when(parent, len(scoped_fields) > 1, when_scopes)

        if not has_required and len(when_scopes) == 1:
            # If there is exactly one optional `when` field, make `when` optional but the field
            # within `when` required.
            [s] = when_scopes
            when_class = _make_when_class(
                model_class, {s._field_name: s._field(parent, True)}, description
            )
            scoped_fields["when"] = (
                when_class | None,
                Field(default=None, description=description),
            )
        else:
            when_fields: dict[str, Any] = {
                s._field_name: s._field(parent, s in required) for s in when_scopes
            }
            when_class = _make_when_class(model_class, when_fields, description)
            if has_required:
                # If any `when` field is required, `when` is itself required.
                scoped_fields["when"] = (when_class, Field(description=description))
            else:
                # If the `when` has no required fields but contains multiple optional fields, it is
                # optional, but if present we require that at least one of its fields be set.
                when_class = RequireAnyOfConstraint(*when_fields.keys()).decorate(
                    when_class
                )
                scoped_fields["when"] = (
                    when_class | None,
                    Field(default=None, description=description),
                )

    return (scoped_fields, when_class)


def _model_name(model_class: type[BaseModel]) -> str:
    return model_class.model_config.get("title") or model_class.__name__


def _describe_when(
    parent: str, has_top_level_scopes: bool, when_scopes: list[Scope]
) -> str:
    description = "Additional scope" if has_top_level_scopes else "Scope"
    if len(when_scopes) > 1:
        description += "s"
    description = f"{description} for {parent}: "
    friendly_names = [str(s).replace("_", " ") for s in when_scopes]
    description += ", ".join(friendly_names[:-1])
    if len(when_scopes) > 1:
        description += f" and {friendly_names[-1]}"
    return description


def _make_when_class(
    model_class: type[BaseModel],
    when_fields: dict[str, Any],
    description: str,
) -> type[BaseModel]:
    qualname = f"{model_class.__name__}.When"
    config = ConfigDict(title=qualname)
    if model_class.model_config.get("frozen"):
        config["frozen"] = (
            True  # Perpetuate parent's immutable/hashable characteristics to "when" clause.
        )
    when_class = create_model(
        qualname,
        __config__=config,
        __doc__=description,
        __module__=model_class.__module__,
        __qualname__=qualname,
        **when_fields,
    )
    when_class = NoExtraFieldsConstraint().decorate(when_class)
    return when_class
