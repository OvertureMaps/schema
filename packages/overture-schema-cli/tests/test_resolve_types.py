"""Tests for resolve_types — CLI glue between filter_models and union creation.

The combinator algebra of filter_models itself is covered in
`test_discovery_filter_models.py` in the system package.
"""

from collections.abc import Iterator
from typing import get_args
from unittest.mock import patch

import pytest
from overture.schema.cli.commands import resolve_types
from overture.schema.system.discovery import ModelKey, TagSelector

DISCOVER_MODELS = "overture.schema.cli.commands.discover_models"


# Mock model classes
class Place:
    pass


class Segment:
    pass


class Building:
    pass


BUILDING_KEY = ModelKey(
    name="building",
    entry_point="mock:Building",
    tags=frozenset({"feature", "overture", "overture:theme=buildings"}),
)
SEGMENT_KEY = ModelKey(
    name="segment",
    entry_point="mock:Segment",
    tags=frozenset({"feature", "overture", "overture:theme=transportation"}),
)
PLACE_KEY = ModelKey(
    name="place",
    entry_point="mock:Place",
    tags=frozenset({"feature", "overture", "overture:theme=places"}),
)

MOCK_MODELS = {
    BUILDING_KEY: Building,
    SEGMENT_KEY: Segment,
    PLACE_KEY: Place,
}


@pytest.fixture(autouse=True)
def _patched_discover_models() -> Iterator[None]:
    with patch(DISCOVER_MODELS, return_value=MOCK_MODELS):
        yield


def test_no_filters_returns_union_of_all() -> None:
    union = resolve_types(TagSelector())
    assert set(get_args(union)) == {Building, Segment, Place}


def test_returns_type_when_filter_matches() -> None:
    # Single match collapses to the bare class; multi-match yields a Union.
    union = resolve_types(TagSelector(include_any=("overture:theme=transportation",)))
    assert union is Segment


def test_empty_match_raises_value_error() -> None:
    with pytest.raises(ValueError, match="No models found"):
        resolve_types(TagSelector(include_any=("nonexistent",)))


def test_type_names_are_case_sensitive() -> None:
    # Lowercase matches.
    assert resolve_types(TagSelector(), type_names=("building",)) is Building
    # Uppercase doesn't.
    with pytest.raises(ValueError, match="No models found"):
        resolve_types(TagSelector(), type_names=("BUILDING",))
