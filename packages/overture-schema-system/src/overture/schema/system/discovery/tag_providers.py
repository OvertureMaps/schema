"""Tag provider logic for Overture schema discovery system."""

from typing import Any

from overture.schema.system.discovery.types import ModelKey
from overture.schema.system.feature import Feature
from overture.schema.system.typing_util import collect_types


def feature_provider(model_class: Any, key: ModelKey, tags: set[str]) -> set[str]:  # noqa: ANN401
    """Add the `"feature"` tag if the entry point references a `Feature` subclass.

    Tags are attached to the entry point's `ModelKey`. For
    discriminated-union features, the provider walks every concrete arm
    via `collect_types`; if any arm is a `Feature` subclass, the tag is
    added to the union's `ModelKey`.

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
        Updated tags, with `"feature"` added if applicable.
    """
    if any(issubclass(tp, Feature) for tp in collect_types(model_class)):
        tags.add("feature")
    return tags
