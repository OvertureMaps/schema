from typing import Annotated

import pytest
from pydantic import BaseModel, ValidationError

from overture.schema.system.field_constraint.string import (
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

PATTERN_CONSTRAINT_CASES = [
    (
        LanguageTagConstraint,
        ["en", "en-US", "en-GB", "zh-CN", "fr-CA", "es-MX"],
        ["invalid-tag-format", "123", "en_US", "toolongcode"],
        "Invalid IETF BCP-47 language tag",
    ),
    (
        CountryCodeAlpha2Constraint,
        ["US", "GB", "CA", "FR", "DE", "JP", "CN", "BR"],
        ["USA", "123", "invalid", "gb", "us"],
        "Invalid ISO 3166-1 alpha-2 country code",
    ),
    (
        RegionCodeConstraint,
        ["US-CA", "GB-ENG", "CA-ON", "FR-75", "DE-BY"],
        ["US", "123-45", "invalid-region", "us-ca"],
        "Invalid ISO 3166-2 subdivision code",
    ),
    (
        WikidataIdConstraint,
        ["Q1", "Q123", "Q999999", "Q1234567890"],
        ["q123", "P123", "Q", "123", "Q12abc"],
        "Invalid Wikidata identifier",
    ),
    (
        PhoneNumberConstraint,
        ["+1-555-123-4567", "+44-20-7946-0958", "+33-1-42-86-83-26", "+81-3-1234-5678"],
        ["555-123-4567", "1-555-123-4567", "not-a-phone"],
        "Invalid phone number format",
    ),
    (
        HexColorConstraint,
        ["#FFFFFF", "#000000", "#FF0000", "#ffffff", "#FFF", "#fff", "#ABC", "#123"],
        ["FFFFFF", "#FF", "#FFFFFFF", "#GGGGGG", "red", "#", "#FFFF"],
        "Invalid hexadecimal color format",
    ),
    (
        NoWhitespaceConstraint,
        ["hello", "identifier123", "snake_case_id", "kebab-case-id", "camelCaseId"],
        [
            "hello world",
            "id with spaces",
            "tab\tcharacter",
            "new\nline",
            "carriage\rreturn",
        ],
        "cannot contain whitespace",
    ),
    (
        SnakeCaseConstraint,
        ["restaurant", "gas_station", "shopping_mall", "coffee_shop", "bank_atm"],
        ["Restaurant", "gas-station", "shopping mall", "category!"],
        "Invalid category format",
    ),
    (
        StrippedConstraint,
        ["hello", "hello world", "text with internal spaces", ""],
        [" hello", "hello ", "\thello", "hello\n", " hello world "],
        "leading or trailing whitespace",
    ),
]


PATTERN_CONSTRAINT_IDS = [cls.__name__ for cls, *_ in PATTERN_CONSTRAINT_CASES]


class TestStringConstraints:
    """Test all string-based constraints."""

    def test_pattern_constraint_valid(self) -> None:
        """Test PatternConstraint with valid values."""
        constraint = PatternConstraint(r"^[A-Z]{2}$", "Must be 2 uppercase letters")

        class TestModel(BaseModel):
            code: Annotated[str, constraint]

        model = TestModel(code="US")
        assert model.code == "US"

        model = TestModel(code="GB")
        assert model.code == "GB"

    def test_pattern_constraint_invalid(self) -> None:
        """Test PatternConstraint with invalid values."""
        constraint = PatternConstraint(r"^[A-Z]{2}$", "Must be 2 uppercase letters")

        class TestModel(BaseModel):
            code: Annotated[str, constraint]

        with pytest.raises(ValidationError) as exc_info:
            TestModel(code="usa")
        assert "Must be 2 uppercase letters" in str(exc_info.value)

        with pytest.raises(ValidationError):
            TestModel(code="123")

    @pytest.mark.parametrize(
        "constraint_cls,valid,invalid,error_substr",
        PATTERN_CONSTRAINT_CASES,
        ids=PATTERN_CONSTRAINT_IDS,
    )
    def test_subclass_valid(
        self,
        constraint_cls: type,
        valid: list[str],
        invalid: list[str],
        error_substr: str,
    ) -> None:
        class TestModel(BaseModel):
            value: Annotated[str, constraint_cls()]

        for v in valid:
            model = TestModel(value=v)
            assert model.value == v

    @pytest.mark.parametrize(
        "constraint_cls,valid,invalid,error_substr",
        PATTERN_CONSTRAINT_CASES,
        ids=PATTERN_CONSTRAINT_IDS,
    )
    def test_subclass_invalid(
        self,
        constraint_cls: type,
        valid: list[str],
        invalid: list[str],
        error_substr: str,
    ) -> None:
        class TestModel(BaseModel):
            value: Annotated[str, constraint_cls()]

        for v in invalid:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(value=v)
            assert error_substr in str(exc_info.value)

    def test_json_pointer_constraint_valid(self) -> None:
        class TestModel(BaseModel):
            pointer: Annotated[str, JsonPointerConstraint()]

        valid_pointers = [
            "",
            "/foo",
            "/foo/bar",
            "/0",
            "/foo/0/bar",
            "/~0",
            "/~1",
        ]

        for ptr in valid_pointers:
            model = TestModel(pointer=ptr)
            assert model.pointer == ptr

    def test_json_pointer_constraint_invalid(self) -> None:
        class TestModel(BaseModel):
            pointer: Annotated[str, JsonPointerConstraint()]

        for ptr in ["foo", "foo/bar"]:
            with pytest.raises(ValidationError) as exc_info:
                TestModel(pointer=ptr)
            assert "JSON Pointer must start" in str(exc_info.value)

    def test_stripped_constraint_pattern_string(self) -> None:
        """Codegen extracts the regex via constraint.pattern.pattern."""
        assert StrippedConstraint().pattern.pattern == r"^(\S(.*\S)?)?\Z"


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

    def test_stripped_constraint_json_schema_pattern(self) -> None:
        """StrippedConstraint's JSON schema pattern accepts empty string
        and rejects leading/trailing whitespace."""
        import re

        class TestModel(BaseModel):
            text: Annotated[str, StrippedConstraint()]

        schema = TestModel.model_json_schema()
        pattern = re.compile(schema["properties"]["text"]["pattern"])

        assert pattern.match("") is not None
        assert pattern.match("a") is not None
        assert pattern.match("a b c") is not None
        assert pattern.match(" leading") is None
        assert pattern.match("trailing ") is None


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


class TestPatternConstraintHierarchy:
    """Test that pattern-based constraints extend PatternConstraint."""

    @pytest.mark.parametrize(
        "constraint_cls",
        [
            CountryCodeAlpha2Constraint,
            HexColorConstraint,
            LanguageTagConstraint,
            NoWhitespaceConstraint,
            SnakeCaseConstraint,
            PhoneNumberConstraint,
            RegionCodeConstraint,
            StrippedConstraint,
            WikidataIdConstraint,
        ],
    )
    def test_pattern_constraints_are_pattern_constraint_instances(
        self, constraint_cls: type
    ) -> None:
        assert isinstance(constraint_cls(), PatternConstraint)

    def test_pattern_constraint_with_description_kwargs(self) -> None:
        """Bare PatternConstraint with description/length kwargs emits correct JSON schema."""
        constraint = PatternConstraint(
            r"^[A-Z]{2}$",
            "Must be 2 uppercase letters",
            description="Two letter code",
            min_length=2,
            max_length=2,
        )

        class TestModel(BaseModel):
            code: Annotated[str, constraint]

        schema = TestModel.model_json_schema()
        props = schema["properties"]["code"]
        assert props["pattern"] == "^[A-Z]{2}$"
        assert props["description"] == "Two letter code"
        assert props["minLength"] == 2
        assert props["maxLength"] == 2

    def test_pattern_constraint_without_optional_kwargs(self) -> None:
        """Bare PatternConstraint without optional kwargs omits them from JSON schema."""
        constraint = PatternConstraint(r"^[A-Z]+$", "Must be uppercase")

        class TestModel(BaseModel):
            code: Annotated[str, constraint]

        schema = TestModel.model_json_schema()
        props = schema["properties"]["code"]
        assert props["pattern"] == "^[A-Z]+$"
        assert "description" not in props
        assert "minLength" not in props
        assert "maxLength" not in props
