from typing import Annotated

import pytest
from pydantic import BaseModel, ValidationError

from overture.schema.system.constraint.string import (
    CountryCodeAlpha2Constraint,
    HexColorConstraint,
    JsonPointerConstraint,
    LanguageTagConstraint,
    NoWhitespaceConstraint,
    PatternConstraint,
    PhoneNumberConstraint,
    RegionCodeConstraint,
    SnakeCaseConstraint,
    StrippedConstraint,
    WikidataIdConstraint,
)


class TestStringConstraints:
    """Test all string-based constraints."""

    def test_pattern_constraint_valid(self) -> None:
        """Test PatternConstraint with valid values."""
        constraint = PatternConstraint(r"^[A-Z]{2}$", "Must be 2 uppercase letters")

        class TestModel(BaseModel):
            code: Annotated[str, constraint]

        # Valid values
        model = TestModel(code="US")
        assert model.code == "US"

        model = TestModel(code="GB")
        assert model.code == "GB"

    def test_pattern_constraint_invalid(self) -> None:
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

    def test_language_tag_constraint_valid(self) -> None:
        """Test LanguageTagConstraint with valid language tags."""

        class TestModel(BaseModel):
            language: Annotated[str, LanguageTagConstraint()]

        # Valid language tags
        valid_tags = ["en", "en-US", "en-GB", "zh-CN", "fr-CA", "es-MX"]

        for tag in valid_tags:
            model = TestModel(language=tag)
            assert model.language == tag

    def test_language_tag_constraint_invalid(self) -> None:
        """Test LanguageTagConstraint with invalid language tags."""

        class TestModel(BaseModel):
            language: Annotated[str, LanguageTagConstraint()]

        invalid_tags = ["invalid-tag-format", "123", "en_US", "toolongcode"]

        for tag in invalid_tags:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(language=tag)
            assert "Invalid IETF BCP-47 language tag" in str(exc_info.value)

    def test_country_code_constraint_valid(self) -> None:
        """Test CountryCodeAlpha2Constraint with valid ISO 3166-1 alpha-2 codes."""

        class TestModel(BaseModel):
            country: Annotated[str, CountryCodeAlpha2Constraint()]

        valid_codes = ["US", "GB", "CA", "FR", "DE", "JP", "CN", "BR"]

        for code in valid_codes:
            model = TestModel(country=code)
            assert model.country == code

    def test_country_code_constraint_invalid(self) -> None:
        """Test CountryCodeAlpha2Constraint with invalid country codes."""

        class TestModel(BaseModel):
            country: Annotated[str, CountryCodeAlpha2Constraint()]

        invalid_codes = ["USA", "123", "invalid", "gb", "us"]

        for code in invalid_codes:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(country=code)
            assert "Invalid ISO 3166-1 alpha-2 country code" in str(exc_info.value)

    def test_region_code_constraint_valid(self) -> None:
        """Test RegionCodeConstraint with valid ISO 3166-2 codes."""

        class TestModel(BaseModel):
            region: Annotated[str, RegionCodeConstraint()]

        valid_codes = ["US-CA", "GB-ENG", "CA-ON", "FR-75", "DE-BY"]

        for code in valid_codes:
            model = TestModel(region=code)
            assert model.region == code

    def test_region_code_constraint_invalid(self) -> None:
        """Test RegionCodeConstraint with invalid region codes."""

        class TestModel(BaseModel):
            region: Annotated[str, RegionCodeConstraint()]

        invalid_codes = ["US", "123-45", "invalid-region", "us-ca"]

        for code in invalid_codes:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(region=code)
            assert "Invalid ISO 3166-2 subdivision code" in str(exc_info.value)

    def test_json_pointer_constraint_valid(self) -> None:
        """Test JsonPointerConstraint with valid JSON pointers."""

        class TestModel(BaseModel):
            pointer: Annotated[str, JsonPointerConstraint()]

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

    def test_json_pointer_constraint_invalid(self) -> None:
        """Test JsonPointerConstraint with invalid JSON pointers."""

        class TestModel(BaseModel):
            pointer: Annotated[str, JsonPointerConstraint()]

        invalid_pointers = [
            "foo",  # Must start with /
            "foo/bar",  # Must start with /
        ]

        for ptr in invalid_pointers:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(pointer=ptr)
            assert "JSON Pointer must start" in str(exc_info.value)

    def test_whitespace_constraint_valid(self) -> None:
        """Test WhitespaceConstraint with valid strings (no leading/trailing
        whitespace)."""

        class TestModel(BaseModel):
            text: Annotated[str, StrippedConstraint()]

        valid_strings = [
            "hello",
            "hello world",
            "text with internal spaces",
            "",  # Empty string is valid
        ]

        for text in valid_strings:
            model = TestModel(text=text)
            assert model.text == text

    def test_whitespace_constraint_invalid(self) -> None:
        """Test WhitespaceConstraint with invalid strings (leading/trailing
        whitespace)."""

        class TestModel(BaseModel):
            text: Annotated[str, StrippedConstraint()]

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

    def test_wikidata_constraint_valid(self) -> None:
        """Test WikidataConstraint with valid Wikidata identifiers."""

        class TestModel(BaseModel):
            wikidata_id: Annotated[str, WikidataIdConstraint()]

        valid_ids = ["Q1", "Q123", "Q999999", "Q1234567890"]

        for wid in valid_ids:
            model = TestModel(wikidata_id=wid)
            assert model.wikidata_id == wid

    def test_wikidata_constraint_invalid(self) -> None:
        """Test WikidataConstraint with invalid Wikidata identifiers."""

        class TestModel(BaseModel):
            wikidata_id: Annotated[str, WikidataIdConstraint()]

        invalid_ids = [
            "q123",  # Lowercase q
            "P123",  # Property instead of item
            "Q",  # Missing number
            "123",  # Missing Q prefix
            "Q12abc",  # Non-numeric suffix
        ]

        for wid in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(wikidata_id=wid)
            assert "Invalid Wikidata identifier" in str(exc_info.value)

    def test_phone_number_constraint_valid(self) -> None:
        """Test PhoneNumberConstraint with valid international phone numbers."""

        class TestModel(BaseModel):
            phone: Annotated[str, PhoneNumberConstraint()]

        valid_phones = [
            "+1-555-123-4567",
            "+44-20-7946-0958",
            "+33-1-42-86-83-26",
            "+81-3-1234-5678",
            "+86-10-8888-8888",
        ]

        for phone in valid_phones:
            model = TestModel(phone=phone)
            assert model.phone == phone

    def test_phone_number_constraint_invalid(self) -> None:
        """Test PhoneNumberConstraint with invalid phone numbers."""

        class TestModel(BaseModel):
            phone: Annotated[str, PhoneNumberConstraint()]

        invalid_phones = [
            "555-123-4567",  # Missing country code
            "1-555-123-4567",  # Missing +
            "not-a-phone",  # Not a phone number
        ]

        for phone in invalid_phones:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(phone=phone)
            assert "Invalid phone number format" in str(exc_info.value)

    def test_hex_color_constraint_valid(self) -> None:
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

    def test_hex_color_constraint_invalid(self) -> None:
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

    def test_no_whitespace_constraint_valid(self) -> None:
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

    def test_no_whitespace_constraint_invalid(self) -> None:
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


