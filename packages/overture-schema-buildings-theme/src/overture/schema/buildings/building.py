import textwrap
from enum import Enum
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.buildings._common import Appearance
from overture.schema.core import OvertureFeature
from overture.schema.core.models import Stacked
from overture.schema.core.names import Named
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)


class BuildingSubtype(str, Enum):
    """
    Broadest classification of the type and purpose of a building.

    This broad classification can be refined by `BuildingClass`.
    """

    AGRICULTURAL = "agricultural"
    CIVIC = "civic"
    COMMERCIAL = "commercial"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    INDUSTRIAL = "industrial"
    MEDICAL = "medical"
    MILITARY = "military"
    OUTBUILDING = "outbuilding"
    RELIGIOUS = "religious"
    RESIDENTIAL = "residential"
    SERVICE = "service"
    TRANSPORTATION = "transportation"


class BuildingClass(str, Enum):
    """
    Further classification of the type and purpose of a building.

    The building class adds detail to the broad classification of `BuildingSubtype`.
    """

    AGRICULTURAL = "agricultural"
    ALLOTMENT_HOUSE = "allotment_house"
    APARTMENTS = "apartments"
    BARN = "barn"
    BEACH_HUT = "beach_hut"
    BOATHOUSE = "boathouse"
    BRIDGE_STRUCTURE = "bridge_structure"
    BUNGALOW = "bungalow"
    BUNKER = "bunker"
    CABIN = "cabin"
    CARPORT = "carport"
    CATHEDRAL = "cathedral"
    CHAPEL = "chapel"
    CHURCH = "church"
    CIVIC = "civic"
    COLLEGE = "college"
    COMMERCIAL = "commercial"
    COWSHED = "cowshed"
    DETACHED = "detached"
    DIGESTER = "digester"
    DORMITORY = "dormitory"
    DWELLING_HOUSE = "dwelling_house"
    FACTORY = "factory"
    FARM = "farm"
    FARM_AUXILIARY = "farm_auxiliary"
    FIRE_STATION = "fire_station"
    GARAGE = "garage"
    GARAGES = "garages"
    GER = "ger"
    GLASSHOUSE = "glasshouse"
    GOVERNMENT = "government"
    GRANDSTAND = "grandstand"
    GREENHOUSE = "greenhouse"
    GUARDHOUSE = "guardhouse"
    HANGAR = "hangar"
    HOSPITAL = "hospital"
    HOTEL = "hotel"
    HOUSE = "house"
    HOUSEBOAT = "houseboat"
    HUT = "hut"
    INDUSTRIAL = "industrial"
    KINDERGARTEN = "kindergarten"
    KIOSK = "kiosk"
    LIBRARY = "library"
    MANUFACTURE = "manufacture"
    MILITARY = "military"
    MONASTERY = "monastery"
    MOSQUE = "mosque"
    OFFICE = "office"
    OUTBUILDING = "outbuilding"
    PARKING = "parking"
    PAVILION = "pavilion"
    POST_OFFICE = "post_office"
    PRESBYTERY = "presbytery"
    PUBLIC = "public"
    RELIGIOUS = "religious"
    RESIDENTIAL = "residential"
    RETAIL = "retail"
    ROOF = "roof"
    SCHOOL = "school"
    SEMI = "semi"
    SEMIDETACHED_HOUSE = "semidetached_house"
    SERVICE = "service"
    SHED = "shed"
    SHRINE = "shrine"
    SILO = "silo"
    SLURRY_TANK = "slurry_tank"
    SPORTS_CENTRE = "sports_centre"
    SPORTS_HALL = "sports_hall"
    STABLE = "stable"
    STADIUM = "stadium"
    STATIC_CARAVAN = "static_caravan"
    STILT_HOUSE = "stilt_house"
    STORAGE_TANK = "storage_tank"
    STY = "sty"
    SUPERMARKET = "supermarket"
    SYNAGOGUE = "synagogue"
    TEMPLE = "temple"
    TERRACE = "terrace"
    TOILETS = "toilets"
    TRAIN_STATION = "train_station"
    TRANSFORMER_TOWER = "transformer_tower"
    TRANSPORTATION = "transportation"
    TRULLO = "trullo"
    UNIVERSITY = "university"
    WAREHOUSE = "warehouse"
    WAYSIDE_SHRINE = "wayside_shrine"


class Building(
    OvertureFeature[Literal["buildings"], Literal["building"]],
    Named,
    Stacked,
    Appearance,
):
    """
    Buildings are man-made structures with roofs that exists permanently in one place.

    A building's geometry represents the two-dimensional footprint of the building as viewed from
    directly above, looking down. Fields such as `height` and `num_floors` allow the
    three-dimensional shape to be approximated. Some buildings, identified by the `has_parts` field,
    have associated `BuildingPart` features which can be used to generate a more representative 3D
    model of the building.
    """

    model_config = ConfigDict(title="building")

    # Overture Feature

    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(
            description="""The building's footprint or roofprint (if traced from aerial/satellite imagery).""",
        ),
    ]

    # Optional

    subtype: Annotated[
        BuildingSubtype | None,
        Field(
            description=textwrap.dedent("""
                A broad classification of the current use and purpose of the building.

                If the current use of the building no longer accords with the original built
                purpose, the current use should be specified. For example, a building built as a
                train station but later converted into a shopping mall would have the value
                `"commercial"` rather than `"transportation"`.
            """).strip()
        ),
    ] = None
    class_: Annotated[
        BuildingClass | None,
        Field(
            alias="class",
            description=textwrap.dedent("""
                A more specific classification of the current use and purpose of the building.

                If the current use of the building no longer accords with the original built
                purpose, the current use should be specified.
            """).strip(),
        ),
    ] = None
    has_parts: Annotated[
        bool | None,
        Field(
            description="Whether the building has associated building part features",
            strict=True,
        ),
    ] = None
