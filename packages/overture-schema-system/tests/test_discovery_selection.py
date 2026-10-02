"""Tests for `select_models`: user predicates, extension application, default hiding."""

import pytest
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
CAPACITY = _key("capacity", "extension", "community")
# Deliberately untagged: hiding and the blanket opt-out are structural, so an
# entry whose tag generation failed must neither leak into selections nor
# dodge `exclude_any=("extension",)`.
HOURS_UNTAGGED = _key("hours")

MODELS: ModelDict = {
    BUILDING: Building,
    CAPACITY: _wrapper("capacity", Capacity),
    HOURS_UNTAGGED: _wrapper("hours", Hours),
}


def _fields(models: ModelDict, name: str) -> set[str]:
    model = next(m for k, m in models.items() if k.name == name)
    assert isinstance(model, type) and issubclass(model, BaseModel)
    return set(model.model_fields)


# ---------------------------------------------------------------------------
# Wrapper-entry visibility
# ---------------------------------------------------------------------------


def test_extensions_dropped_by_default() -> None:
    assert set(select_models(MODELS)) == {BUILDING}


def test_hiding_is_structural_not_tag_based() -> None:
    # The untagged wrapper is still hidden: fail-safe against tag failures.
    assert HOURS_UNTAGGED not in select_models(MODELS)


def test_include_extension_entries_shows_everything() -> None:
    selected = select_models(MODELS, include_extension_entries=True)
    assert set(selected) == set(MODELS)
    # Wrapper entries pass through unchanged; only targets are rebuilt.
    assert selected[CAPACITY] is MODELS[CAPACITY]
    assert selected[HOURS_UNTAGGED] is MODELS[HOURS_UNTAGGED]


def test_engaging_the_tag_does_not_surface_wrappers() -> None:
    # Wrappers are internal merge machinery: no selector spelling surfaces
    # them, only the explicit `include_extension_entries=True`.
    assert select_models(MODELS, TagSelector(include_any=("extension",))) == {}
    assert select_models(MODELS, TagSelector(require_all=("extension",))) == {}


def test_listing_wrappers_requires_the_explicit_parameter() -> None:
    # The supported introspection route: the explicit parameter, with the
    # selector still applying (only the tagged wrapper matches here).
    selected = select_models(
        MODELS,
        TagSelector(include_any=("extension",)),
        include_extension_entries=True,
    )
    assert set(selected) == {CAPACITY}


def test_user_exclusion_always_wins() -> None:
    # A user's own exclude is a predicate, not a default -- naming or engaging
    # cannot override it.
    selector = TagSelector(exclude_any=("extension",))
    assert select_models(MODELS, selector, type_names=("capacity",)) == {}


def test_naming_a_wrapper_does_not_surface_it() -> None:
    # Wrappers are not resolvable types: naming one selects nothing rather
    # than exposing the permissive standalone model.
    assert select_models(MODELS, type_names=("capacity",)) == {}
    assert select_models(MODELS, type_names=("hours",)) == {}


def test_name_collision_selects_the_visible_entry_only() -> None:
    # A model and an extension sharing an entry-point name: naming it selects
    # the visible entry only, so a collision cannot smuggle the permissive
    # wrapper into a selection.
    collided_model = _key("capacity", "feature", entry_point="other:Capacity")
    models: ModelDict = {**MODELS, collided_model: Building}
    selected = select_models(models, type_names=("capacity",))
    assert set(selected) == {collided_model}


def test_type_names_still_conjoin_with_predicates() -> None:
    assert set(select_models(MODELS, type_names=("building",))) == {BUILDING}
    assert select_models(MODELS, type_names=("nonexistent",)) == {}


# ---------------------------------------------------------------------------
# Extension application (selection-time, exclude-gated)
# ---------------------------------------------------------------------------


def test_selection_applies_extensions_by_default() -> None:
    assert {"capacity", "hours"} <= _fields(select_models(MODELS), "building")


def test_blanket_exclude_opts_out_of_all_extensions() -> None:
    selected = select_models(MODELS, TagSelector(exclude_any=("extension",)))
    # Nothing applied means the original class comes back, not a subclass.
    assert selected[BUILDING] is Building
    # The blanket opt-out is structural: the untagged wrapper is covered too.
    assert _fields(selected, "building").isdisjoint({"capacity", "hours"})


def test_tag_exclude_opts_out_of_matching_extensions_only() -> None:
    selected = select_models(MODELS, TagSelector(exclude_any=("community",)))
    fields = _fields(selected, "building")
    assert "capacity" not in fields
    assert "hours" in fields


def test_includes_do_not_gate_application() -> None:
    # Narrowing the scope by tag must not silently strip extension fields.
    selected = select_models(MODELS, TagSelector(include_any=("feature",)))
    assert {"capacity", "hours"} <= _fields(selected, "building")


def test_type_names_do_not_gate_application() -> None:
    # Naming a type must not silently strip extension fields either.
    selected = select_models(MODELS, type_names=("building",))
    assert {"capacity", "hours"} <= _fields(selected, "building")


def test_already_extended_input_with_exclusion_raises() -> None:
    already_extended = select_models(MODELS, include_extension_entries=True)
    with pytest.raises(ValueError, match="already extended"):
        select_models(already_extended, TagSelector(exclude_any=("extension",)))


def test_already_extended_input_with_tag_exclusion_raises() -> None:
    already_extended = select_models(MODELS, include_extension_entries=True)
    with pytest.raises(ValueError, match="already extended"):
        select_models(already_extended, TagSelector(exclude_any=("community",)))


def test_already_extended_input_without_exclusion_is_tolerated() -> None:
    # Re-selecting previously selected output is fine when no exclusion is in
    # play: re-applying an extension is a no-op.
    already_extended = select_models(MODELS, include_extension_entries=True)
    selected = select_models(already_extended)
    assert {"capacity", "hours"} <= _fields(selected, "building")
