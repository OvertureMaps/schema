"""Model discovery system for Overture schema registry."""

import importlib.metadata
import logging
from dataclasses import dataclass, replace
from typing import TypeGuard

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
from overture.schema.system.extension import (
    applied_extension_names,
    create_extended_model,
    extension_targets,
    wrap_extension,
)
from overture.schema.system.typing_util import collect_types

log = logging.getLogger(__name__)

# Set by `extension_provider`. In `select_models`, excluding it opts out of
# extension application.
_EXTENSION_TAG = "extension"

# Tags that are reserved and can only be set by specific packages.
_RESERVED_TAGS: dict[str, set[str]] = {
    "feature": {"overture-schema-system"},
    "overture": {"overture-schema-common"},
    _EXTENSION_TAG: {"overture-schema-system"},
}
# Namespaces that are reserved and can only be set by specific packages.
_RESERVED_NAMESPACES: dict[str, set[str]] = {
    "overture": {"overture-schema-common"},
    "system": {"overture-schema-system"},
}


def _generate_tags(
    model_class: object,
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
    *,
    apply_extensions: bool = True,
) -> ModelDict:
    """Discover and load models via entry points, attaching tags from tag providers.

    A three-stage pipeline -- load and wrap, merge extensions across the complete registry,
    then generate tags from the final model values -- so tags always describe the classes
    this function actually returns.

    Extension entry points are wrapped into standalone wrapper models at load time. When
    `apply_extensions` is true (the default), each extension's field is also merged into the
    target models it extends.

    Parameters
    ----------
    model_group : str, optional
        Entry point group to search (default: `"overture.models"`).
    apply_extensions : bool, optional
        Whether to merge discovered extensions into their target models (default: ``True``). Pass
        ``False`` to obtain the raw (un-extended) model set -- required when the result feeds
        `select_models`, which applies extensions itself so that the selector's excludes can
        opt out of them.

    Returns
    -------
    ModelDict
        Discovered models keyed by ModelKey.
    """
    models = _load_models(model_group)
    if apply_extensions:
        models = extend_models(models)
    return _attach_generated_tags(models)


def _load_models(model_group: str) -> ModelDict:
    """Load and wrap model entry points, keyed with empty tag sets.

    Load and wrap failures are reported distinctly, each skipping only its entry.
    """
    models: ModelDict = {}
    try:
        entries = importlib.metadata.entry_points(group=model_group)
    except Exception as e:
        log.warning(f"Could not discover entry points: {e}")
        return models
    for entry in entries:
        try:
            loaded = entry.load()
        except Exception as e:
            log.warning(f"Could not load model {entry.name}: {e}")
            continue
        try:
            wrapper = wrap_extension(
                entry.name, loaded, module=entry.value.partition(":")[0] or None
            )
        except Exception as e:
            log.warning(f"Could not wrap extension entry {entry.name}: {e}")
            continue
        if wrapper is not None:
            loaded = wrapper
        models[ModelKey(name=entry.name, entry_point=entry.value, tags=frozenset())] = (
            loaded
        )
    return models


def _attach_generated_tags(models: ModelDict) -> ModelDict:
    """Re-key *models* with tags generated from the final model values."""
    tag_providers = discover_tag_providers()
    tagged: ModelDict = {}
    for key, model in models.items():
        tags: frozenset[str] = frozenset()
        try:
            tags = frozenset(_generate_tags(model, key, tag_providers))
        except Exception as e:
            log.warning(f"Could not resolve tags for model {key.name}: {e}")
        tagged[replace(key, tags=tags)] = model
    return tagged


def extend_models(models: ModelDict, *, warn_unapplied: bool = True) -> ModelDict:
    """Merge discovered extensions into the target models they extend.

    Extensions are detected structurally (a wrapper model carrying extension targets), so this works
    on any `ModelDict` regardless of how its tags were filtered. Extension entries themselves are
    left unchanged; every other model is replaced by an extended subclass if any extension targets
    it.

    Parameters
    ----------
    models : ModelDict
        Models to process, as returned by `discover_models(apply_extensions=False)`.
    warn_unapplied : bool, optional
        Warn about extensions that applied to no model in *models* (default: ``True``).
        Over the full registry this flags an extension whose targets are not registered;
        `select_models` passes ``False``, because a narrowed selection legitimately omits
        an extension's targets.

    Returns
    -------
    ModelDict
        Models with extension fields merged into their targets.
    """

    def is_extension(model: object) -> TypeGuard[type[BaseModel]]:
        return (
            isinstance(model, type)
            and issubclass(model, BaseModel)
            and bool(extension_targets(model))
        )

    extension_candidates: dict[str, list[tuple[ModelKey, type[BaseModel]]]] = {}
    for key, model in models.items():
        if is_extension(model):
            extension_candidates.setdefault(key.name, []).append((key, model))

    extensions: dict[str, type[BaseModel]] = {}
    for field_name, candidates in extension_candidates.items():
        if len(candidates) > 1:
            entry_points = ", ".join(sorted(key.entry_point for key, _ in candidates))
            log.warning(
                f"Multiple extensions are registered for field '{field_name}' "
                f"({entry_points}); skipping all of them."
            )
            continue
        extensions[field_name] = candidates[0][1]
    if not extensions:
        return models
    # Skip by the entry's own shape, not by name: a non-extension model that merely
    # shares an entry-point name with an extension must still be extended. A failure
    # to extend one model must not abort the pass for every other model.
    extended: ModelDict = {}
    for key, model in models.items():
        if is_extension(model):
            extended[key] = model
            continue
        try:
            extended[key] = create_extended_model(model, extensions)
        except Exception as e:
            log.warning(
                f"Could not apply extensions to model '{key.name}' "
                f"({key.entry_point}): {e}; leaving it unextended."
            )
            extended[key] = model
    if warn_unapplied:
        applied_names = frozenset().union(
            *(applied_extension_names(model) for model in extended.values())
        )
        for field_name in sorted(set(extensions) - applied_names):
            log.warning(
                f"Extension '{field_name}' was not applied to any discovered model; "
                "its targets may not be registered via entry points."
            )
    return extended


