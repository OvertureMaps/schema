"""Tests for core tag providers."""

from typing import Annotated, Literal

import pytest
from overture.schema.core import OvertureFeature
from overture.schema.core.tag_providers import (
    APPROVED,
    authority_provider,
    theme_provider,
)
from overture.schema.system.discovery import ModelKey
from pydantic import BaseModel, Field, Tag


@pytest.fixture
def road() -> type[OvertureFeature]:
    class Road(OvertureFeature[Literal["transportation"], Literal["road"]]):
        pass

    return Road


@pytest.fixture
def building() -> type[OvertureFeature]:
    class Building(OvertureFeature[Literal["buildings"], Literal["building"]]):
        pass

    return Building


@pytest.fixture
def not_overture() -> type[BaseModel]:
    class NotOverture(BaseModel):
        pass

    return NotOverture


def _empty_key(name: str = "x", entry_point: str = "mod:X") -> ModelKey:
    return ModelKey(name=name, entry_point=entry_point, tags=frozenset())


def test_theme_provider_plain_class(building: type[OvertureFeature]) -> None:
    tags = theme_provider(building, _empty_key(), set())
    assert tags == {"overture:theme=buildings"}


def test_theme_provider_discriminated_union() -> None:
    class Road(OvertureFeature[Literal["transportation"], Literal["road"]]):
        pass

    class Rail(OvertureFeature[Literal["transportation"], Literal["rail"]]):
        pass

    union = Annotated[
        Annotated[Road, Tag("road")] | Annotated[Rail, Tag("rail")],
        Field(discriminator="type"),
    ]
    tags = theme_provider(union, _empty_key(), set())
    assert tags == {"overture:theme=transportation"}


def test_theme_provider_skips_non_overture(not_overture: type[BaseModel]) -> None:
    tags = theme_provider(not_overture, _empty_key(), set())
    assert tags == set()


def test_theme_provider_raises_on_non_literal_theme() -> None:
    class BadFeature(OvertureFeature):  # type: ignore[type-arg]
        # ThemeT defaults to str (its bound), not Literal — a third-party
        # bug we want to surface.
        pass

    with pytest.raises(TypeError, match="must be annotated Literal"):
        theme_provider(BadFeature, _empty_key(), set())


def test_authority_provider_approved(road: type[OvertureFeature]) -> None:
    approved_entry = next(iter(APPROVED))
    key = ModelKey(name="x", entry_point=approved_entry, tags=frozenset())
    tags = authority_provider(road, key, set())
    assert "overture" in tags


def test_authority_provider_not_approved(road: type[OvertureFeature]) -> None:
    key = ModelKey(name="x", entry_point="some.unapproved:Model", tags=frozenset())
    tags = authority_provider(road, key, set())
    assert "overture" not in tags
