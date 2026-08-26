"""Tests for common tag providers."""

from typing import Annotated, Literal

import pytest
from pydantic import BaseModel, Field, Tag

from overture.schema.common import OvertureFeature
from overture.schema.common.tag_providers import (
    overture_provider,
    theme_provider,
)
from overture.schema.system.discovery import ModelKey
from overture.schema.system.discovery.discovery import _generate_tags
from overture.schema.system.discovery.types import (
    TagProvider,
    TagProviderDict,
    TagProviderKey,
)


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


@pytest.fixture
def transportation_union() -> object:
    """A two-arm transportation union. `_generate_tags` walks it to the arms."""

    class Road(OvertureFeature[Literal["transportation"], Literal["road"]]):
        pass

    class Rail(OvertureFeature[Literal["transportation"], Literal["rail"]]):
        pass

    return Annotated[
        Annotated[Road, Tag("road")] | Annotated[Rail, Tag("rail")],
        Field(discriminator="type"),
    ]


def _providers(provider: TagProvider) -> TagProviderDict:
    """Register one provider under a key this package is allowed to use."""
    key = TagProviderKey(
        name=provider.__name__.removesuffix("_provider"),
        entry_point=f"common:{provider.__name__}",
        package_name="overture-schema-common",
    )
    return {key: provider}


def test_theme_provider_plain_class(building: type[OvertureFeature]) -> None:
    tags = theme_provider((building,), _empty_key(), set())
    assert tags == {"overture:theme=buildings"}


def test_theme_provider_discriminated_union(transportation_union: object) -> None:
    tags = _generate_tags(
        transportation_union, _empty_key(), _providers(theme_provider)
    )
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


def test_overture_provider_plain_class(building: type[OvertureFeature]) -> None:
    tags = overture_provider((building,), _empty_key(), set())
    assert tags == {"overture"}


def test_overture_provider_discriminated_union(transportation_union: object) -> None:
    tags = _generate_tags(
        transportation_union, _empty_key(), _providers(overture_provider)
    )
    assert tags == {"overture"}


def test_overture_provider_skips_non_overture(not_overture: type[BaseModel]) -> None:
    tags = overture_provider((not_overture,), _empty_key(), set())
    assert tags == set()


def test_overture_provider_partial_union_still_tags(
    not_overture: type[BaseModel],
) -> None:
    """One Overture arm is enough; a mixed union still counts as Overture."""

    class Road(OvertureFeature[Literal["transportation"], Literal["road"]]):
        pass

    tags = overture_provider((not_overture, Road), _empty_key(), set())
    assert tags == {"overture"}
