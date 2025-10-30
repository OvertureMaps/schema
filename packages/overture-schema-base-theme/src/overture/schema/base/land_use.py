"""Land use feature models for Overture Maps base theme."""

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


class LandUseSubtype(str, Enum):
    """
    Broadest classification of the land use.

    This broad classification can be refined by `LandUseClass`.
    """

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
    """
    Further classification of the land use.

    The land use class adds detail to the broad classification of `LandUseSubtype`.
    """

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


class LandUse(
    OvertureFeature[Literal["base"], Literal["land_use"]],
    Named,
    Stacked,
    SourcedFromOpenStreetMap,
):
    """
    Land use features specify the predominant human use of an area of land, for example commercial
    activity, recreation, farming, housing, education, or military use.

    Land use features relate to `LandCover` features in the following way: land use is the human
    human activity being done with the land, while land cover is the physical thing that covers it.

    TODO: Explain relationship to `Land` features.
    """

    model_config = ConfigDict(title="land_use")

    # Core

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(
            GeometryType.POINT,
            GeometryType.LINE_STRING,
            GeometryType.POLYGON,
            GeometryType.MULTI_POLYGON,
        ),
        Field(
            description=textwrap.dedent(
                """
                Geometry of the land use area, which may be a point, line string, polygon, or
                multi-polygon.
                """
            ).strip(),
        ),
    ]

    # Required

    class_: Annotated[LandUseClass, Field(alias="class")]
    subtype: LandUseSubtype

    # Optional

    elevation: Elevation | None = None
    surface: SurfaceMaterial | None = None
