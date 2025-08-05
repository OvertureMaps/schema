"""Address feature models for Overture Maps addresses theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.core import (
    Feature,
    StrictBaseModel,
)
from overture.schema.core.geometry import (
    Geometry,
    GeometryTypeConstraint,
)
from overture.schema.core.types import CountryCode, TrimmedString


class AddressLevel(StrictBaseModel):
    """An address "admin level". We want to avoid the phrase "admin level" and have chosen "address level". These represent states, regions, districts, cities, neighborhoods, etc. The address schema defines several numbered levels with per-country rules indicating which parts of a country's address goes to which numbered level."""

    value: Annotated[
        TrimmedString | None,
        Field(
            min_length=1,
        ),
    ] = None


class Address(Feature):
    """Addresses are geographic points used for locating businesses and individuals. The rules, fields, and fieldnames of an address can vary extensively between locations. We use a simplified schema to capture worldwide address points.  This initial schema is largely based on the OpenAddresses (www.openaddresses.io) project.

    The address schema allows up to 5 "admin levels". Rather than have field names that apply across all countries, we provide an array called "address_levels" containing the necessary administrative levels for an address.
    """

    model_config = ConfigDict(title="address")

    # Core

    theme: Literal["addresses"]
    type: Literal["address"]
    geometry: Annotated[
        Geometry, GeometryTypeConstraint("Point"), Field(description="Geometry (Point)")
    ]

    # Optional

    address_levels: Annotated[
        list[AddressLevel] | None,
        Field(
            min_length=1,
            max_length=5,
            description="""The administrative levels present in an address. The number of values in this list and their meaning is country-dependent. For example, in the United States we expect two values: the state and the municipality. In other countries there might be only one. Other countries could have three or more. The array is ordered with the highest levels first.

                Note: when a level is not known - most likely because the data provider has not supplied it and we have not derived it from another source, the array element container must be present, but the "value" field should be omitted""",
        ),
    ] = None
    country: CountryCode | None = None
    number: Annotated[
        TrimmedString | None,
        Field(
            min_length=1,
            description="""The house number for this address. This field may not strictly be a number. Values such as "74B", "189 1/2", "208.5" are common as the number part of an address and they are not part of the "unit" of this address.""",
        ),
    ] = None
    postal_city: Annotated[
        TrimmedString | None,
        Field(
            min_length=1,
            description="""In some countries or regions, a mailing address may need to specify a different city name than the city that actually contains the address coordinates. This optional field can be used to specify the alternate city name to use.

                Example from US National Address Database:
                716 East County Road, Winchester, Indiana has "Ridgeville" as its postal city

                Another example in Slovenia:
                Tomaj 71, 6221 Dutovlje, Slovenia""",
        ),
    ] = None
    postcode: Annotated[
        TrimmedString | None,
        Field(
            min_length=1,
            description="The postcode for the address",
        ),
    ] = None
    street: Annotated[
        TrimmedString | None,
        Field(
            min_length=1,
            description="""The street name associated with this address. The street name can include the street "type" or street suffix, e.g., Main Street. Ideally this is fully spelled out and not abbreviated but we acknowledge that many address datasets abbreviate the street name so it is acceptable.""",
        ),
    ] = None
    unit: Annotated[
        TrimmedString | None,
        Field(
            min_length=1,
            description="The suite/unit/apartment/floor number",
        ),
    ] = None
