from typing import Any, get_origin, Annotated, get_args, Union, Literal

from overture.schema.core import OvertureFeature
from pydantic import BaseModel

from overture.schema.system.discovery import ModelKey

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
}


def authority_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    if _matches_manifest(key):
        tags.add("overture:official")
    return tags


def overture_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    if any(issubclass(tp, OvertureFeature) for tp in _reduce_types(model_class)):
        tags.add("overture:feature")
    return tags


def theme_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    for tp in _reduce_types(model_class):
        if issubclass(tp, OvertureFeature):
            tags.add(
                "overture:theme=" + get_args(tp.model_fields["theme"].annotation)[0]
            )
    return tags


def _matches_manifest(key: ModelKey) -> bool:
    if key.entry_point in APPROVED:
        return True
    return False


def _reduce_types(tp: Any) -> set[type]:
    result: set[type] = set()

    def visit(t: Any) -> None:
        origin = get_origin(t)
        if origin is Annotated:
            visit(get_args(t)[0])
            return

        if hasattr(t, "__supertype__"):
            visit(t.__supertype__)
            return

        origin = get_origin(t)

        if origin is Union:
            for arg in get_args(t):
                visit(arg)
            return

        if origin is Literal:
            for val in get_args(t):
                result.add(type(val))
            return

        result.add(t)

    visit(tp)
    return result
