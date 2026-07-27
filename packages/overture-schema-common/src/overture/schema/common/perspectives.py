"""
Political perspectives.
"""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field

from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.string import CountryCodeAlpha2


class PerspectiveMode(str, Enum):
    """Perspective mode for disputed names."""

    ACCEPTED_BY = "accepted_by"
    DISPUTED_BY = "disputed_by"


@no_extra_fields
class Perspectives(BaseModel):
    """Political perspectives container."""

    # Required

    mode: Annotated[
        PerspectiveMode,
        Field(
            description="Whether the perspective holder accepts or disputes this name."
        ),
    ]
    countries: Annotated[
        list[CountryCodeAlpha2],
        Field(
            min_length=1, description="Countries holding the given mode of perspective."
        ),
        UniqueItemsConstraint(),
    ]
