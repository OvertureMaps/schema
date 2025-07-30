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
    """Water feature model."""

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

    # Required

    class_: WaterClass = Field(..., alias="class", description="Water class")
    subtype: WaterSubtype = Field(..., description="Water subtype")

    # Optional

    names: NamesContainer = Field(default=None, description="Multilingual names")
    is_intermittent: bool = Field(
        default=None, description="Is it intermittent water or not"
    )
    is_salt: bool = Field(default=None, description="Is it salt water or not")
    source_tags: dict[str, Any] = Field(
        default=None, description="Source tags from data providers"
    )
    wikidata: WikidataId = Field(default=None, description="Wikidata identifier")
