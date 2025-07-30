"""Address-related models for Overture Maps features."""

from pydantic import Field

from overture.schema.validation.types import CountryCode, RegionCode

from .base import ExtensibleBaseModel, StrictBaseModel


class AddressLevel(StrictBaseModel):
    """Address level with optional value."""

    # Optional

    value: str = Field(default=None, description="Address level value")


class AddressContainer(ExtensibleBaseModel):
    """Address container with flexible admin levels."""

    # Optional

    freeform: str = Field(default=None, description="Freeform address string")
    locality: str = Field(default=None, description="Locality name")
    postcode: str = Field(default=None, description="Postal code")
    region: RegionCode = Field(default=None, description="ISO 3166-2 subdivision code")
    country: CountryCode = Field(
        default=None, description="ISO 3166-1 alpha-2 country code"
    )
    address_levels: list[AddressLevel] = Field(
        default=None, min_length=1, max_length=5, description="Address levels (1-5)"
    )
    postal_city: str = Field(default=None, description="Postal city if different")
