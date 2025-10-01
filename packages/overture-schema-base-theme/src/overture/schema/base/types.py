from typing import Annotated, Any, NewType

from pydantic import Field

from overture.schema.foundation.primitive import float64, int32

Elevation = NewType(
    "Elevation",
    Annotated[
        int32,
        Field(
            le=9000,
            description="Elevation above sea level (in meters) of the feature.",
        ),
    ],
)

Depth = NewType(
    "Depth",
    Annotated[
        int32,
        Field(
            ge=0,
            description="Depth below surface level (in meters) of the feature.",
        ),
    ],
)

Height = NewType(
    "Height",
    Annotated[float64, Field(gt=0, description="Height of the feature in meters.")],
)

SourceTags = NewType(
    "SourceTags",
    Annotated[
        dict[str, Any],
        Field(
            description="Any attributes/tags from the original source data that should be passed through."
        ),
    ],
)
