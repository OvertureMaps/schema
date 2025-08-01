"""Common type definitions using constraint-based validation."""

from typing import Annotated

from pydantic import Field

from .constraints import (
    CategoryPatternConstraint,
    ConfidenceScoreConstraint,
    CountryCodeConstraint,
    HexColorConstraint,
    ISO8601DateTimeConstraint,
    JSONPointerConstraint,
    LanguageTagConstraint,
    LinearReferenceRangeConstraint,
    NoWhitespaceConstraint,
    PhoneNumberConstraint,
    RegionCodeConstraint,
    WhitespaceConstraint,
    WikidataConstraint,
    ZoomLevelConstraint,
)

# String types with constraints
CategoryPattern = Annotated[str, CategoryPatternConstraint()]
CountryCode = Annotated[str, CountryCodeConstraint()]
HexColor = Annotated[str, HexColorConstraint()]
ISO8601DateTime = Annotated[str, ISO8601DateTimeConstraint()]
JSONPointer = Annotated[str, JSONPointerConstraint()]
LanguageTag = Annotated[str, LanguageTagConstraint()]
NoWhitespaceString = Annotated[str, NoWhitespaceConstraint()]
PhoneNumber = Annotated[str, PhoneNumberConstraint()]
RegionCode = Annotated[str, RegionCodeConstraint()]
TrimmedString = Annotated[str, WhitespaceConstraint()]
WikidataId = Annotated[str, WikidataConstraint()]

# Numeric types with constraints
ConfidenceScore = Annotated[float, ConfidenceScoreConstraint()]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]
NonNegativeInt = Annotated[int, Field(ge=0)]
ZoomLevel = Annotated[int, ZoomLevelConstraint()]

# Collection types with constraints
LinearReferenceRange = Annotated[list[float], LinearReferenceRangeConstraint()]
