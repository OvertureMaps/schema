"""Water feature models for Overture Maps base theme."""

import textwrap
from enum import Enum
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.base._common import SourcedFromOpenStreetMap
from overture.schema.core import (
    OvertureFeature,
)
from overture.schema.core.models import Stacked
from overture.schema.core.names import Named
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)


class WaterSubtype(str, Enum):
    """
    The broad classification of water body such as river, ocean or lake.

    This broad classification can be refined using `WaterClass`.
    """

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
    """
    Further description of the type of water body.

    The water class adds detail to the broad classification of `WaterSubtype`.
    """

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


class Water(
    OvertureFeature[Literal["base"], Literal["water"]],
    Stacked,
    Named,
    SourcedFromOpenStreetMap,
):
    """
    Water features represent ocean and inland water bodies.

    In Overture data releases, water features are sourced from OpenStreetMap. There are two main
    categories of water feature: ocean and inland water bodies.

    Ocean
    -----
    The `subytpe` value `"ocean"` indicates an ocean area feature whose geometry represents the
    surface area of an ocean or part of an ocean. Ocean area may be tiled into many small polygons
    of consistent complexity to ensure manageable geometry. In Overture data releases, ocean area
    features are created from OpenStreetMap coastlines data (`natural=coastline`) using a QA'd
    version of the output from the OSMCoastline tool. In aggregate, all the ocean area features
    represent the inverse of the land features with subtype `"land"` and class `"land"`.

    The names and recommended label position for oceans and seas can be found in features with the
    subtype `"physical"` and the class `"ocean"` or `"sea"`.

    Inland Water
    ------------
    Subtypes other than `"ocean"` (and `"physical"`) represent inland water bodies. In Overture data
    releases, these features are sourced from the OpenStreetMap tag `natural=*` where the tag value
    indicates a water body, as well as the tags `natural=water`,  `waterway=*`,
    and `water=*`.
    """

    model_config = ConfigDict(title="water")

    # Overture Feature

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(
            GeometryType.POINT,
            GeometryType.LINE_STRING,
            GeometryType.POLYGON,
            GeometryType.MULTI_POLYGON,
        ),
        Field(
            description=textwrap.dedent("""
                Geometry of the water feature, which may be a point, line string, polygon, or
                multi-polygon.
            """).strip()
        ),
    ]

    # Required

    class_: Annotated[
        WaterClass,
        Field(
            default=WaterClass.WATER,
            alias="class",
        ),
    ] = WaterClass.WATER
    subtype: Annotated[
        WaterSubtype,
        Field(
            default=WaterSubtype.WATER,
        ),
    ] = WaterSubtype.WATER

    # Optional

    is_intermittent: Annotated[
        bool | None,
        Field(
            description="Whether the water body exists intermittently, not permanently",
            strict=True,
        ),
    ] = None
    is_salt: Annotated[
        bool | None,
        Field(description="Whether the water body contains salt water", strict=True),
    ] = None
