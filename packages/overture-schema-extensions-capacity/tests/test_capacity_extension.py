"""Tests for the capacity extension package (a non-model, scalar extension)."""

from typing import cast

import pytest
from overture.schema.buildings import Building
from overture.schema.extensions.capacity import Capacity
from overture.schema.places import Place
from overture.schema.system.discovery import discover_models
from overture.schema.system.extension import (
    create_extended_model,
    extension_targets,
    wrap_extension,
)
from overture.schema.system.geometric import Geometry
from pydantic import BaseModel, ValidationError

_maybe_wrapper = wrap_extension("capacity", Capacity)
assert _maybe_wrapper is not None
_WRAPPER: type[BaseModel] = _maybe_wrapper
PlaceWithCapacity: type[BaseModel] = create_extended_model(
    Place, {"capacity": _WRAPPER}
)
BuildingWithCapacity: type[BaseModel] = create_extended_model(
    Building, {"capacity": _WRAPPER}
)


def _model(value: object) -> type[BaseModel]:
    assert isinstance(value, type) and issubclass(value, BaseModel)
    return value


def _field(model: BaseModel, name: str) -> object:
    return cast(object, getattr(model, name))


def test_capacity_targets_place_and_building() -> None:
    assert extension_targets(Capacity) == (Place, Building)


def test_wrapper_enforces_uint8_range() -> None:
    assert _WRAPPER.model_validate({"capacity": 5}).model_dump()["capacity"] == 5
    with pytest.raises(ValidationError):
        _WRAPPER.model_validate({"capacity": 300})  # exceeds uint8


def test_place_gains_capacity() -> None:
    place = PlaceWithCapacity(
        id="p1",
        theme="places",
        type="place",
        version=1,
        geometry=Geometry.from_wkt("POINT (0 0)"),
        capacity=42,
    )
    assert _field(place, "capacity") == 42


def test_building_gains_capacity() -> None:
    building = BuildingWithCapacity(
        id="b1",
        theme="buildings",
        type="building",
        version=1,
        geometry=Geometry.from_wkt("POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))"),
        capacity=100,
    )
    assert _field(building, "capacity") == 100


def test_unrelated_model_not_extended() -> None:
    class Unrelated(BaseModel):
        value: int

    assert create_extended_model(Unrelated, {"capacity": _WRAPPER}) is Unrelated


def test_discovery_applies_capacity_to_both_targets() -> None:
    models = discover_models()
    by_name = {key.name: model for key, model in models.items()}
    assert "capacity" in _model(by_name["place"]).model_fields
    assert "capacity" in _model(by_name["building"]).model_fields
