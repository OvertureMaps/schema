"""Address feature models for Overture Maps addresses theme."""

from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core.base import (
    OvertureFeature,
    StrictBaseModel,
)
from overture.schema.core.geometry import (
    Geometry,
    GeometryTypeConstraint,
)
from overture.schema.validation import (
    CountryCodeConstraint,
    WhitespaceConstraint,
)


class AddressLevel(StrictBaseModel):
    """Single administrative level in address hierarchy."""

    value: Annotated[str, WhitespaceConstraint()] = Field(
        default=None,
        min_length=1,
        description="Administrative level value (no leading/trailing whitespace)",
    )


class Address(OvertureFeature):
    """Address point model with flexible administrative level structure.

    Uses a simplified schema with flexible administrative levels to capture
    worldwide address points with varying local rules and field names.
    """

    # Core

    theme: Literal["addresses"] = Field(..., description="Feature theme")
    type: Literal["address"] = Field(..., description="Feature type")
    geometry: Annotated[Geometry, GeometryTypeConstraint("Point")] = Field(
        ..., description="Geometry (Point)"
    )

    # Required

    address_levels: list[AddressLevel] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Administrative levels (1-5), ordered highest first",
    )
    country: Annotated[str, CountryCodeConstraint()] = Field(
        ..., description="ISO 3166-1 alpha-2 country code"
    )

    # Optional

    number: Annotated[str, WhitespaceConstraint()] = Field(
        default=None,
        min_length=1,
        description="House/building number (no leading/trailing whitespace)",
    )
    postal_city: Annotated[str, WhitespaceConstraint()] = Field(
        default=None,
        min_length=1,
        description="Alternative city name for mailing (no leading/trailing whitespace)",
    )
    postcode: Annotated[str, WhitespaceConstraint()] = Field(
        default=None,
        min_length=1,
        description="Postal/ZIP code (no leading/trailing whitespace)",
    )
    street: Annotated[str, WhitespaceConstraint()] = Field(
        default=None,
        min_length=1,
        description="Street name (no leading/trailing whitespace)",
    )
    unit: Annotated[str, WhitespaceConstraint()] = Field(
        default=None,
        min_length=1,
        description="Suite/apartment/floor number (no leading/trailing whitespace)",
    )
