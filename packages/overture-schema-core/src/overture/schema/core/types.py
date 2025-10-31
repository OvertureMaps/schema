from typing import Annotated, NewType

from pydantic import (
    Field,
)

from overture.schema.system.primitive import float32, int16, int32

ConfidenceScore = NewType(
    "ConfidenceScore",
    Annotated[
        float32,
        Field(description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0),
    ],
)


Level = NewType(
    "Level",
    Annotated[
        int16,
        Field(description="Z-order of the feature where 0 is visual level"),
    ],
)

FeatureVersion = NewType(
    "FeatureVersion", Annotated[int32, Field(ge=0, description="")]
)

# this is an enum in the JSON Schema, but that prevents OvertureFeature from being extended
Theme = Annotated[
    str, Field(description="Top-level Overture theme this feature belongs to")
]

# this is an enum in the JSON Schema, but that prevents OvertureFeature from being extended
Type = Annotated[str, Field(description="Specific feature type within the theme")]

__all__ = [
    "ConfidenceScore",
    "FeatureVersion",
    "Level",
    "Theme",
    "Type",
]
