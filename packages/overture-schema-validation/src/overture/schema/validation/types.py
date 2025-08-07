"""Common type definitions using constraint-based validation."""

from typing import Annotated, NewType

from pydantic import Field

from overture.schema.core.primitives import float64

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
PlaceCategory = NewType("PlaceCategory", Annotated[str, CategoryPatternConstraint()])
CountryCode = NewType(
    "CountryCode",
    Annotated[
        str,
        CountryCodeConstraint(),
        Field(description="ISO 3166-1 alpha-2 country code"),
    ],
)
HexColor = NewType("HexColor", Annotated[str, HexColorConstraint()])
ISO8601DateTime = NewType(
    "ISO8601DateTime", Annotated[str, ISO8601DateTimeConstraint()]
)
JSONPointer = NewType("JSONPointer", Annotated[str, JSONPointerConstraint()])
LanguageTag = NewType("LanguageTag", Annotated[str, LanguageTagConstraint()])
NoWhitespaceString = NewType(
    "NoWhitespaceString", Annotated[str, NoWhitespaceConstraint()]
)
PhoneNumber = NewType("PhoneNumber", Annotated[str, PhoneNumberConstraint()])
RegionCode = NewType(
    "RegionCode",
    Annotated[
        str,
        RegionCodeConstraint(),
        Field(description="ISO 3166-2 principal subdivision code."),
    ],
)
TrimmedString = NewType("TrimmedString", Annotated[str, WhitespaceConstraint()])
WikidataId = NewType(
    "WikidataId",
    Annotated[
        str,
        WikidataConstraint(),
        Field(
            description="A wikidata ID if available, as found on https://www.wikidata.org/."
        ),
    ],
)

# Numeric types with constraints
ConfidenceScore = NewType(
    "ConfidenceScore",
    Annotated[
        float64,
        ConfidenceScoreConstraint(),
        Field(
            description="Confidence value from the source dataset, particularly relevant for ML-derived data."
        ),
    ],
)
