"""Place feature models for Overture Maps places theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, EmailStr, Field, HttpUrl

from overture.schema.core import (
    Feature,
    StrictBaseModel,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.models import (
    Address,
    Named,
)
from overture.schema.core.types import (
    ConfidenceScore,
    PhoneNumber,
    WikidataId,
)
from overture.schema.core.validation import (
    UniqueItemsConstraint,
)

from ..types import PlaceCategory


class Categories(StrictBaseModel):
    """The categories of the place. Complete list is available on
    GitHub: https://github.com/OvertureMaps/schema/blob/main/docs/schema/concepts/by-theme/places/overture_categories.csv
    """

    # Required

    primary: Annotated[
        PlaceCategory, Field(description="The primary or main category of the place.")
    ]

    # Optional

    alternate: Annotated[
        list[PlaceCategory] | None,
        Field(
            description="""Alternate categories of the place. Some places might fit into two categories, e.g. a book store and a coffee shop. In such a case, the primary category can be augmented with additional applicable categories.""",
        ),
        UniqueItemsConstraint(),
    ] = None


class Brand(StrictBaseModel, Named):
    """The brand of the place. A location with multiple brands is modeled as multiple separate places, each with its own brand."""

    # Optional

    wikidata: WikidataId | None = None


class Place(Feature[Literal["places"], Literal["place"]], Named):
    """A Place is a point representation of a real-world facility, service, or amenity. Place features are compatible with GeoJSON Point features."""

    model_config = ConfigDict(title="place")

    # Required
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Point"),
        Field(
            description="Geometry (Point)",
        ),
    ]

    # Optional

    categories: Categories | None = None
    confidence: Annotated[
        ConfidenceScore | None,
        Field(
            description="""The confidence of the existence of the place. It's a number between 0 and 1. 0 means that we're sure that the place doesn't exist (anymore). 1 means that we're sure that the place exists. If there's no value for the confidence, it means that we don't have any confidence information.""",
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
