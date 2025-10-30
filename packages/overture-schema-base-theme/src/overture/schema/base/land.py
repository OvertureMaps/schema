"""Land feature models for Overture Maps base theme."""

import textwrap
from enum import Enum
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.base._common import Elevation, SourcedFromOpenStreetMap
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

from ._common import SurfaceMaterial


class LandSubtype(str, Enum):
    """
    Broadest classification of the land.

    This broad classification can be refined by `LandClass`.
    """

    CRATER = "crater"
    DESERT = "desert"
    FOREST = "forest"
    GLACIER = "glacier"
    GRASS = "grass"
    LAND = "land"
    PHYSICAL = "physical"
    REEF = "reef"
    ROCK = "rock"
    SAND = "sand"
    SHRUB = "shrub"
    TREE = "tree"
    WETLAND = "wetland"


class LandClass(str, Enum):
    """
    Further classification of the land.

    The land class adds detail to the broad classification of `LandSubtype`.
    """

    ARCHIPELAGO = "archipelago"
    BARE_ROCK = "bare_rock"
    BEACH = "beach"
    CAVE_ENTRANCE = "cave_entrance"
    CLIFF = "cliff"
    DESERT = "desert"
    DUNE = "dune"
    FELL = "fell"
    FOREST = "forest"
    GLACIER = "glacier"
    GRASS = "grass"
    GRASSLAND = "grassland"
    HEATH = "heath"
    HILL = "hill"
    ISLAND = "island"
    ISLET = "islet"
    LAND = "land"
    MEADOW = "meadow"
    METEOR_CRATER = "meteor_crater"
    MOUNTAIN_RANGE = "mountain_range"
    PEAK = "peak"
    PENINSULA = "peninsula"
    PLATEAU = "plateau"
    REEF = "reef"
    RIDGE = "ridge"
    ROCK = "rock"
    SADDLE = "saddle"
    SAND = "sand"
    SCREE = "scree"
    SCRUB = "scrub"
    SHINGLE = "shingle"
    SHRUB = "shrub"
    SHRUBBERY = "shrubbery"
    STONE = "stone"
    TREE = "tree"
    TREE_ROW = "tree_row"
    TUNDRA = "tundra"
    VALLEY = "valley"
    VOLCANIC_CALDERA_RIM = "volcanic_caldera_rim"
    VOLCANO = "volcano"
    WETLAND = "wetland"
    WOOD = "wood"


class Land(
    OvertureFeature[Literal["base"], Literal["land"]],
    Named,
    Stacked,
    SourcedFromOpenStreetMap,
):
    """
    Land features are representations of physical land surfaces.

    In Overture data releases, land features are sourced from OpenStreetMap. TODO. Finish this when
    I get more info from Jennings.



    Physical representations of land surfaces.

    Global land derived from the inverse of OSM Coastlines. Translates `natural` tags from OpenStreetMap.

    TODO: Update this description when the relationship to `land_cover` is better understood.
    """

    model_config = ConfigDict(title="land")

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
                Geometry of the land feature, which may be a point, line string, polygon, or
                multi-polygon.
            """).strip()
        ),
    ]

    # Required

    class_: Annotated[LandClass, Field(default=LandClass.LAND, alias="class")] = (
        LandClass.LAND
    )
    subtype: Annotated[LandSubtype, Field(default=LandSubtype.LAND)] = LandSubtype.LAND

    # Optional

    elevation: Elevation | None = None
    surface: SurfaceMaterial | None = None
