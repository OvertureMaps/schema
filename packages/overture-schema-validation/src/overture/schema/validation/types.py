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
    NoWhitespaceConstraint,
    PhoneNumberConstraint,
    RegionCodeConstraint,
    WhitespaceConstraint,
    WikidataConstraint,
)

# String types with constraints
PlaceCategory = Annotated[str, CategoryPatternConstraint()]
CountryCode = Annotated[
    str, CountryCodeConstraint(), Field(description="ISO 3166-1 alpha-2 country code")
]
HexColor = Annotated[str, HexColorConstraint()]
ISO8601DateTime = Annotated[str, ISO8601DateTimeConstraint()]
JSONPointer = Annotated[str, JSONPointerConstraint()]
LanguageTag = Annotated[str, LanguageTagConstraint()]
NoWhitespaceString = Annotated[str, NoWhitespaceConstraint()]
PhoneNumber = Annotated[str, PhoneNumberConstraint()]
RegionCode = Annotated[
    str,
    RegionCodeConstraint(),
    Field(description="ISO 3166-2 principal subdivision code."),
]
TrimmedString = Annotated[str, WhitespaceConstraint()]
WikidataId = Annotated[
    str,
    WikidataConstraint(),
    Field(
        description="A wikidata ID if available, as found on https://www.wikidata.org/."
    ),
]

# Numeric types with constraints
ConfidenceScore = Annotated[
    float,
    ConfidenceScoreConstraint(),
    Field(
        description="Confidence value from the source dataset, particularly relevant for ML-derived data."
    ),
]
