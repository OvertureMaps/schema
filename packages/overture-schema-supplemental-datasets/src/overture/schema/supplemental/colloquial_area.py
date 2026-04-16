"""Colloquial Area feature type for Overture Maps Supplemental Datasets."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from overture.schema.core.names import Names
from overture.schema.core.sources import SourceItem
from overture.schema.core.types import FeatureVersion
from overture.schema.system.feature import Feature
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.string import NoWhitespaceString, WikidataId


@no_extra_fields
class ColloquialAreaProperties(BaseModel):
    """Properties specific to colloquial area features.
    
    Supplemental datasets do not use the 'theme' property since they are
    not part of the reference map themes.
    """

    # Required properties
    type: Literal["colloquial_area"] = "colloquial_area"
    version: FeatureVersion
    names: Names
    sources: list[SourceItem]

    # Optional properties
    bbox: Annotated[
        list[float] | None,
        Field(
            default=None,
            min_length=4,
            max_length=4,
            description="Bounding box as [west, south, east, north]",
        ),
    ] = None

    center_point: Annotated[
        Annotated[
            Geometry,
            GeometryTypeConstraint(GeometryType.POINT),
        ]
        | None,
        Field(
            default=None,
            description="Representative center point for labeling or geocoding",
        ),
    ] = None

    parent_name: Annotated[
        NoWhitespaceString | None,
        Field(
            default=None,
            description="Name of the parent geographic area containing this colloquial area",
        ),
    ] = None

    wikipedia_url: Annotated[
        HttpUrl | None,
        Field(
            default=None,
            description="URL to the Wikipedia article about this colloquial area",
        ),
    ] = None

    wikidata: Annotated[
        WikidataId | None,
        Field(
            default=None,
            description="Wikidata identifier for this colloquial area",
        ),
    ] = None


class ColloquialArea(Feature):
    """A colloquial area represents an informal, culturally defined, or commonly
    referenced area that does not correspond to official administrative boundaries.

    Unlike countries, states, counties, or cities whose boundaries are legally
    defined, colloquial areas evolve from cultural, historical, economic, or
    linguistic identity. These areas have no official ISO codes, no fixed
    administrative definitions, and frequently overlap existing divisions.
    They are nonetheless highly important for search, mapping, analytics, and
    user experience.

    Examples:
    - South Florida: A cultural and economic region including Miami, Fort
      Lauderdale, and West Palm Beach
    - East Asia: A macro-region comprising Japan, South Korea, China, Mongolia, etc.
    - Northern Italy: Regions north of the Po River, used in climate, economic,
      and tourism contexts

    Part of supplemental datasets—single-source datasets separate from the
    Overture reference map that follow a different release cadence and do not
    have GERS IDs. Supplemental datasets do not use the 'theme' property.
    """

    id: str
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(
            description="Area geometry must be Polygon or MultiPolygon",
        ),
    ]
    properties: ColloquialAreaProperties
