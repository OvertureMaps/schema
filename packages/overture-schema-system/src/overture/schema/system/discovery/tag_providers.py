"""Tag provider logic for Overture schema discovery system."""

from collections.abc import Iterable

from pydantic import BaseModel

from overture.schema.system.discovery.types import ModelKey
from overture.schema.system.feature import Feature


def feature_provider(
    types: Iterable[type[BaseModel]],
    key: ModelKey,
    tags: set[str],
) -> set[str]:
    """Add the `"feature"` tag if any concrete type is a `Feature` subclass.

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
        Updated tags, with `"feature"` added if applicable.
    """
    if any(issubclass(tp, Feature) for tp in types):
        tags.add("feature")
    return tags
