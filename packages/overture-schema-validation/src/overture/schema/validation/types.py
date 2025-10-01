"""Common type definitions using constraint-based validation."""

from typing import Annotated, NewType

from pydantic import Field

from overture.schema.foundation.primitive import float64

from .constraints import (
    CategoryPatternConstraint,
    ConfidenceScoreConstraint,
)

# String types with constraints
PlaceCategory = NewType("PlaceCategory", Annotated[str, CategoryPatternConstraint()])
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
