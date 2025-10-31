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

Prominence = NewType(
    "Prominence",
    Annotated[
        int,
        Field(
            ge=1,
            lt=100,
            description="Represents Overture's view of a place's significance or importance.  This value can be used to help drive cartographic display of a place and is derived from various factors including, but not limited to: population, capital status, place tags, and type.",
        ),
    ],
)

MinZoom = NewType(
    "MinZoom",
    Annotated[
        int,
        Field(
            ge=0,
            le=23,
            description="""Recommended minimum tile zoom per the Slippy Maps convention.

The Slippy Maps zooms are explained in the following references:
- https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
- https://www.maptiler.com/google-maps-coordinates-tile-bounds-projection""",
        ),
    ],
)

MaxZoom = NewType(
    "MaxZoom",
    Annotated[
        int,
        Field(
            ge=0,
            le=23,
            description="""Recommended maximum tile zoom per the Slippy Maps convention.

The Slippy Maps zooms are explained in the following references:
- https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
- https://www.maptiler.com/google-maps-coordinates-tile-bounds-projection""",
        ),
    ],
)

SortKey = NewType(
    "SortKey",
    Annotated[
        int,
        Field(
            # default=0,
            description="An ascending numeric that defines the recommended order features should be drawn in. Features with lower number should be shown on top of features with a higher number.",
        ),
    ],
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
    "MaxZoom",
    "MinZoom",
    "Prominence",
    "SortKey",
    "Theme",
    "Type",
]
