__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from collections.abc import Generator
from functools import reduce
from operator import or_
from types import UnionType
from typing import Annotated, Any, Literal, cast, get_args, get_origin

from pydantic import BaseModel, Field, Tag, TypeAdapter

from overture.schema.core import OvertureFeature
from overture.schema.core.discovery import discover_models
from overture.schema.system.feature import Feature


def validate(data: object) -> BaseModel:
    """
    Validate a Python object, which can be a dictionary or model instance, using the union of all
    discovered Overture models.

    Parameters
    ----------
    data : object
        Python object to validate against the model.

    Returns
    -------
    BaseModel
        Validated model class

    Raises
    ------
    ValidationError
        If `data` is not valid according to one of the discovered Overture models
    """
    tap = _union_type_adapter()

    return cast(BaseModel, tap.validate_python(data))


def validate_json(json_data: str | bytes | bytearray) -> BaseModel:
    """
    Validate JSON data using the union of all discovered Overture models.

    Parameters
    ----------
    data : str | bytes | bytearray
        JSON data to validate

    Returns
    -------
    BaseModel
        Validated model class

    Raises
    ------
    ValidationError
        If `json_data` is not valid according to one of the discovered Overture models
    """
    tap = _union_type_adapter()

    return cast(BaseModel, tap.validate_json(json_data))


__all__ = [
    "validate",
    "validate_json",
]


def _union_type_adapter() -> TypeAdapter:
    """
    Return a Pydantic type adapter that can validate the union of all models discovered using entry
    points.
    """
    models = discover_models()
    if not models:
        raise RuntimeError("no registered models found via entry points")

    discriminated_models: tuple[type[OvertureFeature], ...] = tuple(
        cast(type[OvertureFeature], m) for m in models.values() if _can_discriminate(m)
    )
    discriminated_union: UnionType | None = _discriminated_union(discriminated_models)

    non_discriminated_models: Generator[type[BaseModel], None, None] = (
        m for m in models.values() if not _can_discriminate(m)
    )
    non_discriminated_union: UnionType | None = reduce(
        or_, non_discriminated_models, None
    )

    if discriminated_union and non_discriminated_union:
        model_union = discriminated_union | non_discriminated_union
    elif discriminated_union:
        model_union = discriminated_union
    elif non_discriminated_union:
        model_union = non_discriminated_union
    else:
        raise RuntimeError("logic error: unreachable code")

    return TypeAdapter(model_union)


def _discriminated_union(
    feature_classes: tuple[type[OvertureFeature], ...],
) -> Any:  # noqa: ANN401
    """
    Create a discriminated union of the Overture features since they can be discriminated on the
    `type` field. This is just a performance optimization, and the union will work even if no models
    are discriminated.
    """
    if not feature_classes:
        return None
    else:
        return Annotated[
            reduce(
                or_,
                (
                    Annotated[f, Tag(cast(str, _typeliteral(f)))]
                    for f in feature_classes
                ),
            ),
            Field(discriminator=Feature.field_discriminator("type", *feature_classes)),
        ]


def _can_discriminate(model_class: object) -> bool:
    """
    Return true if given value can participate in a discriminated union on the `type` field because
    it is an Overture feature with where the `type` field has a single literal value.
    """
    return (
        isinstance(model_class, type)
        and issubclass(model_class, OvertureFeature)
        and _typeliteral(cast(type[OvertureFeature], model_class)) is not None
    )


def _typeliteral(feature_class: type[OvertureFeature]) -> object:
    """
    Return the literal value of the Overture Feature model's `type` field, if it has one, or `None`
    if it does not.

    Parameters
    ----------
    feature_class : type[OvertureFeature]
        Overture feature model class

    Returns
    -------
    object
        The literal constrained value of the model class' `type` field, or `None` if the `type`
        field does not have a literal value

    Raises
    ------
    TypeError
        If the `type` field is constrained to `Literal[None]`, as this is absurd
    """
    type_type = feature_class.model_fields["type"].annotation
    while get_origin(type_type) is Annotated:
        type_type = get_args(Annotated)[0]
    if get_origin(type_type) is not Literal:
        return None
    literal = get_args(type_type)[0]
    if literal is None:
        raise TypeError(
            f"literal value of `type` field for `{OvertureFeature.__name__}` class "
            f"`{feature_class.__name__}` is constrained to `None`"
        )
    return literal
