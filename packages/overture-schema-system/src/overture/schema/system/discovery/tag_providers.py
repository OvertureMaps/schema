"""Tag provider logic for Overture schema discovery system."""

from pydantic import BaseModel

from overture.schema.system.discovery.types import ModelKey
from overture.schema.system.feature import Feature
from overture.schema.system.typing_util import collect_types


def feature_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    """Add the ``"feature"`` tag if the model is a subclass of Feature.

    Parameters
    ----------
    model_class : type[BaseModel]
        Model class to inspect.
    key : ModelKey
        Key identifying the model.
    tags : set[str]
        Current tags; may be extended.

    Returns
    -------
    set[str]
        Updated tags, with ``"feature"`` added if applicable.
    """
    if any(issubclass(tp, Feature) for tp in collect_types(model_class)):
        tags.add("feature")
    return tags
