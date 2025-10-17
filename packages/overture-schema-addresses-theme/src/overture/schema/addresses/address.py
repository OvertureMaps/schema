"""Address feature model."""

import textwrap
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from overture.schema.core import (
    OvertureFeature,
)
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.string import CountryCodeAlpha2, StrippedString


@no_extra_fields
class AddressLevel(BaseModel):
    """
    A sub-country addressing unit, such as a region, city, or neighborhood, that is less specific
    than a street name and not a postal code.

    In the following address, the terms `Montréal` and `QC` are address levels:

    ```
    3998 Rue De Bullion, Montréal, QC H2W 2E4
    ```

    The number of address levels per address is country-dependent.

    Other addressing systems may use the terms "administrative level" or "admin level"  for the
    same concept. We have chosen the term "address level" to communicate the fact that in some
    countries and regions, address levels do not necessarily correspond to administrative units.
    """

    value: Annotated[
        StrippedString | None,
        Field(
            min_length=1,
        ),
    ] = None


class Address(OvertureFeature[Literal["addresses"], Literal["address"]]):
    """
    Addresses are structured labels for the geographic locations where businesses and individuals
    reside.

    While address formats around the world have some general points in common, the specifics vary
    extensively from place to place. The rules for dividing an address up into parts or fields vary,
    as do the names of those parts or fields.

    The address schema uses a simplified approach to capture the common structure of addresses
    worldwide while accommodating local variance. The schema is heavily based on the OpenAddresses
    (www.openaddresses.io) project.

    For sub-country administrative levels (and non-administrative levels such as neighborhoods), the
    schema provides the `address_levels` field. This is where the names of cities and towns,
    provinces, state, and regions, and similar addressing units are found.
    """

    model_config = ConfigDict(title="address")

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POINT),
        Field(description="Position of the address. Addresses are point geometries."),
    ]

    # Optional

    address_levels: Annotated[
        list[AddressLevel] | None,
        Field(
            min_length=1,
            max_length=5,
            description=textwrap.dedent("""
                Names of the sub-country addressing areas the address belongs to, including the city
                or locality, in descending order of generality.

                The list is sorted so that the highest, or most general, level comes first (*e.g.*,
                region) and the lowest, or most particular level, comes last (*e.g.*, city or town).

                The number of items in this list and their meaning is country-dependent. For
                example, in the United States, we expect two items: the state, and the locality or
                municipality within the state. Other countries might have as few as one, or even
                three or more.

                When a specific level that is required for a country is not known. most likely
                because the data provider has not supplied it and we have not derived it from
                another source, the list item corresponding to that level must be present, but its
                `value` field should be omitted.
            """).strip(),
        ),
    ] = None
    country: CountryCodeAlpha2 = Field(
        description="The country the address belongs to, as an ISO 3166-1 alpha-2 country code."
    )
    number: Annotated[
        StrippedString | None,
        Field(
            min_length=1,
            description=textwrap.dedent("""
                The house number.

                This field does not necessarily contain an integer or even a number. Values such as
                "74B", "189 1/2", and "208.5", where the non-integer or non-number part is part of
                the house number, not a unit number, are in common use.
            """).strip(),
        ),
    ] = None
    postal_city: Annotated[
        StrippedString | None,
        Field(
            min_length=1,
            description=textwrap.dedent("""
                The postal authority designated city name, if applicable.

                In some countries or regions, a mailing address may need to specify a different city
                name than the city that actually contains the address coordinates. This optional
                field can be used to specify the alternate city name to use.

                For example:

                - The postal city for the US address *716 East County Road, Winchester, Indiana*
                  is Ridgeville.
                - The postal city for the Slovenian address *Tomaj 71, 6221 Tomaj, Slovenia* is
                  Dutovlje.
            """).strip(),
        ),
    ] = None
    postcode: Annotated[
        StrippedString | None,
        Field(
            min_length=1,
            description="The postal code.",
        ),
    ] = None
    street: Annotated[
        StrippedString | None,
        Field(
            min_length=1,
            description=textwrap.dedent("""
                The street name.

                The street name can include a type (*e.g.*, "Street" or "St", "Boulevard" or "Blvd",
                *etc.*) and a directional (*e.g.*, "NW" or "Northwest", "S" or "Sud"). Both type and
                directional, if present, may be either a prefix or a suffix to the primary name.
                They may either be fully spelled-out or abbreviated.
            """).strip(),
        ),
    ] = None
    unit: Annotated[
        StrippedString | None,
        Field(
            min_length=1,
            description=textwrap.dedent("""
                The secondary address unit designator.

                In the case where the primary street address is divided into secondary units, which
                may be apartments, floors, or even buildings if the primary street address is a
                campus, this field names the specific secondary unit being addressed.
            """).strip(),
        ),
    ] = None