class TestJsonSchemaGeneration:
    """Test JSON schema generation for all constraints."""

    def test_string_constraints_json_schema(self) -> None:
        """Test that string constraints generate proper JSON schema."""

        class TestModel(BaseModel):
            language: Annotated[str, LanguageTagConstraint()]
            country: Annotated[str, CountryCodeAlpha2Constraint()]
            color: Annotated[str, HexColorConstraint()]

        schema = TestModel.model_json_schema()
        props = schema["properties"]

        # Check that patterns are included
        assert "pattern" in props["language"]
        assert "pattern" in props["country"]
        assert "pattern" in props["color"]

        # Check descriptions
        assert "IETF BCP-47 language tag" in props["language"].get("description", "")


class TestErrorHandling:
    """Test error handling and validation context."""

    def test_validation_error_context(self) -> None:
        """Test that validation errors include proper context and location info."""

        class TestModel(BaseModel):
            country: Annotated[str, CountryCodeAlpha2Constraint()]

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

    def test_nested_validation_errors(self) -> None:
        """Test validation errors in nested structures."""

        class NestedModel(BaseModel):
            country: Annotated[str, CountryCodeAlpha2Constraint()]

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

    def test_snake_case_constraint_valid(self) -> None:
        """Test CategoryPatternConstraint with valid snake_case patterns."""

        class TestModel(BaseModel):
            category: Annotated[str, SnakeCaseConstraint()]

        valid_categories = [
            "restaurant",
            "gas_station",
            "shopping_mall",
            "coffee_shop",
            "bank_atm",
        ]

        for cat in valid_categories:
            model = TestModel(category=cat)
            assert model.category == cat

    def test_snake_case_constraint_invalid(self) -> None:
        """Test CategoryPatternConstraint with invalid category patterns."""

        class TestModel(BaseModel):
            category: Annotated[str, SnakeCaseConstraint()]

        invalid_categories = [
            "Restaurant",  # Capital letter
            "gas-station",  # Hyphen instead of underscore
            "shopping mall",  # Space instead of underscore
            "category!",  # Special character
        ]

        for cat in invalid_categories:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(category=cat)
            assert "Invalid category format" in str(exc_info.value)
