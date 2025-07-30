"""Comprehensive tests for constraint-based validation in overture-schema-validation package."""

from typing import Annotated

import pytest
from pydantic import BaseModel, Field, ValidationError

from overture.schema.validation import (
    CompositeUniqueConstraint,
    ConfidenceScore,
    ConfidenceScoreConstraint,
    CountryCode,
    CountryCodeConstraint,
    HexColor,
    HexColorConstraint,
    ISO8601DateTime,
    ISO8601DateTimeConstraint,
    JSONPointer,
    JSONPointerConstraint,
    LanguageTag,
    LanguageTagConstraint,
    LinearReferenceRange,
    LinearReferenceRangeConstraint,
    MinItemsConstraint,
    NonNegativeFloat,
    NonNegativeInt,
    NoWhitespaceConstraint,
    PatternConstraint,
    RegionCode,
    RegionCodeConstraint,
    UniqueItemsConstraint,
    WhitespaceConstraint,
    ZoomLevel,
    ZoomLevelConstraint,
)


class TestStringConstraints:
    """Test all string-based constraints."""

    def test_pattern_constraint_valid(self):
        """Test PatternConstraint with valid values."""
        constraint = PatternConstraint(r"^[A-Z]{2}$", "Must be 2 uppercase letters")

        class TestModel(BaseModel):
            code: Annotated[str, constraint]

        # Valid values
        model = TestModel(code="US")
        assert model.code == "US"

        model = TestModel(code="GB")
        assert model.code == "GB"

    def test_pattern_constraint_invalid(self):
        """Test PatternConstraint with invalid values."""
        constraint = PatternConstraint(r"^[A-Z]{2}$", "Must be 2 uppercase letters")

        class TestModel(BaseModel):
            code: Annotated[str, constraint]

        # Invalid values
        with pytest.raises(ValidationError) as exc_info:
            TestModel(code="usa")
        assert "Must be 2 uppercase letters" in str(exc_info.value)

        with pytest.raises(ValidationError):
            TestModel(code="123")

    def test_language_tag_constraint_valid(self):
        """Test LanguageTagConstraint with valid language tags."""

        class TestModel(BaseModel):
            language: Annotated[str, LanguageTagConstraint()]

        # Valid language tags
        valid_tags = ["en", "en-US", "en-GB", "zh-CN", "fr-CA", "es-MX"]

        for tag in valid_tags:
            model = TestModel(language=tag)
            assert model.language == tag

    def test_language_tag_constraint_invalid(self):
        """Test LanguageTagConstraint with invalid language tags."""

        class TestModel(BaseModel):
            language: Annotated[str, LanguageTagConstraint()]

        invalid_tags = ["invalid-tag-format", "123", "en_US", "toolongcode"]

        for tag in invalid_tags:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(language=tag)
            assert "Invalid IETF BCP-47 language tag" in str(exc_info.value)

    def test_country_code_constraint_valid(self):
        """Test CountryCodeConstraint with valid ISO 3166-1 alpha-2 codes."""

        class TestModel(BaseModel):
            country: Annotated[str, CountryCodeConstraint()]

        valid_codes = ["US", "GB", "CA", "FR", "DE", "JP", "CN", "BR"]

        for code in valid_codes:
            model = TestModel(country=code)
            assert model.country == code

    def test_country_code_constraint_invalid(self):
        """Test CountryCodeConstraint with invalid country codes."""

        class TestModel(BaseModel):
            country: Annotated[str, CountryCodeConstraint()]

        invalid_codes = ["USA", "123", "invalid", "gb", "us"]

        for code in invalid_codes:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(country=code)
            assert "Invalid ISO 3166-1 alpha-2 country code" in str(exc_info.value)

    def test_region_code_constraint_valid(self):
        """Test RegionCodeConstraint with valid ISO 3166-2 codes."""

        class TestModel(BaseModel):
            region: Annotated[str, RegionCodeConstraint()]

        valid_codes = ["US-CA", "GB-ENG", "CA-ON", "FR-75", "DE-BY"]

        for code in valid_codes:
            model = TestModel(region=code)
            assert model.region == code

    def test_region_code_constraint_invalid(self):
        """Test RegionCodeConstraint with invalid region codes."""

        class TestModel(BaseModel):
            region: Annotated[str, RegionCodeConstraint()]

        invalid_codes = ["US", "123-45", "invalid-region", "us-ca"]

        for code in invalid_codes:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(region=code)
            assert "Invalid ISO 3166-2 subdivision code" in str(exc_info.value)

    def test_iso8601_datetime_constraint_valid(self):
        """Test ISO8601DateTimeConstraint with valid datetime strings."""

        class TestModel(BaseModel):
            timestamp: Annotated[str, ISO8601DateTimeConstraint()]

        valid_datetimes = [
            "2023-10-15T10:30:00Z",
            "2023-12-25T00:00:00+00:00",
            "2024-01-01T12:00:00-05:00",
            "2023-06-15T14:30:00.123Z",
        ]

        for dt in valid_datetimes:
            model = TestModel(timestamp=dt)
            assert model.timestamp == dt

    def test_iso8601_datetime_constraint_invalid(self):
        """Test ISO8601DateTimeConstraint with invalid datetime strings."""

        class TestModel(BaseModel):
            timestamp: Annotated[str, ISO8601DateTimeConstraint()]

        invalid_datetimes = [
            "not-a-timestamp",
            "2023-13-01T10:30:00Z",  # Invalid month
            "2023-10-32T10:30:00Z",  # Invalid day
            "2023-10-15 10:30:00",  # Missing T separator
            "2023/10/15T10:30:00Z",  # Wrong date separator
        ]

        for dt in invalid_datetimes:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(timestamp=dt)
            assert "Invalid ISO 8601 datetime" in str(exc_info.value)

    def test_json_pointer_constraint_valid(self):
        """Test JSONPointerConstraint with valid JSON pointers."""

        class TestModel(BaseModel):
            pointer: Annotated[str, JSONPointerConstraint()]

        valid_pointers = [
            "",
            "/foo",
            "/foo/bar",
            "/0",
            "/foo/0/bar",
            "/~0",  # Represents ~
            "/~1",  # Represents /
        ]

        for ptr in valid_pointers:
            model = TestModel(pointer=ptr)
            assert model.pointer == ptr

    def test_json_pointer_constraint_invalid(self):
        """Test JSONPointerConstraint with invalid JSON pointers."""

        class TestModel(BaseModel):
            pointer: Annotated[str, JSONPointerConstraint()]

        invalid_pointers = [
            "foo",  # Must start with /
            "foo/bar",  # Must start with /
        ]

        for ptr in invalid_pointers:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(pointer=ptr)
            assert "JSON Pointer must start" in str(exc_info.value)

    def test_whitespace_constraint_valid(self):
        """Test WhitespaceConstraint with valid strings (no leading/trailing whitespace)."""

        class TestModel(BaseModel):
            text: Annotated[str, WhitespaceConstraint()]

        valid_strings = [
            "hello",
            "hello world",
            "text with internal spaces",
            "",  # Empty string is valid
        ]

        for text in valid_strings:
            model = TestModel(text=text)
            assert model.text == text

    def test_whitespace_constraint_invalid(self):
        """Test WhitespaceConstraint with invalid strings (leading/trailing whitespace)."""

        class TestModel(BaseModel):
            text: Annotated[str, WhitespaceConstraint()]

        invalid_strings = [
            " hello",  # Leading space
            "hello ",  # Trailing space
            "\thello",  # Leading tab
            "hello\n",  # Trailing newline
            " hello world ",  # Both leading and trailing
        ]

        for text in invalid_strings:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(text=text)
            assert "cannot have leading or trailing whitespace" in str(exc_info.value)

    def test_hex_color_constraint_valid(self):
        """Test HexColorConstraint with valid hex colors."""

        class TestModel(BaseModel):
            color: Annotated[str, HexColorConstraint()]

        valid_colors = [
            "#FFFFFF",
            "#000000",
            "#FF0000",
            "#00FF00",
            "#0000FF",
            "#ABCDEF",
            "#123456",
            "#ffffff",  # lowercase
            "#abcdef",  # lowercase
            "#FFF",  # 3-character uppercase
            "#fff",  # 3-character lowercase
            "#ABC",  # 3-character mixed case
            "#123",  # 3-character numbers
        ]

        for color in valid_colors:
            model = TestModel(color=color)
            assert model.color == color

    def test_hex_color_constraint_invalid(self):
        """Test HexColorConstraint with invalid hex colors."""

        class TestModel(BaseModel):
            color: Annotated[str, HexColorConstraint()]

        invalid_colors = [
            "FFFFFF",  # Missing #
            "#FF",  # Too short (2 chars)
            "#FFFFFFF",  # Too long (7 chars)
            "#GGGGGG",  # Invalid hex characters
            "red",  # Not hex
            "#",  # Just hash
            "#FFFF",  # Invalid length (4 chars)
        ]

        for color in invalid_colors:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(color=color)
            # Just check that validation fails - message may vary
            assert len(exc_info.value.errors()) > 0

    def test_no_whitespace_constraint_valid(self):
        """Test NoWhitespaceConstraint with valid strings (no whitespace)."""

        class TestModel(BaseModel):
            identifier: Annotated[str, NoWhitespaceConstraint()]

        valid_identifiers = [
            "hello",
            "identifier123",
            "snake_case_id",
            "kebab-case-id",
            "camelCaseId",
        ]

        for ident in valid_identifiers:
            model = TestModel(identifier=ident)
            assert model.identifier == ident

    def test_no_whitespace_constraint_invalid(self):
        """Test NoWhitespaceConstraint with invalid strings (containing whitespace)."""

        class TestModel(BaseModel):
            identifier: Annotated[str, NoWhitespaceConstraint()]

        invalid_identifiers = [
            "hello world",
            "id with spaces",
            "tab\tcharacter",
            "new\nline",
            "carriage\rreturn",
        ]

        for ident in invalid_identifiers:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(identifier=ident)
            # Just check that validation fails - message may vary
            assert len(exc_info.value.errors()) > 0


