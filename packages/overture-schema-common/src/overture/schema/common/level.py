"""
Z-order stacking.
"""

from typing import Annotated, NewType

from pydantic import BaseModel, Field

from overture.schema.system.numeric import int32

Level = NewType(
    "Level",
    Annotated[
        int32,
        Field(description="Z-order of the feature where 0 is visual level"),
    ],
)


class Stacked(BaseModel):
    """Properties defining feature Z-order, i.e., stacking order."""

    level: Annotated[
        Level | None,
        Field(
            description=(
                "Z-order of the feature where 0 is visual level. A feature "
                "without a level is at visual level."
            )
        ),
    ] = None
