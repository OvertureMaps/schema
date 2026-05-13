"""Model discovery system for Overture schema registry."""

import importlib.metadata
import logging
from dataclasses import dataclass, replace
from typing import Any

from pydantic import BaseModel

from overture.schema.system.discovery.tag import (
    get_namespace,
    is_valid_tag,
)
from overture.schema.system.discovery.types import (
    ModelDict,
    ModelKey,
    TagProviderDict,
    TagProviderKey,
)
from overture.schema.system.typing_util import collect_types

log = logging.getLogger(__name__)

# Tags that are reserved and can only be set by specific packages.
_RESERVED_TAGS: dict[str, set[str]] = {
    "feature": {"overture-schema-system"},
}
# Namespaces that are reserved and can only be set by specific packages.
_RESERVED_NAMESPACES: dict[str, set[str]] = {
    "overture": {"overture-schema-core"},
    "system": {"overture-schema-system"},
}


def _generate_tags(
    model_class: Any,  # noqa: ANN401
    key: ModelKey,
    providers: TagProviderDict,
) -> set[str]:
    """Generate tags for a model class using tag providers.

    The model is walked once via `collect_types` to find every concrete
    `BaseModel` arm, and each provider is called with the result. Tags
    a provider adds are filtered for validity and permission before
    being included. Provider errors are caught and logged as warnings
    rather than propagated.

    Parameters
    ----------
    model_class
        Value loaded from an `overture.models` entry point — usually a
        `type[BaseModel]`, or a discriminated-union expression.
    key
        Key identifying the model.
    providers
        Tag providers to invoke.

    Returns
    -------
    set[str]
        Tags generated for the model.
    """
    types = collect_types(model_class)
    tags: set[str] = set()
    for provider_key, provider in providers.items():
        try:
            added_tags = set(provider(types, key, tags.copy())) - tags
            filtered_tags = _filter_tags(added_tags, provider_key)
            tags.update(filtered_tags)
        except Exception as e:
            log.warning(
                f"Error in tag provider {provider_key.name} for model {key.name}: {e}",
                exc_info=True,
            )
    return tags


def _filter_tags(tags: set[str], provider: TagProviderKey) -> set[str]:
    """Filter tags that cannot be used by the provider, including invalid tags,
    reserved tags, and tags using a reserved namespace.

    Parameters
    ----------
    tags : set[str]
        Tags to filter.
    provider : TagProviderKey
        Provider attempting to set the tags.

    Returns
    -------
    set[str]
        Permitted tags.
    """
    filtered_tags: set[str] = set()
    reserved_tags: set[str] = {
        tag for tag, pkgs in _RESERVED_TAGS.items() if provider.package_name not in pkgs
    }
    reserved_namespaces: set[str] = {
        ns
        for ns, pkgs in _RESERVED_NAMESPACES.items()
        if provider.package_name not in pkgs
    }
    for tag in tags:
        if not is_valid_tag(tag):
            log.warning(
                f"Tag provider '{provider.name}' (package '{provider.package_name}') attempted to set '{tag}' as tag. "
                f"This tag does not match the required format."
            )
            continue
        if tag in reserved_tags:
            allowed_pkgs = _RESERVED_TAGS.get(tag, set())
            log.warning(
                f"Tag provider '{provider.name}' (package '{provider.package_name}') attempted to set reserved tag '{tag}'. "
                f"This tag can only be set by packages from: {allowed_pkgs}."
            )
            continue
        tag_ns = get_namespace(tag)
        if tag_ns and tag_ns in reserved_namespaces:
            allowed_pkgs = _RESERVED_NAMESPACES.get(tag_ns, set())
            log.warning(
                f"Tag provider '{provider.name}' (package '{provider.package_name}') attempted to set tag '{tag}' in reserved namespace '{tag_ns}'. "
                f"This namespace can only be set by packages from: {allowed_pkgs}."
            )
            continue
        filtered_tags.add(tag)
    return filtered_tags


def discover_tag_providers(
    tag_providers_group: str = "overture.tag_providers",
) -> TagProviderDict:
    """Discover and load tag providers via entry points.

    Parameters
    ----------
    tag_providers_group : str, optional
        Entry point group to search (default: `"overture.tag_providers"`).

    Returns
    -------
    TagProviderDict
        Discovered tag providers keyed by TagProviderKey.
    """
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
                log.warning(f"Could not load tag provider {tag_provider.name}: {e}")
    except Exception as e:
        log.warning(f"Could not discover entry points: {e}")
    return tag_providers


def discover_models(
    model_group: str = "overture.models",
) -> ModelDict:
    """Discover and load models via entry points, attaching tags from tag providers.

    Parameters
    ----------
    model_group : str, optional
        Entry point group to search (default: `"overture.models"`).

    Returns
    -------
    ModelDict
        Discovered models keyed by ModelKey.
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
                        tags=frozenset(_generate_tags(model_class, key, tag_providers)),
                    )
                except Exception as e:
                    log.warning(f"Could not resolve tags for model {model.name}: {e}")
                models[key] = model_class
            except Exception as e:
                log.warning(f"Could not load model {model.name}: {e}")
    except Exception as e:
        log.warning(f"Could not discover entry points: {e}")
    return models


@dataclass(frozen=True, slots=True, kw_only=True)
class TagSelector:
    """Three tag tuples consumed by `filter_models`.

    See `filter_models` for predicate semantics, including how
    empty tuples are interpreted.

    Attributes
    ----------
    include_any
        Scope (OR) — tags that bring models into the result.
    require_all
        Narrow (AND) — tags every kept model must have.
    exclude_any
        Subtract (OR-NOT) — tags that drop a model from the result.
    """

    include_any: tuple[str, ...] = ()
    require_all: tuple[str, ...] = ()
    exclude_any: tuple[str, ...] = ()


def filter_models(
    models: ModelDict,
    selector: TagSelector = TagSelector(),
    *,
    type_names: tuple[str, ...] = (),
) -> ModelDict:
    """Filter models by tag predicates and optional type-name match.

    Each tuple in `selector` is a predicate over `key.tags`; a model
    is kept only if it satisfies every predicate. Empty tuples are
    no-ops — empty `include_any` imposes no scope, empty
    `require_all` imposes no narrowing, empty `exclude_any` drops
    nothing — so an empty selector returns `models` unchanged.

    Parameters
    ----------
    models
        Models to filter.
    selector
        Tag predicates to apply.
    type_names
        If non-empty, only models whose `key.name` is in the list
        are kept. Orthogonal to the tag predicate algebra.

    Returns
    -------
    ModelDict
        Models satisfying every supplied predicate.
    """

    def matches(key: ModelKey) -> bool:
        if selector.include_any and not any(
            t in key.tags for t in selector.include_any
        ):
            return False
        if selector.require_all and not all(
            t in key.tags for t in selector.require_all
        ):
            return False
        if selector.exclude_any and any(t in key.tags for t in selector.exclude_any):
            return False
        if type_names and key.name not in type_names:
            return False
        return True

    return {k: m for k, m in models.items() if matches(k)}


def get_registered_model(model_name: str) -> type[BaseModel] | None:
    """Get the model by name.

    Loads all models via entry points and returns the first with a matching name.
    If multiple models share the same name, the first one encountered is returned.

    Parameters
    ----------
    model_name : str
        Model name to look up.

    Returns
    -------
    type[BaseModel] or None
        Model class if found, otherwise `None`.
    """
    models = discover_models()
    for key, model_class in models.items():
        if key.name == model_name:
            return model_class
    return None
