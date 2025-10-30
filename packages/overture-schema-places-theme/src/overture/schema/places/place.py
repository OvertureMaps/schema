"""Place feature models for Overture Maps places theme."""

import textwrap
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from overture.schema.core import (
    OvertureFeature,
)
from overture.schema.core.names import (
    Named,
)
from overture.schema.core.types import (
    ConfidenceScore,
)
from overture.schema.system.field_constraint import (
    UniqueItemsConstraint,
)
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.string import (
    CountryCodeAlpha2,
    PhoneNumber,
    RegionCode,
    SnakeCaseString,
    WikidataId,
)


class OperatingStatus(str, Enum):
    """
    General indication of whether a place is: in continued operation, in a temporary operating
    hiatus, or closed permanently.

    Operating status should not be confused with opening hours or operating hours. In particular,
    the status `"open"` does not mean the place is open *right now*, it means that in general the
    place is continuing to operate normally, as opposed to being in an operating hiatus
    (`"temporarily_closed"`) or shuttered (`"permanently_closed"`).
    """

    OPEN = "open"
    PERMANENTLY_CLOSED = "permanently_closed"
    TEMPORARILY_CLOSED = "temporarily_closed"


@no_extra_fields
class Categories(BaseModel):
    """
    Categories a place belongs to.

    Complete list is available on GitHub: https://github.com/OvertureMaps/schema/blob/main/docs/schema/concepts/by-theme/places/overture_categories.csv
    """

    # Required

    primary: Annotated[
        SnakeCaseString,
        Field(description="The primary or main category of the place."),
    ]

    # Optional

    alternate: Annotated[
        list[SnakeCaseString] | None,
        Field(
            description=textwrap.dedent("""
                Alternate categories of the place.

                Some places might fit into two categories, e.g., a book store and a coffee shop. In
                these cases, the primary category can be augmented with additional categories.
            """).strip(),
        ),
        UniqueItemsConstraint(),
    ] = None


@no_extra_fields
class Brand(Named):
    """
    A brand associated with a place.

    A location with multiple brands is modeled as multiple separate places, each with its own brand.
    """

    # Optional

    wikidata: WikidataId | None = None


@no_extra_fields
class Address(BaseModel):
    """
    An address associated with a place.
    """

    # Optional

    freeform: Annotated[
        str | None,
        Field(
            description="Free-form address that contains street name, house number and other address info",
        ),
    ] = None
    locality: Annotated[
        str | None,
        Field(
            description="City, town, or neighborhood component of the place address",
        ),
    ] = None
    postcode: Annotated[
        str | None, Field(description="Postal code component of the place address")
    ] = None
    region: RegionCode | None = None
    country: CountryCodeAlpha2 | None = None


class Place(OvertureFeature[Literal["places"], Literal["place"]], Named):
    """
    Places are point representations of real-world facilities, businesses, services, or amenities.
    """

    model_config = ConfigDict(title="place")

    # Overture Feature

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POINT),
        Field(
            description="Position of the place. Places are point geometries.",
        ),
    ]

    # Required

    operating_status: Annotated[
        OperatingStatus,
        Field(
            description=textwrap.dedent("""
                An indication of whether a place is: in continued operation, in a temporary
                operating hiatus, or closed permanently.

                This is not an indication of opening hours or that the place is open/closed at the
                current time-of-day or day-of-week.

                When `operating_status` is `"permanently_closed"`, the `confidence` field will be
                set to 0.
            """).strip(),
        ),
    ]

    # Optional

    categories: Categories | None = None
    basic_category: Annotated[
        SnakeCaseString | None,
        Field(
            description=textwrap.dedent(
                """
                The basic level category of a place.

                This field classifies places into categories at a level that most people find
                intuitive. The full list of possible values it may hold can be found at (TODO).

                The basic level category, or simply basic category, is based on a cognitive science
                model use in taxonomy and ontology development. The idea is to provide the category
                name at the level of generality that is preferred by humans in learning and memory
                tasks. This category to be roughly in the middle of the general-to-specific category
                hierarchy.
                """
            ).strip()
        ),
    ] = None
    confidence: Annotated[
        ConfidenceScore | None,
        Field(
            description=textwrap.dedent(
                """
                A score between 0 and 1 indicating how confident we are that the place exists.

                A confidence score of 0 indicates that we are certain the place doesn't exist
                anymore and will always be paired with an `operating_status` of
                `"permanently_closed"`.

                A confidence score of 1 indicates that we are certain the place does exist.

                If there is no value for confidence, it means we don't have enough information on
                which to estimate our confidence level.
                """
            ).strip(),
        ),
    ] = None
    websites: Annotated[
        list[HttpUrl] | None,
        Field(min_length=1, description="The websites of the place."),
        UniqueItemsConstraint(),
    ] = None
    socials: Annotated[
        list[HttpUrl] | None,
        Field(min_length=1, description="The social media URLs of the place."),
        UniqueItemsConstraint(),
    ] = None
    emails: Annotated[
        list[EmailStr] | None,
        Field(min_length=1, description="The email addresses of the place."),
        UniqueItemsConstraint(),
    ] = None
    phones: Annotated[
        list[PhoneNumber] | None,
        Field(min_length=1, description="The phone numbers of the place."),
        UniqueItemsConstraint(),
    ] = None
    brand: Annotated[
        Brand | None, Field(description="The brand associated with the place.")
    ] = None
    addresses: Annotated[
        list[Address] | None,
        Field(min_length=1, description="The address or addresses of the place"),
    ] = None
