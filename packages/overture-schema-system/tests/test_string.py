from datetime import datetime

import pytest
from pydantic import BaseModel, ValidationError

from overture.schema.system.string import (
    CountryCodeAlpha2,
    HexColor,
    JsonPointer,
    LanguageTag,
    RegionCode,
)


class TestConstrainedTypes:
    """Test the pre-defined constrained types."""

    def test_constrained_types_valid(self) -> None:
        """Test that constrained types work correctly with valid values."""

        class TestModel(BaseModel):
            language: LanguageTag
            country: CountryCodeAlpha2
            region: RegionCode
            timestamp: datetime
            pointer: JsonPointer
            color: HexColor

        model = TestModel(
            language="en-US",
            country="US",
            region="US-CA",
            timestamp="2023-10-15T10:30:00Z",
            pointer="/foo/bar",
            color="#FF0000",
        )

        assert model.language == "en-US"
        assert model.country == "US"
        assert model.region == "US-CA"
        assert model.color == "#FF0000"

    def test_constrained_types_invalid(self) -> None:
        """Test that constrained types reject invalid values."""

        class TestModel(BaseModel):
            language: LanguageTag
            country: CountryCodeAlpha2
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
