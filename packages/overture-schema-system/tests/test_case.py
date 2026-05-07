"""Tests for PascalCase to snake_case conversion."""

import pytest

from overture.schema.system.case import to_snake_case


class TestToSnakeCase:
    """Tests for snake_case conversion helper."""

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("Building", "building"),
            ("BuildingPart", "building_part"),
            ("RoadSegment", "road_segment"),
            ("Place", "place"),
            ("simple", "simple"),
            ("HTTPServer", "http_server"),
            ("HTMLParser", "html_parser"),
        ],
    )
    def test_converts_pascal_to_snake(self, input_name: str, expected: str) -> None:
        """PascalCase names convert to snake_case; acronyms collapse."""
        assert to_snake_case(input_name) == expected