class TestCollectionConstraints:
    """Test all collection-based constraints."""

    def test_unique_items_constraint_valid(self):
        """Test UniqueItemsConstraint with unique items."""

        class TestModel(BaseModel):
            tags: Annotated[list[str], UniqueItemsConstraint()]

        valid_lists = [
            [],
            ["a"],
            ["a", "b", "c"],
            ["unique", "items", "only"],
        ]

        for items in valid_lists:
            model = TestModel(tags=items)
            assert model.tags == items

    def test_unique_items_constraint_invalid(self):
        """Test UniqueItemsConstraint with duplicate items."""

        class TestModel(BaseModel):
            tags: Annotated[list[str], UniqueItemsConstraint()]

        invalid_lists = [
            ["a", "a"],
            ["a", "b", "a"],
            ["duplicate", "values", "duplicate"],
        ]

        for items in invalid_lists:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(tags=items)
            assert "All items must be unique" in str(exc_info.value)

    def test_min_items_constraint_valid(self):
        """Test MinItemsConstraint with valid item counts."""

        class TestModel(BaseModel):
            items: Annotated[list[str], MinItemsConstraint(2)]

        valid_lists = [
            ["a", "b"],
            ["a", "b", "c"],
            ["a", "b", "c", "d", "e"],
        ]

        for items in valid_lists:
            model = TestModel(items=items)
            assert model.items == items

    def test_min_items_constraint_invalid(self):
        """Test MinItemsConstraint with too few items."""

        class TestModel(BaseModel):
            items: Annotated[list[str], MinItemsConstraint(2)]

        invalid_lists = [
            [],
            ["a"],
        ]

        for items in invalid_lists:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(items=items)
            assert "too few items" in str(exc_info.value)

    def test_composite_unique_constraint_valid(self):
        """Test CompositeUniqueConstraint with unique composite keys."""

        class Item(BaseModel):
            category: str
            name: str
            value: int

        class TestModel(BaseModel):
            items: Annotated[list[Item], CompositeUniqueConstraint("category", "name")]

        valid_items = [
            [],
            [Item(category="food", name="apple", value=1)],
            [
                Item(category="food", name="apple", value=1),
                Item(category="food", name="banana", value=2),  # Different name
                Item(category="drink", name="apple", value=3),  # Different category
            ],
        ]

        for items in valid_items:
            model = TestModel(items=items)
            assert model.items == items

    def test_composite_unique_constraint_invalid(self):
        """Test CompositeUniqueConstraint with duplicate composite keys."""

        class Item(BaseModel):
            category: str
            name: str
            value: int

        class TestModel(BaseModel):
            items: Annotated[list[Item], CompositeUniqueConstraint("category", "name")]

        # Items with same category and name (duplicate composite key)
        duplicate_items = [
            Item(category="food", name="apple", value=1),
            Item(
                category="food", name="apple", value=2
            ),  # Same category+name, different value
        ]

        with pytest.raises(ValidationError) as exc_info:
            TestModel(items=duplicate_items)
        assert "Items must be unique based on (category, name)" in str(exc_info.value)


