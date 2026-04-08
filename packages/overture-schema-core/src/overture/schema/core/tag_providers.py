from typing import get_args

from pydantic import BaseModel

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


def authority_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    """Add the ``"overture"`` tag if the model originates from an approved Overture package.

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
        Updated tags, with ``"overture"`` added if applicable.
    """
    if _matches_manifest(key):
        tags.add("overture")
    return tags


def theme_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    """Add the ``"overture:theme={theme}"`` tag if the model is a subclass of OvertureFeature.

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
        Updated tags, with ``"overture:theme={theme}"`` added if applicable.
    """
    for tp in collect_types(model_class):
        if issubclass(tp, OvertureFeature):
            tags.add(
                "overture:theme=" + get_args(tp.model_fields["theme"].annotation)[0]
            )
    return tags


def _matches_manifest(key: ModelKey) -> bool:
    return key.entry_point in APPROVED
