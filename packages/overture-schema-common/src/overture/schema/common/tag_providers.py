"""Tag providers for the common Overture schema package.

Each provider inspects a discovered model and returns the set of tags
that should be attached. Registered via the
`overture.tag_providers` entry-point group.
"""

from collections.abc import Iterable
from typing import Literal, get_args, get_origin

from pydantic import BaseModel

from overture.schema.common import OvertureFeature
from overture.schema.system.discovery import ModelKey


def overture_provider(
    types: Iterable[type[BaseModel]],
    key: ModelKey,
    tags: set[str],
) -> set[str]:
    """Add `"overture"` when the entry point references an `OvertureFeature`.

    The tag says the model is built on Overture's feature model -- that it
    carries the theme/type/id/version/sources contract `OvertureFeature`
    defines -- as distinct from `feature`, which says only that it is a
    `Feature`. It exists so that question is answerable by tag:
    `overture-schema list-types --tag overture` selects those types, and a
    consumer filtering on them needs no dependency on this package and no
    `issubclass` call.

    It is *not* a claim that the type belongs to the Overture schema. Any
    package can subclass `OvertureFeature` and register an entry point, and
    this provider tags it like any other. Reserving the tag to this package
    governs who may *emit* it, not which models receive it.

    One qualifying arm is enough: a discriminated union with any
    `OvertureFeature` arm is an Overture feature type.

    This shares its predicate with `theme_provider` below, so `overture` is
    also derivable as "carries any `overture:theme=` tag". It is emitted
    separately because a selector a user can type is worth more than the
    derivation, and because a future non-themed `OvertureFeature` would
    break the equivalence.

    Parameters
    ----------
    types
        Concrete `BaseModel` subclasses for the entry point. For
        discriminated-union features this is every arm.
    key
        Key identifying the model.
    tags
        Current tags; may be extended.

    Returns
    -------
    set[str]
        Updated tags, with `"overture"` added if applicable.
    """
    if any(issubclass(tp, OvertureFeature) for tp in types):
        tags.add("overture")
    return tags


def theme_provider(
    types: Iterable[type[BaseModel]],
    key: ModelKey,
    tags: set[str],
) -> set[str]:
    """Add `"overture:theme={theme}"` for each `OvertureFeature` referenced.

    Tags are attached to the entry point's `ModelKey`. For
    discriminated-union features, every concrete arm contributes its
    own `theme`; arms that share a theme deduplicate to a single tag,
    and arms with different themes contribute multiple
    `overture:theme=X` tags to the same `ModelKey`.

    Each arm's `theme` field must be annotated as a single-value
    `Literal[str]`; any other annotation is a model-definition bug and
    raises `TypeError`.

    Parameters
    ----------
    types
        Concrete `BaseModel` subclasses for the entry point. For
        discriminated-union features this is every arm.
    key
        Key identifying the model.
    tags
        Current tags; may be extended.

    Returns
    -------
    set[str]
        Updated tags, with `"overture:theme={theme}"` added if applicable.

    Raises
    ------
    TypeError
        If a referenced `OvertureFeature`'s `theme` is not a single-value
        `Literal[str]`.
    """
    for tp in types:
        if issubclass(tp, OvertureFeature):
            tags.add(f"overture:theme={_theme_literal(tp)}")
    return tags


def _theme_literal(model_class: type[OvertureFeature]) -> str:
    """Extract the literal `theme` value from an `OvertureFeature` subclass.

    Raises
    ------
    TypeError
        If `theme` is not annotated as a single-value `Literal`.
    """
    annotation = model_class.model_fields["theme"].annotation
    if get_origin(annotation) is not Literal:
        raise TypeError(
            f"{model_class.__name__}.theme must be annotated Literal[...]; "
            f"got {annotation!r}"
        )
    args = get_args(annotation)
    if len(args) != 1 or not isinstance(args[0], str):
        raise TypeError(
            f"{model_class.__name__}.theme must be a single-value str Literal; "
            f"got {annotation!r}"
        )
    return args[0]