@dataclass(frozen=True, slots=True, kw_only=True)
class TagSelector:
    """Three tag tuples consumed by `select_models`.

    See `matches` for predicate semantics, including how empty tuples
    are interpreted.

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

    def matches(self, tags: frozenset[str]) -> bool:
        """Whether *tags* satisfies every predicate tuple (empty tuples are no-ops)."""
        return (
            (not self.include_any or not tags.isdisjoint(self.include_any))
            and tags.issuperset(self.require_all)
            and tags.isdisjoint(self.exclude_any)
        )


def _filter_models(
    models: ModelDict,
    selector: TagSelector = TagSelector(),
    *,
    type_names: tuple[str, ...] = (),
) -> ModelDict:
    """Filter models by tag predicates and optional type-name match.

    The predicate stage of `select_models`, the public entry point, which
    additionally applies extensions to the filtered models.
    """
    names = frozenset(type_names)
    return {
        key: model
        for key, model in models.items()
        if (not names or key.name in names) and selector.matches(key.tags)
    }


def _is_extension_entry(model: object) -> bool:
    """Whether a registry entry structurally declares extension targets."""
    return bool(extension_targets(model))


def _reject_unhonorable_excludes(
    models: ModelDict,
    extension_keys: set[ModelKey],
    excluded_names: frozenset[str],
    blanket_exclusion: bool,
) -> None:
    """Raise if an extension exclusion cannot take effect on already-extended input.

    An exclusion can only prevent a *pending* merge. If a model in *models* already
    carries an excluded extension's field (it was merged during discovery), silently
    returning it would make the exclusion a no-op -- the wrapper entry disappears
    while the merged field stays behind.
    """
    if not excluded_names and not blanket_exclusion:
        return
    applied: frozenset[str] = frozenset()
    for key, model in models.items():
        if key not in extension_keys:
            applied |= applied_extension_names(model)
    blocked = applied if blanket_exclusion else applied & excluded_names
    if blocked:
        raise ValueError(
            f"cannot exclude extension(s) {sorted(blocked)}: the given models were "
            "already extended. Pass the raw registry from "
            "`discover_models(apply_extensions=False)` so `select_models` controls "
            "extension application."
        )


def select_models(
    models: ModelDict,
    selector: TagSelector = TagSelector(),
    *,
    type_names: tuple[str, ...] = (),
    include_extension_entries: bool = False,
) -> ModelDict:
    """Select models by user predicates, then apply the surviving extensions.

    *models* should be the raw registry from
    `discover_models(apply_extensions=False)`: extension application happens
    *here*, after selection, so the selector is also the extension opt-out.

    Application semantics are asymmetric by design. The selector's
    `exclude_any` gates merging: excluding the ``extension`` tag opts out of
    every extension (matched structurally, so it also covers a wrapper whose
    tag generation failed), and excluding a more specific tag opts out of the
    extensions carrying it. `include_any`/`require_all`/`type_names` do *not*
    gate merging -- selecting ``--type place`` narrows the result to `place`,
    it does not silently strip optional extension fields from it. Passing
    already-extended models together with an extension exclusion raises
    `ValueError`, because the exclusion could not take effect.

    Visibility of the standalone wrapper *entries* is separate from
    application: they are internal merge machinery, dropped from the result
    unless ``include_extension_entries=True`` is passed explicitly (for
    introspection, e.g. a registry listing; still subject to `selector` and
    `type_names`). Dropping is structural — declared extension targets, not
    the ``extension`` tag — so a wrapper whose tag generation failed stays
    hidden, and neither engaging the tag nor naming a wrapper in `type_names`
    surfaces one.
    """
    extension_keys = {
        key for key, model in models.items() if _is_extension_entry(model)
    }

    # Extensions to apply: gated by excludes only.
    blanket_exclusion = _EXTENSION_TAG in selector.exclude_any
    if blanket_exclusion:
        applicable: ModelDict = {}
    else:
        exclude_only = TagSelector(exclude_any=selector.exclude_any)
        applicable = {
            key: models[key] for key in extension_keys if exclude_only.matches(key.tags)
        }
    excluded_names = frozenset(key.name for key in extension_keys) - frozenset(
        key.name for key in applicable
    )
    _reject_unhonorable_excludes(
        models, extension_keys, excluded_names, blanket_exclusion
    )

    selected = _filter_models(models, selector, type_names=type_names)
    regular_selected = {
        key: model for key, model in selected.items() if key not in extension_keys
    }
    extended = extend_models({**regular_selected, **applicable}, warn_unapplied=False)
    result: ModelDict = {
        key: (model if key in extension_keys else extended[key])
        for key, model in selected.items()
    }

    if include_extension_entries:
        return result
    return {key: model for key, model in result.items() if key not in extension_keys}


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
