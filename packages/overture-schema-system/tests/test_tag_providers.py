from collections.abc import Iterable
from typing import Annotated

import pytest
from pydantic import BaseModel, Field, Tag

from overture.schema.system.discovery.discovery import _generate_tags
from overture.schema.system.discovery.tag_providers import feature_provider
from overture.schema.system.discovery.types import (
    ModelKey,
    TagProvider,
    TagProviderDict,
    TagProviderKey,
)
from overture.schema.system.feature import Feature


@pytest.fixture
def core_tag_provider() -> TagProviderKey:
    return TagProviderKey(
        name="core", entry_point="core:Provider", package_name="overture-schema-core"
    )


@pytest.fixture
def system_tag_provider() -> TagProviderKey:
    return TagProviderKey(
        name="system",
        entry_point="system:Provider",
        package_name="overture-schema-system",
    )


@pytest.fixture
def other_tag_provider() -> TagProviderKey:
    return TagProviderKey(
        name="other", entry_point="other:Provider", package_name="other-package"
    )


@pytest.fixture
def feature() -> type[Feature]:
    class SomeFeature(Feature):
        pass

    return SomeFeature


@pytest.fixture
def not_a_feature() -> type[BaseModel]:
    class NotAFeature(BaseModel):
        pass

    return NotAFeature


@pytest.fixture
def any_key() -> ModelKey:
    return ModelKey(name="x", entry_point="m:X", tags=frozenset())


@pytest.fixture
def any_model() -> type[BaseModel]:
    class M(BaseModel):
        pass

    return M


def fake_provider(*tags: str) -> TagProvider:
    """Provider that always returns the given tags, ignoring its inputs."""

    def _provider(
        types: Iterable[type[BaseModel]],
        key: ModelKey,
        current_tags: set[str],
    ) -> set[str]:
        return set(tags)

    return _provider


def test_valid_tags(
    other_tag_provider: TagProviderKey,
    any_key: ModelKey,
    any_model: type[BaseModel],
) -> None:
    providers = {
        other_tag_provider: fake_provider("valid", "other:valid", "other:valid=true")
    }
    result = _generate_tags(any_model, any_key, providers)
    assert result == {"valid", "other:valid", "other:valid=true"}


def test_invalid_tag(
    other_tag_provider: TagProviderKey,
    any_key: ModelKey,
    any_model: type[BaseModel],
) -> None:
    providers = {other_tag_provider: fake_provider("InvalidTag")}
    result = _generate_tags(any_model, any_key, providers)
    assert result == set()


def test_reserved_tag(
    other_tag_provider: TagProviderKey,
    any_key: ModelKey,
    any_model: type[BaseModel],
) -> None:
    providers = {other_tag_provider: fake_provider("feature", "valid")}
    result = _generate_tags(any_model, any_key, providers)
    assert result == {"valid"}


def test_allowed_reserved_tag(
    system_tag_provider: TagProviderKey,
    any_key: ModelKey,
    any_model: type[BaseModel],
) -> None:
    system_providers = {system_tag_provider: fake_provider("feature")}
    assert _generate_tags(any_model, any_key, system_providers) == {"feature"}


def test_reserved_namespace(
    other_tag_provider: TagProviderKey,
    any_key: ModelKey,
    any_model: type[BaseModel],
) -> None:
    providers = {
        other_tag_provider: fake_provider(
            "overture:feature", "system:feature", "valid:tag"
        )
    }
    result = _generate_tags(any_model, any_key, providers)
    assert result == {"valid:tag"}


def test_allowed_reserved_namespace(
    core_tag_provider: TagProviderKey,
    system_tag_provider: TagProviderKey,
    any_key: ModelKey,
    any_model: type[BaseModel],
) -> None:
    core_providers = {core_tag_provider: fake_provider("overture:feature")}
    assert _generate_tags(any_model, any_key, core_providers) == {"overture:feature"}

    system_providers = {system_tag_provider: fake_provider("system:feature")}
    assert _generate_tags(any_model, any_key, system_providers) == {"system:feature"}


def test_empty_tags(
    other_tag_provider: TagProviderKey,
    any_key: ModelKey,
    any_model: type[BaseModel],
) -> None:
    providers = {other_tag_provider: fake_provider()}
    assert _generate_tags(any_model, any_key, providers) == set()


def test_mixed_tags(
    other_tag_provider: TagProviderKey,
    any_key: ModelKey,
    any_model: type[BaseModel],
) -> None:
    providers = {
        other_tag_provider: fake_provider(
            "valid", "feature", "overture:feature", "InvalidTag"
        )
    }
    result = _generate_tags(any_model, any_key, providers)
    assert result == {"valid"}


def test_feature_provider_adds_feature_tag(feature: type[Feature]) -> None:
    key = ModelKey(name="feature", entry_point="system:Feature", tags=frozenset())
    result = feature_provider((feature,), key, set())
    assert "feature" in result


def test_feature_provider_does_not_add_feature_tag(
    not_a_feature: type[BaseModel],
) -> None:
    key = ModelKey(
        name="notafeature", entry_point="system:NotAFeature", tags=frozenset()
    )
    result = feature_provider((not_a_feature,), key, set())
    assert "feature" not in result


def test_feature_provider_handles_discriminated_union(
    system_tag_provider: TagProviderKey,
) -> None:
    # Mimics the shape of `Segment`: Annotated[Union[...], Field(discriminator=...)].
    # `_generate_tags` is responsible for walking the union to concrete arms.
    class ArmA(Feature):
        pass

    class ArmB(BaseModel):
        pass

    union = Annotated[
        Annotated[ArmA, Tag("a")] | Annotated[ArmB, Tag("b")],
        Field(discriminator="type"),
    ]
    key = ModelKey(name="union", entry_point="mod:Union", tags=frozenset())
    providers: TagProviderDict = {system_tag_provider: feature_provider}
    result = _generate_tags(union, key, providers)
    assert "feature" in result
