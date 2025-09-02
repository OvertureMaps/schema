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

from .constraints import (
    CategoryPatternConstraint,
    ConfidenceScoreConstraint,
    CountryCodeConstraint,
    HexColorConstraint,
    JSONPointerConstraint,
    LanguageTagConstraint,
    LinearReferenceRangeConstraint,
    NoWhitespaceConstraint,
    PatternConstraint,
    PatternPropertiesDictConstraint,
    PhoneNumberConstraint,
    RegionCodeConstraint,
    StringConstraint,
    UniqueItemsConstraint,
    WhitespaceConstraint,
    WikidataConstraint,
)
from .mixin import (
    ConstraintValidatedModel,
    allow_extension_fields,
    any_of,
    exactly_one_of,
    min_properties,
    not_required_if,
    required_if,
)

__all__ = [
    "CategoryPatternConstraint",
    "ConfidenceScoreConstraint",
    "ConstraintValidatedModel",
    "CountryCodeConstraint",
    "HexColorConstraint",
    "JSONPointerConstraint",
    "LanguageTagConstraint",
    "LinearReferenceRangeConstraint",
    "NoWhitespaceConstraint",
    "PatternConstraint",
    "PatternPropertiesDictConstraint",
    "PhoneNumberConstraint",
    "RegionCodeConstraint",
    "StringConstraint",
    "UniqueItemsConstraint",
    "WhitespaceConstraint",
    "WikidataConstraint",
    "allow_extension_fields",
    "any_of",
    "exactly_one_of",
    "min_properties",
    "not_required_if",
    "required_if",
]
