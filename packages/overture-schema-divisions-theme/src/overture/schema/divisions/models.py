from typing import Annotated, NewType

from pydantic import ConfigDict, Field

from overture.schema.core import StrictBaseModel
from overture.schema.core.types import Id, StrippedString
from overture.schema.divisions.enums import PlaceType

DivisionId = NewType(
    "DivisionId", Annotated[Id, Field(min_length=1, description="ID of the division")]
)


class HierarchyItem(StrictBaseModel):
    """One division in a hierarchy."""

    model_config = ConfigDict(frozen=True)

    # Required

    division_id: DivisionId
    subtype: PlaceType
    name: Annotated[
        StrippedString, Field(min_length=1, description="Primary name of the division")
    ]


class CapitalOfDivisionItem(StrictBaseModel):
    """One division that has capital."""

    model_config = ConfigDict(frozen=True)

    # Required

    division_id: DivisionId
    subtype: PlaceType
