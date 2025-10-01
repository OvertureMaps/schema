"""Common type definitions using constraint-based validation."""

from typing import Annotated, NewType

from pydantic import Field

from overture.schema.foundation.primitive import float64

from .constraints import (
    CategoryPatternConstraint,
    ConfidenceScoreConstraint,
    CountryCodeConstraint,
    HexColorConstraint,
    JsonPointerConstraint,
    LanguageTagConstraint,
    NoWhitespaceConstraint,
    PhoneNumberConstraint,
    RegionCodeConstraint,
    StrippedConstraint,
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
JsonPointer = NewType("JsonPointer", Annotated[str, JsonPointerConstraint()])
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
StrippedString = NewType("StrippedString", Annotated[str, StrippedConstraint()])
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
