"""Tests for PascalCase to snake_case conversion."""

import pytest
from overture.schema.codegen.extraction.case_conversion import to_snake_case


class TestToSnakeCase:
    """Tests for snake_case conversion helper."""

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            ("Building", "building"),
            ("BuildingPart", "building_part"),
            ("RoadSegment", "road_segment"),
            ("Place", "place"),
            ("simple", "simple"),  # Already lowercase
            ("HTTPServer", "http_server"),  # Consecutive caps
        ],
    )
    def test_converts_pascal_to_snake(self, input_name: str, expected: str) -> None:
        """PascalCase names should convert to snake_case."""
        assert to_snake_case(input_name) == expected
