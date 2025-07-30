"""Land feature models for Overture Maps base theme."""

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

from ..shared import SurfaceMaterial


class LandSubtype(str, Enum):
    """Land subtype classification."""

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
    """Land class classification."""

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


class Land(OvertureFeature):
    """Land feature model."""

    # Core

    theme: Literal["base"] = Field(..., description="Feature theme")
    type: Literal["land"] = Field(..., description="Feature type")
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Point", "LineString", "Polygon", "MultiPolygon"),
    ] = Field(..., description="Geometry (Point, LineString, Polygon, or MultiPolygon)")

    # Required

    class_: LandClass = Field(..., alias="class", description="Land class")
    subtype: LandSubtype = Field(..., description="Land subtype")

    # Optional

    elevation: int = Field(
        default=None, le=9000, description="Elevation above sea level in meters"
    )
    names: NamesContainer = Field(default=None, description="Multilingual names")
    source_tags: dict[str, Any] = Field(
        default=None, description="Source tags from data providers"
    )
    surface: SurfaceMaterial = Field(default=None, description="Surface material")
