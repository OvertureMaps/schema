"""Model discovery system for Overture schema registry."""

import importlib.metadata
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel

from overture.schema.system.feature import Feature

logger = logging.getLogger(__name__)


RESERVED_TAGS: dict[str, set[str]] = {
    "overture": {"overture-schema-core"},
    "feature": {"overture-schema-system"},
}
TAG = r"[a-z0-9][a-z0-9_-]*"
NAMESPACE_TAG = r"[a-z0-9]+:[a-z0-9]+(?:=[a-z0-9_.-]+)?"
TAG_RE = re.compile(rf"^(?:{TAG}|{NAMESPACE_TAG})$")


@dataclass(frozen=True, slots=True)
class ModelKey:
    """Key identifying a registered model by name, entry point, and tags.

    Attributes
    ----------
    name : str
        The friendly name of the model, derived from the entry point key
    entry_point : str
        The entry point value in "module:Class" format
    tags : frozenset[str]
        A set of tags associated with the model, including both plain tags and structured tags

    """

    name: str  # friendly name from entry point key
    entry_point: str  # The entry point value in "module:Class" format
    tags: frozenset[str]  # plain and structured tags


@dataclass(frozen=True, slots=True)
class TagProviderKey:
    """Key identifying a registered model by namespace, theme, and type.

    Attributes
    ----------
    name : str
        The friendly name of the model, derived from the entry point key
    entry_point : str
        The entry point value in "module:Class" format

    """

    name: str  # friendly name from entry point key
    entry_point: str  # entry point value (module:Class)
    package_name: str  # distribution package name


TagProvider = Callable[[type[BaseModel], ModelKey, set[str]], set[str]]


def generate_tags(
    model_class: type[BaseModel],
    key: ModelKey,
    providers: dict[TagProviderKey, TagProvider],
) -> set[str]:
    tags: set[str] = set()

    for provider_key, provider in providers.items():
        try:
            added_tags = provider(model_class, key, tags.copy()).difference(tags)
            filtered_tags = _filter_tags(added_tags, provider_key)
            tags.update(filtered_tags)
        except Exception as e:
            logger.warning(
                f"Error in tag provider {provider.__name__} for model {key.name}: {e}"
            )

    return tags


def _filter_tags(tags: set[str], provider: TagProviderKey) -> set[str]:
    reserved_tags = tuple(
        tag for tag, dist in RESERVED_TAGS.items() if provider.package_name not in dist
    )

    return {tag for tag in tags if TAG_RE.match(tag) and tag not in reserved_tags}


def discover_tag_providers(
    tag_providers_group: str = "overture.tag_providers",
) -> dict[TagProviderKey, TagProvider]:
    tag_providers = {}

    try:
        for tag_provider in importlib.metadata.entry_points(group=tag_providers_group):
            try:
                tag_provider_class = tag_provider.load()

                key = TagProviderKey(
                    name=tag_provider.name,
                    entry_point=tag_provider.value,
                    package_name=getattr(tag_provider.dist, "name", ""),
                )

                tag_providers[key] = tag_provider_class

            except Exception as e:
                # Log warning but don't fail for individual tag providers
                logger.warning(
                    "Could not load tag provider %s: %s", tag_provider.name, e
                )
    except Exception as e:
        logger.warning("Could not discover entry points: %s", e)

    return tag_providers


def discover_models(
    model_group: str = "overture.models",
) -> dict[ModelKey, type[BaseModel]]:
    """Discover all registered Overture models via entry points.

    Parameters
    ----------
    model_group: str
        The entry point group to search for models (default: "overture.models")

    Returns
    -------
    dict[ModelKey, type[BaseModel]]
        Dict mapping ModelKey to model classes.
        Theme will be None for entries without an explicit theme component.
    """
    models = {}
    tag_providers = discover_tag_providers()

    try:
        for model in importlib.metadata.entry_points(group=model_group):
            try:
                model_class = model.load()

                key = ModelKey(
                    name=model.name,
                    entry_point=model.value,
                    tags=frozenset(),
                )

                try:
                    key = replace(
                        key,
                        tags=frozenset(generate_tags(model_class, key, tag_providers)),
                    )
                except Exception as e:
                    logger.warning(
                        "Could not resolve tags for model %s: %s", model.name, e
                    )

                models[key] = model_class

            except Exception as e:
                # Log warning but don't fail for individual models
                logger.warning("Could not load model %s: %s", model.name, e)
    except Exception as e:
        logger.warning("Could not discover entry points: %s", e)

    return models


def filter_models(
    models: dict[ModelKey, type[BaseModel]],
    tags: tuple[str, ...] = (),
    excluded_tags: tuple[str, ...] = (),
    type_names: tuple[str, ...] = (),
) -> dict[ModelKey, type[BaseModel]]:
    """Filter models to those that contain all required tags."""
    filters = []

    if tags:
        filters.append(lambda key: all(tag in key.tags for tag in tags))
    if excluded_tags:
        filters.append(lambda key: not any(tag in key.tags for tag in excluded_tags))
    if type_names:
        filters.append(lambda key: key.name in type_names)

    if filters:
        models = {
            key: model for key, model in models.items() if all(f(key) for f in filters)
        }
    return models


def get_registered_model(feature_type: str) -> type[BaseModel] | None:
    """Get the Pydantic model for a type.

    This uses setuptools entry points for registration.
    If multiple types share the same name, the first one encountered will be returned.

    Parameters
    ----------
    feature_type : str
        The type name

    Returns
    -------
    type[BaseModel] | None
        The first encountered model class if found, None otherwise.

    """
    # Check all discovered models for a match
    models = discover_models()
    # Need to find by type, not exact key match
    for key, model_class in models.items():
        if key.name == feature_type:
            return model_class
    return None


def tags_by_key(tags: frozenset[str] | set[str], key: str) -> set[str]:
    """Extract values for k/v tags with the given key.

    tags_by_key(frozenset({"overture:theme=buildings", "overture", "draft"}), "overture:theme")
    -> {"buildings"}
    """
    prefix = key + "="
    return {tag[len(prefix) :] for tag in tags if tag.startswith(prefix)}


def tags_by_namespace(tags: frozenset[str] | set[str], namespace: str) -> set[str]:
    """Extract tag bodies within a namespace.

    tags_by_namespace(frozenset({"system:extension", "overture"}), "system")
    -> {"extension"}
    """
    prefix = namespace + ":"
    return {tag[len(prefix) :] for tag in tags if tag.startswith(prefix)}


def feature_provider(
    model_class: type[BaseModel], key: ModelKey, tags: set[str]
) -> set[str]:
    if any(issubclass(tp, Feature) for tp in _extract_types(model_class)):
        tags.add("feature")
    return tags


def _extract_types(tp: Any) -> set[type]:  # noqa: ANN401
    result: set[type] = set()

    def visit(t: Any) -> None:  # noqa: ANN401
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