class TestNumericConstraints:
    """Test all numeric constraints."""

    def test_confidence_score_constraint_valid(self):
        """Test ConfidenceScoreConstraint with valid scores (0.0 to 1.0)."""

        class TestModel(BaseModel):
            confidence: Annotated[float, ConfidenceScoreConstraint()]

        valid_scores = [0.0, 0.1, 0.5, 0.9, 1.0, 0.123456]

        for score in valid_scores:
            model = TestModel(confidence=score)
            assert model.confidence == score

    def test_confidence_score_constraint_invalid(self):
        """Test ConfidenceScoreConstraint with invalid scores."""

        class TestModel(BaseModel):
            confidence: Annotated[float, ConfidenceScoreConstraint()]

        invalid_scores = [-0.1, 1.1, 2.0, -1.0, 10.0]

        for score in invalid_scores:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(confidence=score)
            # Check for Pydantic's built-in error messages
            assert "greater than or equal to 0" in str(
                exc_info.value
            ) or "less than or equal to 1" in str(exc_info.value)

    def test_zoom_level_constraint_valid(self):
        """Test ZoomLevelConstraint with valid zoom levels (0 to 23)."""

        class TestModel(BaseModel):
            zoom: Annotated[int, ZoomLevelConstraint()]

        valid_zooms = [0, 1, 10, 15, 20, 23]

        for zoom in valid_zooms:
            model = TestModel(zoom=zoom)
            assert model.zoom == zoom

    def test_zoom_level_constraint_invalid(self):
        """Test ZoomLevelConstraint with invalid zoom levels."""

        class TestModel(BaseModel):
            zoom: Annotated[int, ZoomLevelConstraint()]

        invalid_zooms = [-1, 24, 25, 100, -10]

        for zoom in invalid_zooms:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(zoom=zoom)
            # Check for Pydantic's built-in error messages
            assert "greater than or equal to 0" in str(
                exc_info.value
            ) or "less than or equal to 23" in str(exc_info.value)

    def test_non_negative_constraint_valid(self):
        """Test NonNegativeConstraint with valid non-negative numbers."""

        class TestModel(BaseModel):
            value: NonNegativeFloat

        valid_values = [0.0, 0.1, 1.0, 100.0, 999.99]

        for val in valid_values:
            model = TestModel(value=val)
            assert model.value == val

    def test_non_negative_constraint_invalid(self):
        """Test NonNegativeConstraint with invalid negative numbers."""

        class TestModel(BaseModel):
            value: NonNegativeFloat

        invalid_values = [-0.1, -1.0, -100.0, -999.99]

        for val in invalid_values:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(value=val)
            # Check for Pydantic's built-in error message
            assert "greater than or equal to 0" in str(exc_info.value)


