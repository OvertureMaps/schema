"""Water feature models for Overture Maps base theme."""

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import Field

from overture.schema.core.base import (
    OvertureFeature,
)
from overture.schema.core.geometry import Geometry, GeometryTypeConstraint
from overture.schema.core.names import (
    NamesContainer,
)
from overture.schema.validation.types import WikidataId


class WaterSubtype(str, Enum):
    """Water subtype classification."""

    CANAL = "canal"
    HUMAN_MADE = "human_made"
    LAKE = "lake"
    OCEAN = "ocean"
    PHYSICAL = "physical"
    POND = "pond"
    RESERVOIR = "reservoir"
    RIVER = "river"
    SPRING = "spring"
    STREAM = "stream"
    WASTEWATER = "wastewater"
    WATER = "water"


class WaterClass(str, Enum):
    """Water class classification."""

    BASIN = "basin"
    BAY = "bay"
    BLOWHOLE = "blowhole"
    CANAL = "canal"
    CAPE = "cape"
    DITCH = "ditch"
    DOCK = "dock"
    DRAIN = "drain"
    FAIRWAY = "fairway"
    FISH_PASS = "fish_pass"
    FISHPOND = "fishpond"
    GEYSER = "geyser"
    HOT_SPRING = "hot_spring"
    LAGOON = "lagoon"
    LAKE = "lake"
    MOAT = "moat"
    OCEAN = "ocean"
    OXBOW = "oxbow"
    POND = "pond"
    REFLECTING_POOL = "reflecting_pool"
    RESERVOIR = "reservoir"
    RIVER = "river"
    SALT_POND = "salt_pond"
    SEA = "sea"
    SEWAGE = "sewage"
    SHOAL = "shoal"
    SPRING = "spring"
    STRAIT = "strait"
    STREAM = "stream"
    SWIMMING_POOL = "swimming_pool"
    TIDAL_CHANNEL = "tidal_channel"
    WASTEWATER = "wastewater"
    WATER = "water"
    WATER_STORAGE = "water_storage"
    WATERFALL = "waterfall"


class Water(OvertureFeature):
    """Water body feature model representing aquatic surfaces and waterways.

    Models diverse water features including rivers, lakes, oceans, streams,
    canals, ponds, and other aquatic surfaces. Covers both natural water bodies
    and human-made water features such as reservoirs and artificial waterways.
    """

    # Core

    theme: Literal["base"] = Field(..., description="Feature theme")
    type: Literal["water"] = Field(..., description="Feature type")
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Point", "LineString", "Polygon", "MultiPolygon"),
    ] = Field(
        ...,
        description="Geometry (Point, LineString, Polygon, or MultiPolygon)",
    )

    # Optional

    class_: WaterClass = Field(
        default=WaterClass.WATER, alias="class", description="Water class"
    )
    names: NamesContainer | None = Field(default=None, description="Multilingual names")
    is_intermittent: bool | None = Field(
        default=None, description="Is it intermittent water or not"
    )
    is_salt: bool | None = Field(default=None, description="Is it salt water or not")
    source_tags: dict[str, Any] | None = Field(
        default=None, description="Source tags from data providers"
    )
    subtype: WaterSubtype = Field(
        default=WaterSubtype.WATER, description="Water subtype"
    )
    wikidata: WikidataId | None = Field(default=None, description="Wikidata identifier")
