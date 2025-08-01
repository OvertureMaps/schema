"""Place feature models for Overture Maps places theme."""

import re
from typing import Annotated, Literal

from pydantic import AnyUrl, EmailStr, Field

from overture.schema.core.addresses import (
    AddressContainer,
)
from overture.schema.core.base import (
    OvertureFeature,
    StrictBaseModel,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.names import (
    NamesContainer,
)
from overture.schema.validation import (
    PatternConstraint,
    UniqueItemsConstraint,
)
from overture.schema.validation.types import (
    CategoryPattern,
    ConfidenceScore,
    PhoneNumber,
    WikidataId,
)


class Categories(StrictBaseModel):
    """Place categories with primary and alternate classification."""

    # Required

    primary: CategoryPattern = Field(..., description="Primary category (required)")

    # Optional

    alternate: Annotated[list[CategoryPattern], UniqueItemsConstraint()] | None = Field(
        default=None, min_length=1, description="Alternate categories"
    )


class Brand(StrictBaseModel):
    """Brand information for places."""

    # Required

    names: NamesContainer = Field(..., description="Multilingual brand names")

    # Optional

    wikidata: WikidataId | None = Field(default=None, description="Wikidata identifier")


class Contact(StrictBaseModel):
    """Contact information for places."""

    # Optional

    email: EmailStr | None = Field(default=None, description="Email address")
    phone: PhoneNumber | None = Field(
        default=None,
        description="Phone number in international format",
    )
    social_media: dict[str, AnyUrl] | None = Field(
        default=None, description="Social media profiles"
    )
    website: AnyUrl | None = Field(default=None, description="Website URL")


# Hours format constraint
HoursFormat = Annotated[
    str,
    PatternConstraint(
        r"^(\d{2}:\d{2}-\d{2}:\d{2}|closed|24/7|24 hours)$",
        "Hours must be in format 'HH:MM-HH:MM' or 'closed' or '24/7'",
        re.IGNORECASE,
    ),
]


class OperatingHours(StrictBaseModel):
    """Operating hours for places."""

    # Optional

    monday: HoursFormat | None = Field(default=None, description="Monday hours")
    tuesday: HoursFormat | None = Field(default=None, description="Tuesday hours")
    wednesday: HoursFormat | None = Field(default=None, description="Wednesday hours")
    thursday: HoursFormat | None = Field(default=None, description="Thursday hours")
    friday: HoursFormat | None = Field(default=None, description="Friday hours")
    saturday: HoursFormat | None = Field(default=None, description="Saturday hours")
    sunday: HoursFormat | None = Field(default=None, description="Sunday hours")


class Confidence(StrictBaseModel):
    """Confidence scores for place data."""

    # Optional

    overall: ConfidenceScore | None = Field(
        default=None, description="Overall confidence"
    )
    location: ConfidenceScore | None = Field(
        default=None, description="Location confidence"
    )
    name: ConfidenceScore | None = Field(default=None, description="Name confidence")
    categories: ConfidenceScore | None = Field(
        default=None, description="Categories confidence"
    )


class Place(OvertureFeature):
    """Point model for real-world facilities, services, and amenities.

    Represents places of interest with category classifications, contact
    information, and confidence scores for data quality assessment.
    """

    # Required

    theme: Literal["places"] = Field(..., description="Feature theme")
    type: Literal["place"] = Field(..., description="Feature type")
    geometry: Annotated[Geometry, GeometryTypeConstraint("Point")] = Field(
        ..., description="Geometry (Point)"
    )

    # Optional

    addresses: list[AddressContainer] | None = Field(
        default=None, min_length=1, description="Place addresses"
    )
    brand: Brand | None = Field(default=None, description="Brand information")
    categories: Categories | None = Field(default=None, description="Place categories")
    confidence: ConfidenceScore | None = Field(
        default=None, description="Confidence score (0.0-1.0)"
    )
    names: NamesContainer | None = Field(default=None, description="Multilingual names")
    emails: Annotated[list[EmailStr], UniqueItemsConstraint()] | None = Field(
        default=None, min_length=1, description="Email addresses"
    )
    phones: Annotated[list[PhoneNumber], UniqueItemsConstraint()] | None = Field(
        default=None, min_length=1, description="Phone numbers"
    )
    socials: Annotated[list[str], UniqueItemsConstraint()] | None = Field(
        default=None, min_length=1, description="Social media URLs"
    )
    websites: Annotated[list[str], UniqueItemsConstraint()] | None = Field(
        default=None, min_length=1, description="Website URLs"
    )
