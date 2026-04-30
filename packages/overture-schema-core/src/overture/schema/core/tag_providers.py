"""Tag providers for the core Overture schema package.

Each provider inspects a discovered model and returns the set of tags
that should be attached. Registered via the
`overture.tag_providers` entry-point group.
"""

from typing import Any, Literal, get_args, get_origin

from overture.schema.core import OvertureFeature
from overture.schema.system.discovery import ModelKey
from overture.schema.system.typing_util import collect_types

APPROVED = {
    "overture.schema.addresses:Address",
    "overture.schema.base:Bathymetry",
    "overture.schema.base:Infrastructure",
    "overture.schema.base:Land",
    "overture.schema.base:LandCover",
    "overture.schema.base:LandUse",
    "overture.schema.base:Water",
    "overture.schema.buildings:Building",
    "overture.schema.buildings:BuildingPart",
    "overture.schema.divisions:Division",
    "overture.schema.divisions:DivisionArea",
    "overture.schema.divisions:DivisionBoundary",
    "overture.schema.places:Place",
    "overture.schema.transportation:Connector",
    "overture.schema.transportation:Segment",
    "overture.schema.annex:Sources",
}


def authority_provider(model_class: Any, key: ModelKey, tags: set[str]) -> set[str]:  # noqa: ANN401
    """Add the `"overture"` tag if the model originates from an approved Overture package.

    Parameters
    ----------
    model_class
        A class or discriminated-union type expression loaded from an
        `overture.models` entry point.
    key
        Key identifying the model.
    tags
        Current tags; may be extended.

    Returns
    -------
    set[str]
        Updated tags, with `"overture"` added if applicable.
    """
    if _matches_manifest(key):
        tags.add("overture")
    return tags


def theme_provider(model_class: Any, key: ModelKey, tags: set[str]) -> set[str]:  # noqa: ANN401
    """Add `"overture:theme={theme}"` for each `OvertureFeature` referenced.

    Tags are attached to the entry point's `ModelKey`. For
    discriminated-union features, the provider walks every concrete arm
    via `collect_types` and reads each arm's `theme`; tags from all arms
    accumulate on the union's `ModelKey`. Arms that share a theme
    deduplicate to a single tag; arms with different themes contribute
    multiple `overture:theme=X` tags to the same `ModelKey`.

    Each arm's `theme` field must be annotated as a single-value
    `Literal[str]`; any other annotation is a model-definition bug and
    raises `TypeError`.

    Parameters
    ----------
    model_class
        A class or discriminated-union type expression loaded from an
        `overture.models` entry point.
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
    for tp in collect_types(model_class):
        if issubclass(tp, OvertureFeature):
            tags.add(f"overture:theme={_theme_literal(tp)}")
    return tags


def _matches_manifest(key: ModelKey) -> bool:
    return key.entry_point in APPROVED


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
