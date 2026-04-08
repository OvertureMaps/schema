import re
import unittest

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


class TestPlainTagRegex(unittest.TestCase):
    def test_valid_plain_tags(self) -> None:
        valid_tags = [
            "v",
            "valid",
            "valid1",
            "valid_tag",
            "valid-tag",
            "0valid",
            "42",
        ]
        for tag in valid_tags:
            self.assertTrue(
                re.fullmatch(PLAIN_TAG, tag), f"PLAIN_TAG should match: {tag}"
            )
            self.assertTrue(TAG.fullmatch(tag), f"TAG should match: {tag}")
            self.assertTrue(
                is_valid_tag(tag), f"is_valid_tag should return True for: {tag}"
            )

    def test_invalid_plain_tags(self) -> None:
        invalid_tags = [
            "",
            "_invalid",
            "-invalid",
            "Invalid",
            "invalid!",
            "invalid ",
            "in.valid",
            "3.14",
        ]
        for tag in invalid_tags:
            self.assertFalse(
                re.fullmatch(PLAIN_TAG, tag), f"PLAIN_TAG should not match: {tag}"
            )
            self.assertFalse(TAG.fullmatch(tag), f"TAG should not match: {tag}")
            self.assertFalse(
                is_valid_tag(tag), f"is_valid_tag should return False for: {tag}"
            )


class TestNamespaceTagRegex(unittest.TestCase):
    def test_valid_namespace_tags(self) -> None:
        valid_tags = [
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
        for tag in valid_tags:
            self.assertTrue(
                re.fullmatch(NAMESPACE_TAG, tag), f"NAMESPACE_TAG should match: {tag}"
            )
            self.assertTrue(TAG.fullmatch(tag), f"TAG should match: {tag}")
            self.assertTrue(
                is_valid_tag(tag), f"is_valid_tag should return True for: {tag}"
            )

    def test_invalid_namespace_tags(self) -> None:
        invalid_tags = [
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
        for tag in invalid_tags:
            self.assertFalse(
                re.fullmatch(NAMESPACE_TAG, tag),
                f"NAMESPACE_TAG should not match: {tag}",
            )
            self.assertFalse(TAG.fullmatch(tag), f"TAG should not match: {tag}")
            self.assertFalse(
                is_valid_tag(tag), f"is_valid_tag should return False for: {tag}"
            )
