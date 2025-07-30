"""Constraint-based validation utilities for Overture Maps schemas.

This package provides a comprehensive set of validation constraints that can be
applied to Pydantic models to enforce data quality and business rules for
Overture Maps feature data.

Key Features:
- String pattern validation (language tags, country codes, etc.)
- Collection validation (uniqueness, size constraints)
- Numeric constraints (ranges, confidence scores)
- Conditional validation (field dependencies, mutual exclusion)
- Linear referencing validation
- Composite constraint composition

Usage:
    from overture.schema.validation import (
        LanguageTagConstraint,
        CountryCodeConstraint,
        UniqueItemsConstraint,
    )
    from typing import Annotated
    from pydantic import BaseModel, Field

    class MyModel(BaseModel):
        language: Annotated[str, LanguageTagConstraint()]
        country: Annotated[str, CountryCodeConstraint()]
        tags: Annotated[list[str], UniqueItemsConstraint()]
"""

# Import all constraint classes for easy access
from .constraints import (
    BaseConstraint,
    CollectionConstraint,
    CompositeUniqueConstraint,
    ConfidenceScoreConstraint,
    CountryCodeConstraint,
    HexColorConstraint,
    ISO8601DateTimeConstraint,
    JSONPointerConstraint,
    LanguageTagConstraint,
    LinearReferenceRangeConstraint,
    MinItemsConstraint,
    NoWhitespaceConstraint,
    PatternConstraint,
    PatternPropertiesDictConstraint,
    RegionCodeConstraint,
    StringConstraint,
    UniqueItemsConstraint,
    WhitespaceConstraint,
    WikidataConstraint,
    ZoomLevelConstraint,
)
from .mixin import (
    AtLeastOneOfValidator,
    BaseConstraintValidator,
    ConstraintValidatedModel,
    ExactlyOneOfValidator,
    ExtensionPrefixValidator,
    NotRequiredIfValidator,
    RequiredIfValidator,
    allow_extension_fields,
    at_least_one_of,
    exactly_one_of,
    not_required_if,
    register_constraint,
    required_if,
)
from .types import (
    ConfidenceScore,
    CountryCode,
    HexColor,
    ISO8601DateTime,
    JSONPointer,
    LanguageTag,
    LinearReferenceRange,
    NonNegativeFloat,
    NonNegativeInt,
    NoWhitespaceString,
    RegionCode,
    TrimmedString,
    ZoomLevel,
)

__all__ = [
    "AtLeastOneOfValidator",
    "BaseConstraint",
    "BaseConstraintValidator",
    "CollectionConstraint",
    "CompositeUniqueConstraint",
    "ConfidenceScore",
    "ConfidenceScoreConstraint",
    "ConstraintValidatedModel",
    "CountryCode",
    "CountryCodeConstraint",
    "ExactlyOneOfValidator",
    "ExtensionPrefixValidator",
    "HexColor",
    "HexColorConstraint",
    "ISO8601DateTime",
    "ISO8601DateTimeConstraint",
    "JSONPointer",
    "JSONPointerConstraint",
    "LanguageTag",
    "LanguageTagConstraint",
    "LinearReferenceRange",
    "LinearReferenceRangeConstraint",
    "MinItemsConstraint",
    "NoWhitespaceConstraint",
    "NoWhitespaceString",
    "NonNegativeFloat",
    "NonNegativeInt",
    "NotRequiredIfValidator",
    "PatternConstraint",
    "PatternPropertiesDictConstraint",
    "RegionCode",
    "RegionCodeConstraint",
    "RequiredIfValidator",
    "StringConstraint",
    "TrimmedString",
    "UniqueItemsConstraint",
    "WhitespaceConstraint",
    "WikidataConstraint",
    "ZoomLevel",
    "ZoomLevelConstraint",
    "allow_extension_fields",
    "at_least_one_of",
    "exactly_one_of",
    "not_required_if",
    "register_constraint",
    "required_if",
]