class TestSpecializedConstraints:
    """Test specialized constraints."""

    def test_linear_reference_range_constraint_valid(self):
        """Test LinearReferenceRangeConstraint with valid ranges."""

        class TestModel(BaseModel):
            range_val: Annotated[list[float], LinearReferenceRangeConstraint()]

        valid_ranges = [
            [0.0, 1.0],
            [0.1, 0.9],
            [0.0, 0.5],
            [0.25, 0.75],
        ]

        for range_val in valid_ranges:
            model = TestModel(range_val=range_val)
            assert model.range_val == range_val

    def test_linear_reference_range_constraint_invalid(self):
        """Test LinearReferenceRangeConstraint with invalid ranges."""

        class TestModel(BaseModel):
            range_val: Annotated[list[float], LinearReferenceRangeConstraint()]

        invalid_ranges = [
            [0.9, 0.1],  # start > end
            [-0.1, 0.5],  # start < 0
            [0.5, 1.1],  # end > 1
            [0.5, 0.5],  # start == end
            [0.0],  # Wrong length
            [0.0, 0.5, 1.0],  # Wrong length
        ]

        for range_val in invalid_ranges:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(range_val=range_val)
            # Check that validation fails with appropriate error
            assert len(exc_info.value.errors()) > 0


class TestConstrainedTypes:
    """Test the pre-defined constrained types."""

    def test_constrained_types_valid(self):
        """Test that constrained types work correctly with valid values."""

        class TestModel(BaseModel):
            language: LanguageTag
            country: CountryCode
            region: RegionCode
            timestamp: ISO8601DateTime
            pointer: JSONPointer
            range_val: LinearReferenceRange
            confidence: ConfidenceScore
            zoom: ZoomLevel
            non_neg_float: NonNegativeFloat
            non_neg_int: NonNegativeInt
            color: HexColor

        model = TestModel(
            language="en-US",
            country="US",
            region="US-CA",
            timestamp="2023-10-15T10:30:00Z",
            pointer="/foo/bar",
            range_val=[0.1, 0.9],
            confidence=0.95,
            zoom=15,
            non_neg_float=123.45,
            non_neg_int=42,
            color="#FF0000",
        )

        assert model.language == "en-US"
        assert model.country == "US"
        assert model.region == "US-CA"
        assert model.confidence == 0.95
        assert model.zoom == 15
        assert model.color == "#FF0000"

    def test_constrained_types_invalid(self):
        """Test that constrained types reject invalid values."""

        class TestModel(BaseModel):
            language: LanguageTag
            country: CountryCode
            color: HexColor

        # Test invalid language tag
        with pytest.raises(ValidationError):
            TestModel(language="invalid-tag-format", country="US", color="#FF0000")

        # Test invalid country code
        with pytest.raises(ValidationError):
            TestModel(language="en-US", country="invalid", color="#FF0000")

        # Test invalid color
        with pytest.raises(ValidationError):
            TestModel(language="en-US", country="US", color="not-a-color")


