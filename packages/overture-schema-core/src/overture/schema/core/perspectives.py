"""Perspective-related models."""

from enum import Enum
from typing import Annotated

from pydantic import Field

from overture.schema.core.base import StrictBaseModel
from overture.schema.validation.constraints import UniqueItemsConstraint
from overture.schema.validation.types import CountryCode


class PerspectiveMode(str, Enum):
    """Perspective mode for disputed names."""

    ACCEPTED_BY = "accepted_by"
    DISPUTED_BY = "disputed_by"


class Perspectives(StrictBaseModel):
    """Political perspectives container."""

    # Required

    mode: PerspectiveMode = Field(..., description="Perspective mode")
    countries: Annotated[list[CountryCode], UniqueItemsConstraint()] = Field(
        ..., min_length=1, description="ISO 3166-1 alpha-2 country codes"
    )
