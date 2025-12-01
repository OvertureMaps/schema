from typing import Annotated, NewType

from pydantic import BaseModel, ConfigDict, Field

from overture.schema.divisions.enums import PlaceType
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.ref import Id
from overture.schema.system.string import StrippedString

DivisionId = NewType(
    "DivisionId", Annotated[Id, Field(min_length=1, description="ID of the division")]
)


@no_extra_fields
class HierarchyItem(BaseModel):
    """One division in a hierarchy."""

    model_config = ConfigDict(frozen=True)

    # Required

    division_id: DivisionId
    subtype: PlaceType
    name: Annotated[
        StrippedString, Field(min_length=1, description="Primary name of the division")
    ]


@no_extra_fields
class CapitalOfDivisionItem(BaseModel):
    """One division that has capital."""

    model_config = ConfigDict(frozen=True)

    # Required

    division_id: DivisionId
    subtype: PlaceType
