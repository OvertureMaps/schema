import re

import pytest

from overture.schema.system.discovery.tag import (
    NAMESPACE_TAG,
    PLAIN_TAG,
    TAG,
    get_values_for_key,
    is_valid_tag,
)


def test_get_values_for_key_returns_correct_values() -> None:
    tags = frozenset({"overture:theme=buildings", "overture", "draft"})
    key = "overture:theme"
    result = get_values_for_key(tags, key)
    assert result == {"buildings"}


def test_get_values_for_key_returns_empty_set_for_nonexistent_key() -> None:
    tags = frozenset({"overture:theme=buildings", "overture", "draft"})
    key = "nonexistent:key"
    result = get_values_for_key(tags, key)
    assert result == set()


def test_get_values_for_key_handles_empty_tags() -> None:
    tags: frozenset[str] = frozenset()
    key = "overture:theme"
    result = get_values_for_key(tags, key)
    assert result == set()


VALID_PLAIN_TAGS = [
    "v",
    "valid",
    "valid1",
    "valid_tag",
    "valid-tag",
    "0valid",
    "42",
]

INVALID_PLAIN_TAGS = [
    "",
    "_invalid",
    "-invalid",
    "Invalid",
    "invalid!",
    "invalid ",
    "in.valid",
    "3.14",
]

VALID_NAMESPACE_TAGS = [
    "ns:predicate",
    "ns:predicate1",
    "ns:predicate-1",
    "ns:predicate=value",
    "ns:predicate=value_0",
    "ns:predicate=value-0",
    "ns:predicate=value.0",
    "ns:predicate=value_2-3.4",
    "ns:predicate=42",
    "ns:predicate=3.14",
    "ns:predicate=Value",
]

INVALID_NAMESPACE_TAGS = [
    "ns:",
    ":predicate",
    "ns:predicate=",
    "ns:predicate=value ",
    "ns:predicate=value!",
    "ns:predicate=ns:value",
    "ns:predicate=predicate=value",
    "Ns:predicate",
    "ns:Predicate",
]


@pytest.mark.parametrize("tag", VALID_PLAIN_TAGS)
def test_valid_plain_tag(tag: str) -> None:
    assert re.fullmatch(PLAIN_TAG, tag)
    assert TAG.fullmatch(tag)
    assert is_valid_tag(tag)


@pytest.mark.parametrize("tag", INVALID_PLAIN_TAGS)
def test_invalid_plain_tag(tag: str) -> None:
    assert not re.fullmatch(PLAIN_TAG, tag)
    assert not TAG.fullmatch(tag)
    assert not is_valid_tag(tag)


@pytest.mark.parametrize("tag", VALID_NAMESPACE_TAGS)
def test_valid_namespace_tag(tag: str) -> None:
    assert re.fullmatch(NAMESPACE_TAG, tag)
    assert TAG.fullmatch(tag)
    assert is_valid_tag(tag)


@pytest.mark.parametrize("tag", INVALID_NAMESPACE_TAGS)
def test_invalid_namespace_tag(tag: str) -> None:
    assert not re.fullmatch(NAMESPACE_TAG, tag)
    assert not TAG.fullmatch(tag)
    assert not is_valid_tag(tag)
