"""Place feature models for Overture Maps places theme."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from overture.schema.core import (
    OvertureFeature,
)
from overture.schema.core.models import (
    Address,
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
from overture.schema.system.string import PhoneNumber, WikidataId

from ..types import SnakeCaseString
from .enums import OperatingStatus


@no_extra_fields
class Categories(BaseModel):
    """The categories of the place.

    Complete list is available on
    GitHub: https://github.com/OvertureMaps/schema/blob/main/docs/schema/concepts/by-theme/places/overture_categories.csv
    """

    # Required

    primary: Annotated[
        SnakeCaseString,
        Field(
            description="The primary or main category of the place. This can be empty."
        ),
    ]

    # Optional

    alternate: Annotated[
        list[SnakeCaseString] | None,
        Field(
            description="""Alternate categories of the place. Some places might fit into two categories, e.g. a book store and a coffee shop. In such a case, the primary category can be augmented with additional applicable categories.""",
        ),
        UniqueItemsConstraint(),
    ] = None


@no_extra_fields
class Brand(Named):
    """The brand of the place.

    A location with multiple brands is modeled as multiple separate places, each with
    its own brand.
    """

    # Optional

    wikidata: WikidataId | None = None


class Place(OvertureFeature[Literal["places"], Literal["place"]], Named):
    """A Place is a point representation of a real-world facility, service, or amenity.

    Place features are compatible with GeoJSON Point features.
    """

    model_config = ConfigDict(title="place")

    # Required
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POINT),
        Field(
            description="Position of the place",
        ),
    ]
    operating_status: Annotated[
        OperatingStatus,
        Field(
            description="""Indicates the operating status of a place, can be one of ["open", "permanently_closed", "temporarily_closed"].
This is not an indication of 'opening hours' or that the place is open/closed at the current time-of-day or day-of-week.""",
        ),
    ]

    # Optional

    categories: Categories | None = None
    basic_category: Annotated[
        SnakeCaseString | None,
        Field(
            description="""The basic level category of a place. At present this is a mapping of the categories.primary entry to a new, simplified name. This mapping can be 1:1 or M:1 from the existing primary.categories entry. If the entry is currently empty in categories.primary, this entry will be empty.  This type of categorization is a cognitive science model that is relevant for taxonomy and ontology development that shows the most broadest and general category name that is most often found in the middle of a general-to-specific hierarchy, with generalization proceeding upward and specialization proceeding downward.  The full list of basic level categories is available at:(todo)"""
        ),
    ] = None
    confidence: Annotated[
        ConfidenceScore | None,
        Field(
            description="""The confidence of the existence of the place. It's a number between 0 and 1. 0 means that we're sure that the place doesn't exist (anymore). 1 means that we're sure that the place exists. If there's no value for the confidence, it means that we don't have any confidence information. Places with operating_status set to 'closed' will have a confidence score of 0""",
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
    brand: Brand | None = None
    addresses: Annotated[list[Address] | None, Field(min_length=1)] = None