class TestJSONSchemaGeneration:
    """Test JSON schema generation for all constraints."""

    def test_string_constraints_json_schema(self):
        """Test that string constraints generate proper JSON schema."""

        class TestModel(BaseModel):
            language: Annotated[str, LanguageTagConstraint()]
            country: Annotated[str, CountryCodeConstraint()]
            color: Annotated[str, HexColorConstraint()]

        schema = TestModel.model_json_schema()
        props = schema["properties"]

        # Check that patterns are included
        assert "pattern" in props["language"]
        assert "pattern" in props["country"]
        assert "pattern" in props["color"]

        # Check descriptions
        assert "IETF BCP-47 language tag" in props["language"].get("description", "")

    def test_collection_constraints_json_schema(self):
        """Test that collection constraints generate proper JSON schema."""

        class TestModel(BaseModel):
            unique_items: Annotated[list[str], UniqueItemsConstraint()]
            min_items: Annotated[list[str], MinItemsConstraint(2)]
            max_items: list[str] = Field(..., max_length=5)

        schema = TestModel.model_json_schema()
        props = schema["properties"]

        # Check collection constraints
        assert props["unique_items"].get("uniqueItems") is True
        assert props["min_items"].get("minItems") == 2
        assert props["max_items"].get("maxItems") == 5

    def test_numeric_constraints_json_schema(self):
        """Test that numeric constraints generate proper JSON schema."""

        class TestModel(BaseModel):
            confidence: Annotated[float, ConfidenceScoreConstraint()]
            zoom: Annotated[int, ZoomLevelConstraint()]
            non_negative: NonNegativeFloat

        schema = TestModel.model_json_schema()
        props = schema["properties"]

        # Check numeric bounds
        assert props["confidence"].get("minimum") == 0.0
        assert props["confidence"].get("maximum") == 1.0
        assert props["zoom"].get("minimum") == 0
        assert props["zoom"].get("maximum") == 23
        assert props["non_negative"].get("minimum") == 0.0


class TestErrorHandling:
    """Test error handling and validation context."""

    def test_validation_error_context(self):
        """Test that validation errors include proper context and location info."""

        class TestModel(BaseModel):
            country: Annotated[str, CountryCodeConstraint()]

        with pytest.raises(ValidationError) as exc_info:
            TestModel(country="invalid")

        error = exc_info.value
        assert error.error_count() == 1

        error_detail = error.errors()[0]
        assert error_detail["type"] == "value_error"
        assert error_detail["input"] == "invalid"
        assert "Invalid ISO 3166-1 alpha-2 country code" in str(
            error_detail["ctx"]["error"]
        )

    def test_nested_validation_errors(self):
        """Test validation errors in nested structures."""

        class NestedModel(BaseModel):
            country: Annotated[str, CountryCodeConstraint()]

        class TestModel(BaseModel):
            nested: NestedModel
            items: list[NestedModel]

        # Test nested object error
        with pytest.raises(ValidationError) as exc_info:
            TestModel(nested=NestedModel(country="invalid"), items=[])

        error = exc_info.value
        assert error.error_count() >= 1

        # Test nested array error
        with pytest.raises(ValidationError) as exc_info:
            TestModel(
                nested=NestedModel(country="US"), items=[NestedModel(country="invalid")]
            )

        error = exc_info.value
        assert error.error_count() >= 1
