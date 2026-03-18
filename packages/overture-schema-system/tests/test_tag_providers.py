import pytest
from pydantic import BaseModel

from overture.schema.system.discovery import (
    ModelKey,
    TagProviderKey,
    _filter_tags,
    feature_provider,
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


def test_valid_tags(other_tag_provider: TagProviderKey) -> None:
    tags = {"valid", "other:valid", "other:valid=true"}
    filtered = _filter_tags(tags, other_tag_provider)
    assert filtered == tags


def test_invalid_tag(other_tag_provider: TagProviderKey) -> None:
    tags = {"InvalidTag"}
    filtered = _filter_tags(tags, other_tag_provider)
    assert filtered == set()


def test_reserved_tag(other_tag_provider: TagProviderKey) -> None:
    tags = {"overture", "feature", "valid"}
    filtered = _filter_tags(tags, other_tag_provider)
    assert "valid" in filtered
    assert "overture" not in filtered
    assert "feature" not in filtered


def test_allowed_reserved_tag(
    core_tag_provider: TagProviderKey, system_tag_provider: TagProviderKey
) -> None:
    assert "overture" in _filter_tags({"overture"}, core_tag_provider)
    assert "feature" in _filter_tags({"feature"}, system_tag_provider)


def test_reserved_namespace(other_tag_provider: TagProviderKey) -> None:
    tags = {"overture:feature", "system:feature", "valid:tag"}
    filtered = _filter_tags(tags, other_tag_provider)
    assert "valid:tag" in filtered
    assert "overture:feature" not in filtered
    assert "system:feature" not in filtered


def test_allowed_reserved_namespace(
    core_tag_provider: TagProviderKey, system_tag_provider: TagProviderKey
) -> None:
    assert "overture:feature" in _filter_tags({"overture:feature"}, core_tag_provider)
    assert "system:feature" in _filter_tags({"system:feature"}, system_tag_provider)


def test_empty_tags(other_tag_provider: TagProviderKey) -> None:
    assert _filter_tags(set(), other_tag_provider) == set()


def test_mixed_tags(other_tag_provider: TagProviderKey) -> None:
    tags = {"valid", "feature", "overture:feature", "InvalidTag"}
    filtered = _filter_tags(tags, other_tag_provider)
    assert filtered == {"valid"}


def test_feature_provider_adds_feature_tag(feature: type[Feature]) -> None:
    key = ModelKey(name="feature", entry_point="system:Feature", tags=frozenset())
    result = feature_provider(feature, key, set())
    assert "feature" in result


def test_feature_provider_does_not_add_feature_tag(
    not_a_feature: type[BaseModel],
) -> None:
    key = ModelKey(
        name="notafeature", entry_point="system:NotAFeature", tags=frozenset()
    )
    result = feature_provider(not_a_feature, key, set())
    assert "feature" not in result
