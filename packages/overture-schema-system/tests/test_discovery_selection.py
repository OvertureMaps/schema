"""Tests for `select_models`: user predicates plus default extension hiding."""

from pydantic import BaseModel

from overture.schema.system.discovery import (
    ModelKey,
    TagSelector,
    select_models,
)
from overture.schema.system.discovery.types import ModelDict
from overture.schema.system.extension import extends, wrap_extension


class Building(BaseModel):
    name: str


@extends(Building)
class Capacity(BaseModel):
    capacity: int | None = None


@extends(Building)
class Hours(BaseModel):
    hours: str | None = None


def _wrapper(name: str, obj: object) -> type[BaseModel]:
    wrapper = wrap_extension(name, obj)
    assert wrapper is not None
    return wrapper


def _key(name: str, *tags: str, entry_point: str | None = None) -> ModelKey:
    return ModelKey(
        name=name, entry_point=entry_point or f"m:{name}", tags=frozenset(tags)
    )


BUILDING = _key("building", "feature")
CAPACITY = _key("capacity", "extension")
# Deliberately untagged: hiding is structural, so an entry whose tag
# generation failed must stay hidden rather than leak into selections.
HOURS_UNTAGGED = _key("hours")

MODELS: ModelDict = {
    BUILDING: Building,
    CAPACITY: _wrapper("capacity", Capacity),
    HOURS_UNTAGGED: _wrapper("hours", Hours),
}


def test_extensions_dropped_by_default() -> None:
    assert select_models(MODELS) == {BUILDING: Building}


def test_hiding_is_structural_not_tag_based() -> None:
    # The untagged wrapper is still hidden: fail-safe against tag failures.
    assert HOURS_UNTAGGED not in select_models(MODELS)


def test_include_extension_entries_shows_everything() -> None:
    assert select_models(MODELS, include_extension_entries=True) == MODELS


def test_engaging_the_tag_lifts_the_default() -> None:
    # The tag is the *selection* vocabulary: engaging it lifts the default,
    # and the predicate stage then matches tagged entries (the untagged wrapper is
    # unreachable this way -- by design, its tags are broken).
    selected = select_models(MODELS, TagSelector(include_any=("extension",)))
    assert set(selected) == {CAPACITY}
    selected = select_models(MODELS, TagSelector(require_all=("extension",)))
    assert set(selected) == {CAPACITY}


def test_user_exclusion_always_wins() -> None:
    # A user's own exclude is a predicate, not a default -- naming or engaging
    # cannot override it.
    selector = TagSelector(exclude_any=("extension",))
    assert select_models(MODELS, selector, type_names=("capacity",)) == {}


def test_extension_only_name_is_exempt_from_the_default() -> None:
    # "capacity" resolves exclusively to a hidden entry: naming it was
    # necessarily about that entry. Works for the untagged wrapper too.
    assert set(select_models(MODELS, type_names=("capacity",))) == {CAPACITY}
    assert set(select_models(MODELS, type_names=("hours",))) == {HOURS_UNTAGGED}


def test_ambiguous_name_keeps_the_wrapper_hidden() -> None:
    # A model and an extension sharing an entry-point name: naming it selects
    # the visible entry only, so a collision cannot smuggle the permissive
    # wrapper into a selection.
    collided_model = _key("capacity", "feature", entry_point="other:Capacity")
    models: ModelDict = {**MODELS, collided_model: Building}
    selected = select_models(models, type_names=("capacity",))
    assert set(selected) == {collided_model}


def test_ambiguous_name_with_engaged_tag_shows_both() -> None:
    collided_model = _key("capacity", "feature", entry_point="other:Capacity")
    models: ModelDict = {**MODELS, collided_model: Building}
    selected = select_models(
        models,
        TagSelector(include_any=("extension", "feature")),
        type_names=("capacity",),
    )
    assert set(selected) == {CAPACITY, collided_model}


def test_type_names_still_conjoin_with_predicates() -> None:
    assert select_models(MODELS, type_names=("building",)) == {BUILDING: Building}
    assert select_models(MODELS, type_names=("nonexistent",)) == {}
