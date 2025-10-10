"""Test JSON Schema generation for mixin-based constraint validation."""

from enum import Enum
from typing import Any

import pytest


class SubtypeEnum(str, Enum):
    """Test enum for subtypes."""

    COUNTRY = "country"
    REGION = "region"
    LOCALITY = "locality"


def assert_pattern_constraint(
    schema: dict[str, Any],
    field_name: str,
    expected_pattern: str,
    expected_description: str | None = None,
) -> None:
    """Assert that a field has the expected pattern constraint."""
    assert "properties" in schema
    assert field_name in schema["properties"]
    field_schema = schema["properties"][field_name]
    assert "pattern" in field_schema
    assert field_schema["pattern"] == expected_pattern
    if expected_description:
        assert field_schema.get("description") == expected_description


def assert_range_constraint(
    schema: dict[str, Any],
    field_name: str,
    min_val: float | None = None,
    max_val: float | None = None,
    description: str | None = None,
) -> None:
    """Assert that a field has the expected range constraints."""
    assert "properties" in schema
    assert field_name in schema["properties"]
    field_schema = schema["properties"][field_name]
    if min_val is not None:
        assert field_schema.get("minimum") == min_val
    if max_val is not None:
        assert field_schema.get("maximum") == max_val
    if description:
        assert field_schema.get("description") == description


def assert_collection_constraint(
    schema: dict[str, Any],
    field_name: str,
    min_items: int | None = None,
    max_items: int | None = None,
    unique_items: bool | None = None,
) -> None:
    """Assert that a field has the expected collection constraints."""
    assert "properties" in schema
    assert field_name in schema["properties"]
    field_schema = schema["properties"][field_name]
    if min_items is not None:
        assert field_schema.get("minItems") == min_items
    if max_items is not None:
        assert field_schema.get("maxItems") == max_items
    if unique_items is not None:
        assert field_schema.get("uniqueItems") == unique_items


if __name__ == "__main__":
    pytest.main([__file__])
