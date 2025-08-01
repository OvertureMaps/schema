"""Address-related models for Overture Maps features."""

from typing import Annotated

from pydantic import Field

from overture.schema.validation.constraints import WhitespaceConstraint
from overture.schema.validation.types import CountryCode, RegionCode

from .base import ExtensibleBaseModel, StrictBaseModel


class AddressLevel(StrictBaseModel):
    """Single administrative level in address hierarchy."""

    value: Annotated[str, WhitespaceConstraint()] | None = Field(
        default=None,
        min_length=1,
        description="""An address "admin level". We want to avoid the phrase "admin level" and have chosen "address level". These represent states, regions, districts, cities, neighborhoods, etc. The address schema defines several numbered levels with per-country rules indicating which parts of a country's address goes to which numbered level.""",
    )

    value: Annotated[str, WhitespaceConstraint()] | None = Field(
        default=None,
        min_length=1,
        description="""An address "admin level". We want to avoid the phrase "admin level" and have chosen "address level". These represent states, regions, districts, cities, neighborhoods, etc. The address schema defines several numbered levels with per-country rules indicating which parts of a country's address goes to which numbered level.""",
    )


class AddressContainer(ExtensibleBaseModel):
    """Address container with flexible admin levels."""

    # Optional

    freeform: str | None = Field(default=None, description="Freeform address string")
    locality: str | None = Field(default=None, description="Locality name")
    postcode: str | None = Field(default=None, description="Postal code")
    region: RegionCode | None = Field(
        default=None, description="ISO 3166-2 subdivision code"
    )
    country: CountryCode | None = Field(
        default=None, description="ISO 3166-1 alpha-2 country code"
    )
    address_levels: list[AddressLevel] | None = Field(
        default=None, min_length=1, max_length=5, description="Address levels (1-5)"
    )
    postal_city: str | None = Field(
        default=None, description="Postal city if different"
    )
