"""Tests for `plain_value`, the value to use when a schema value becomes text."""

from enum import Enum

import pytest

from overture.schema.system import plain_value
from overture.schema.system.doc import DocumentedEnum


class PlainKind(str, Enum):
    ROAD = "road"


class DocumentedKind(str, DocumentedEnum):
    ROAD = ("road", "A road.")


class IntKind(int, Enum):
    ONE = 1


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (PlainKind.ROAD, "road"),
        (DocumentedKind.ROAD, "road"),
        (IntKind.ONE, 1),
    ],
)
def test_unwraps_an_enum_member_to_its_value(value: Enum, expected: object) -> None:
    """A member of any enum, `DocumentedEnum` included, gives its `.value`."""
    result = plain_value(value)

    assert result == expected
    assert not isinstance(result, Enum)


@pytest.mark.parametrize("value", ["road", 3, 2.5, None, True])
def test_passes_a_non_member_through(value: object) -> None:
    """A string, number, bool or `None` comes back as the same object."""
    assert plain_value(value) is value
