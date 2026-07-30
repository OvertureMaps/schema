"""
Confidence scores for machine-generated or machine-augmented data.
"""

from typing import Annotated, NewType

from pydantic import Field

from overture.schema.system.numeric import float64

ConfidenceScore = NewType(
    "ConfidenceScore",
    Annotated[
        float64,
        Field(description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0),
    ],
)
