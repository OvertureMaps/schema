"""Common type definitions using constraint-based validation."""

from typing import Annotated

from pydantic import Field

from .constraints import (
    ConfidenceScoreConstraint,
    CountryCodeConstraint,
    HexColorConstraint,
    ISO8601DateTimeConstraint,
    JSONPointerConstraint,
    LanguageTagConstraint,
    LinearReferenceRangeConstraint,
    NoWhitespaceConstraint,
    RegionCodeConstraint,
    WhitespaceConstraint,
    WikidataConstraint,
    ZoomLevelConstraint,
)

# String types with constraints
LanguageTag = Annotated[str, LanguageTagConstraint()]
CountryCode = Annotated[str, CountryCodeConstraint()]
RegionCode = Annotated[str, RegionCodeConstraint()]
ISO8601DateTime = Annotated[str, ISO8601DateTimeConstraint()]
JSONPointer = Annotated[str, JSONPointerConstraint()]
TrimmedString = Annotated[str, WhitespaceConstraint()]
HexColor = Annotated[str, HexColorConstraint()]
NoWhitespaceString = Annotated[str, NoWhitespaceConstraint()]
WikidataId = Annotated[str, WikidataConstraint()]

# Numeric types with constraints
ConfidenceScore = Annotated[float, ConfidenceScoreConstraint()]
ZoomLevel = Annotated[int, ZoomLevelConstraint()]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]
NonNegativeInt = Annotated[int, Field(ge=0)]

# Collection types with constraints
LinearReferenceRange = Annotated[list[float], LinearReferenceRangeConstraint()]
