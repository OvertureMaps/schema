import re
import unittest

from overture.schema.system.discovery import (
    NAMESPACE_TAG,
    TAG,
    TAG_RE,
    tags_by_key,
    tags_by_namespace,
)


def test_tags_by_key_returns_correct_values() -> None:
    tags = frozenset({"overture:theme=buildings", "overture", "draft"})
    key = "overture:theme"
    result = tags_by_key(tags, key)
    assert result == {"buildings"}


def test_tags_by_key_returns_empty_set_for_nonexistent_key() -> None:
    tags = frozenset({"overture:theme=buildings", "overture", "draft"})
    key = "nonexistent:key"
    result = tags_by_key(tags, key)
    assert result == set()


def test_tags_by_key_handles_empty_tags() -> None:
    tags: frozenset[str] = frozenset()
    key = "overture:theme"
    result = tags_by_key(tags, key)
    assert result == set()


def test_tags_by_namespace_returns_correct_values() -> None:
    tags = frozenset({"system:extension", "overture"})
    namespace = "system"
    result = tags_by_namespace(tags, namespace)
    assert result == {"extension"}


def test_tags_by_namespace_returns_empty_set_for_nonexistent_namespace() -> None:
    tags = frozenset({"system:extension", "overture"})
    namespace = "nonexistent"
    result = tags_by_namespace(tags, namespace)
    assert result == set()


def test_tags_by_namespace_handles_empty_tags() -> None:
    tags: frozenset[str] = frozenset()
    namespace = "system"
    result = tags_by_namespace(tags, namespace)
    assert result == set()


class TestSimpleTagRegex(unittest.TestCase):
    def test_valid_simple_tags(self) -> None:
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
            self.assertTrue(re.fullmatch(TAG, tag), f"Should match: {tag}")
            self.assertTrue(TAG_RE.fullmatch(tag), f"TAG_RE should match: {tag}")

    def test_invalid_simple_tags(self) -> None:
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
            self.assertFalse(re.fullmatch(TAG, tag), f"Should not match: {tag}")
            self.assertFalse(TAG_RE.fullmatch(tag), f"TAG_RE should not match: {tag}")


class TestNamespaceTagRegex(unittest.TestCase):
    def test_valid_namespace_tags(self) -> None:
        valid_tags = [
            "ns:predicate",
            "ns:predicate1",
            "ns:predicate=value",
            "ns:predicate=value_0",
            "ns:predicate=value-0",
            "ns:predicate=value.0",
            "ns:predicate=value_2-3.4",
            "ns:predicate=42",
            "ns:predicate=3.14",
        ]
        for tag in valid_tags:
            self.assertTrue(re.fullmatch(NAMESPACE_TAG, tag), f"Should match: {tag}")
            self.assertTrue(TAG_RE.fullmatch(tag), f"TAG_RE should match: {tag}")

    def test_invalid_namespace_tags(self) -> None:
        invalid_tags = [
            "ns:",
            ":predicate",
            "ns:predicate=",
            "ns:predicate=Value",
            "ns:predicate=value ",
            "ns:predicate=value!",
            "ns:predicate=ns:value",
            "ns:predicate=predicate=value",
            "Ns:predicate",
            "ns:Predicate",
        ]
        for tag in invalid_tags:
            self.assertFalse(
                re.fullmatch(NAMESPACE_TAG, tag), f"Should not match: {tag}"
            )
            self.assertFalse(TAG_RE.fullmatch(tag), f"TAG_RE should not match: {tag}")
