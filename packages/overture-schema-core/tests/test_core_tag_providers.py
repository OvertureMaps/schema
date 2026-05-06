"""Tests for core tag providers."""

from typing import Annotated, Literal

import pytest
from overture.schema.core import OvertureFeature
from overture.schema.core.tag_providers import (
    theme_provider,
)
from overture.schema.system.discovery import ModelKey
from overture.schema.system.discovery.discovery import _generate_tags
from overture.schema.system.discovery.types import TagProviderDict, TagProviderKey
from pydantic import BaseModel, Field, Tag


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
    tags = theme_provider((building,), _empty_key(), set())
    assert tags == {"overture:theme=buildings"}


def test_theme_provider_discriminated_union() -> None:
    # `_generate_tags` is responsible for walking the union to concrete arms.
    class Road(OvertureFeature[Literal["transportation"], Literal["road"]]):
        pass

    class Rail(OvertureFeature[Literal["transportation"], Literal["rail"]]):
        pass

    union = Annotated[
        Annotated[Road, Tag("road")] | Annotated[Rail, Tag("rail")],
        Field(discriminator="type"),
    ]
    provider_key = TagProviderKey(
        name="theme",
        entry_point="core:theme_provider",
        package_name="overture-schema-core",
    )
    providers: TagProviderDict = {provider_key: theme_provider}
    tags = _generate_tags(union, _empty_key(), providers)
    assert tags == {"overture:theme=transportation"}


def test_theme_provider_skips_non_overture(not_overture: type[BaseModel]) -> None:
    tags = theme_provider((not_overture,), _empty_key(), set())
    assert tags == set()


def test_theme_provider_raises_on_non_literal_theme() -> None:
    class BadFeature(OvertureFeature):  # type: ignore[type-arg]
        # ThemeT defaults to str (its bound), not Literal — a third-party
        # bug we want to surface.
        pass

    with pytest.raises(TypeError, match="must be annotated Literal"):
        theme_provider((BadFeature,), _empty_key(), set())
