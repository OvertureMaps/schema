"""Union type construction for model validation."""

from functools import reduce
from operator import or_
from typing import Annotated, Any, Literal, TypeAlias, cast, get_args, get_origin

from pydantic import BaseModel, Field, Tag

from overture.schema.system.feature import Feature

from .discovery import ModelDict
from .models import OvertureFeature

UnionType: TypeAlias = type[BaseModel] | Any


def _can_discriminate(model_class: object) -> bool:
    """Check if a model can participate in a discriminated union.

    Returns True if the model is an OvertureFeature with a single literal 'type' value.
    """
    if not (isinstance(model_class, type) and issubclass(model_class, OvertureFeature)):
        return False

    return _type_literal(cast(type[OvertureFeature], model_class)) is not None


def _type_literal(feature_class: type[OvertureFeature]) -> str | None:
    """Extract the literal value from an OvertureFeature's 'type' field.

    Returns the literal type value, or None if not a single literal.
    """
    if "type" not in feature_class.model_fields:
        return None

    type_annotation = feature_class.model_fields["type"].annotation

    # Unwrap Annotated if present
    while get_origin(type_annotation) is Annotated:
        type_annotation = get_args(type_annotation)[0]

    # Check if it's a Literal with a single value
    if get_origin(type_annotation) is Literal:
        args = get_args(type_annotation)
        if len(args) == 1 and isinstance(args[0], str):
            return args[0]

    return None


def _discriminated_union(feature_classes: tuple[type[OvertureFeature], ...]) -> Any:  # noqa: ANN401
    """Create a discriminated union of Overture features on the 'type' field."""
    if not feature_classes:
        return None
    elif len(feature_classes) == 1:
        # Single model doesn't need a discriminated union
        return feature_classes[0]

    def _tag(f: type[OvertureFeature]) -> str:
        literal = _type_literal(f)
        assert literal is not None, (
            f"{f.__name__} passed _can_discriminate but has no type literal"
        )
        return literal

    return Annotated[
        reduce(
            or_,
            (Annotated[f, Tag(_tag(f))] for f in feature_classes),
        ),
        Field(discriminator=Feature.field_discriminator("type", *feature_classes)),
    ]


def create_union_type_from_models(
    models: ModelDict,
) -> UnionType:
    """Create a union type from a dict of models.

    Uses discriminated unions for OvertureFeatures when possible for better performance.

    Parameters
    ----------
    models : ModelDict
        Dict mapping ModelKey to Pydantic model classes

    Returns
    -------
    UnionType
        Union type suitable for TypeAdapter

    Raises
    ------
    ValueError
        If no models are provided

    """
    if not models:
        raise ValueError("No models provided")

    # Partition models in a single pass
    discriminated_list: list[type[OvertureFeature]] = []
    non_discriminated_list: list[type[BaseModel]] = []
    for m in models.values():
        if _can_discriminate(m):
            discriminated_list.append(cast(type[OvertureFeature], m))
        else:
            non_discriminated_list.append(m)

    discriminated_union = _discriminated_union(tuple(discriminated_list))
    non_discriminated_union = (
        reduce(or_, non_discriminated_list) if non_discriminated_list else None
    )

    # Combine discriminated and non-discriminated unions.
    # At least one is non-None because models is verified non-empty above
    # and every model lands in exactly one partition.
    assert discriminated_union is not None or non_discriminated_union is not None
    if discriminated_union is not None and non_discriminated_union is not None:
        return discriminated_union | non_discriminated_union
    elif discriminated_union is not None:
        return discriminated_union
    else:
        return non_discriminated_union  # type: ignore[return-value]
