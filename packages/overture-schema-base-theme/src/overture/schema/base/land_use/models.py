"""LandUse feature models for Overture Maps base theme."""

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


class LandUseSubtype(str, Enum):
    """Broad types of land use."""

    AGRICULTURE = "agriculture"
    AQUACULTURE = "aquaculture"
    CAMPGROUND = "campground"
    CEMETERY = "cemetery"
    CONSTRUCTION = "construction"
    DEVELOPED = "developed"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    GOLF = "golf"
    GRASS = "grass"
    HORTICULTURE = "horticulture"
    LANDFILL = "landfill"
    MANAGED = "managed"
    MEDICAL = "medical"
    MILITARY = "military"
    PARK = "park"
    PEDESTRIAN = "pedestrian"
    PROTECTED = "protected"
    RECREATION = "recreation"
    RELIGIOUS = "religious"
    RESIDENTIAL = "residential"
    RESOURCE_EXTRACTION = "resource_extraction"
    TRANSPORTATION = "transportation"
    WINTER_SPORTS = "winter_sports"


class LandUseClass(str, Enum):
    """Further classification of land use."""

    ABORIGINAL_LAND = "aboriginal_land"
    AIRFIELD = "airfield"
    ALLOTMENTS = "allotments"
    ANIMAL_KEEPING = "animal_keeping"
    AQUACULTURE = "aquaculture"
    BARRACKS = "barracks"
    BASE = "base"
    BEACH_RESORT = "beach_resort"
    BROWNFIELD = "brownfield"
    BUNKER = "bunker"
    CAMP_SITE = "camp_site"
    CEMETERY = "cemetery"
    CLINIC = "clinic"
    COLLEGE = "college"
    COMMERCIAL = "commercial"
    CONNECTION = "connection"
    CONSTRUCTION = "construction"
    DANGER_AREA = "danger_area"
    DOCTORS = "doctors"
    DOG_PARK = "dog_park"
    DOWNHILL = "downhill"
    DRIVING_RANGE = "driving_range"
    DRIVING_SCHOOL = "driving_school"
    EDUCATION = "education"
    ENVIRONMENTAL = "environmental"
    FAIRWAY = "fairway"
    FARMLAND = "farmland"
    FARMYARD = "farmyard"
    FATBIKE = "fatbike"
    FLOWERBED = "flowerbed"
    FOREST = "forest"
    GARAGES = "garages"
    GARDEN = "garden"
    GOLF_COURSE = "golf_course"
    GRASS = "grass"
    GRAVE_YARD = "grave_yard"
    GREEN = "green"
    GREENFIELD = "greenfield"
    GREENHOUSE_HORTICULTURE = "greenhouse_horticulture"
    HIGHWAY = "highway"
    HIKE = "hike"
    HOSPITAL = "hospital"
    ICE_SKATE = "ice_skate"
    INDUSTRIAL = "industrial"
    INSTITUTIONAL = "institutional"
    KINDERGARTEN = "kindergarten"
    LANDFILL = "landfill"
    LATERAL_WATER_HAZARD = "lateral_water_hazard"
    LOGGING = "logging"
    MARINA = "marina"
    MEADOW = "meadow"
    MILITARY = "military"
    MILITARY_HOSPITAL = "military_hospital"
    MILITARY_SCHOOL = "military_school"
    MUSIC_SCHOOL = "music_school"
    NATIONAL_PARK = "national_park"
    NATURAL_MONUMENT = "natural_monument"
    NATURE_RESERVE = "nature_reserve"
    NAVAL_BASE = "naval_base"
    NORDIC = "nordic"
    NUCLEAR_EXPLOSION_SITE = "nuclear_explosion_site"
    OBSTACLE_COURSE = "obstacle_course"
    ORCHARD = "orchard"
    PARK = "park"
    PEAT_CUTTING = "peat_cutting"
    PEDESTRIAN = "pedestrian"
    PITCH = "pitch"
    PLANT_NURSERY = "plant_nursery"
    PLAYGROUND = "playground"
    PLAZA = "plaza"
    PROTECTED = "protected"
    PROTECTED_LANDSCAPE_SEASCAPE = "protected_landscape_seascape"
    QUARRY = "quarry"
    RAILWAY = "railway"
    RANGE = "range"
    RECREATION_GROUND = "recreation_ground"
    RELIGIOUS = "religious"
    RESIDENTIAL = "residential"
    RESORT = "resort"
    RETAIL = "retail"
    ROUGH = "rough"
    SALT_POND = "salt_pond"
    SCHOOL = "school"
    SCHOOLYARD = "schoolyard"
    SKI_JUMP = "ski_jump"
    SKITOUR = "skitour"
    SLED = "sled"
    SLEIGH = "sleigh"
    SNOW_PARK = "snow_park"
    SPECIES_MANAGEMENT_AREA = "species_management_area"
    STADIUM = "stadium"
    STATE_PARK = "state_park"
    STATIC_CARAVAN = "static_caravan"
    STRICT_NATURE_RESERVE = "strict_nature_reserve"
    TEE = "tee"
    THEME_PARK = "theme_park"
    TRACK = "track"
    TRAFFIC_ISLAND = "traffic_island"
    TRAINING_AREA = "training_area"
    TRENCH = "trench"
    UNIVERSITY = "university"
    VILLAGE_GREEN = "village_green"
    VINEYARD = "vineyard"
    WATER_HAZARD = "water_hazard"
    WATER_PARK = "water_park"
    WILDERNESS_AREA = "wilderness_area"
    WINTER_SPORTS = "winter_sports"
    WORKS = "works"
    ZOO = "zoo"


class LandUse(OvertureFeature):
    """Human land use classification model.

    Represents how humans utilize land areas through structured categorization
    of land usage patterns. Covers diverse human activities including agriculture,
    residential development, commercial areas, recreational facilities, industrial
    zones, and infrastructure.

    Supports detailed classification through subtype and class hierarchies,
    elevation data, surface materials, and multilingual naming.
    """

    # Core

    theme: Literal["base"] = Field(..., description="Feature theme")
    type: Literal["land_use"] = Field(..., description="Feature type")
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint("Point", "LineString", "Polygon", "MultiPolygon"),
    ] = Field(
        ...,
        description="Geometry (Point, LineString, Polygon, or MultiPolygon)",
    )

    # Required

    class_: LandUseClass = Field(
        ..., alias="class", description="Further classification of the land use"
    )
    subtype: LandUseSubtype = Field(..., description="Broad type of land")

    # Optional

    elevation: float | None = Field(default=None, description="Elevation in meters")
    level: int | None = Field(default=None, description="Z-order level")
    names: NamesContainer | None = Field(default=None, description="Multilingual names")
    source_tags: dict[str, Any] | None = Field(
        default=None, description="Source tags from data providers"
    )
    surface: SurfaceMaterial | None = Field(
        default=None, description="Surface material"
    )
