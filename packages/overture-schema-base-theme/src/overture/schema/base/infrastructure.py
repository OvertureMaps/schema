"""Infrastructure feature models for Overture Maps base theme."""

import textwrap
from enum import Enum
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from overture.schema.base._common import Height, SourcedFromOpenStreetMap
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


class InfrastructureSubtype(str, Enum):
    """
    Broadest classification of the type of infrastructure.

    This broad classification can be refined by `InfrastructureClass`.
    """

    AERIALWAY = "aerialway"
    AIRPORT = "airport"
    BARRIER = "barrier"
    BRIDGE = "bridge"
    COMMUNICATION = "communication"
    EMERGENCY = "emergency"
    MANHOLE = "manhole"
    PEDESTRIAN = "pedestrian"
    PIER = "pier"
    POWER = "power"
    QUAY = "quay"
    RECREATION = "recreation"
    TOWER = "tower"
    TRANSIT = "transit"
    TRANSPORTATION = "transportation"
    UTILITY = "utility"
    WASTE_MANAGEMENT = "waste_management"
    WATER = "water"


class InfrastructureClass(str, Enum):
    """
    Further classification of the type of infrastructure.

    The infrastructure class adds detail to the broad classification of `InfrastructureSubtype`.
    """

    AERIALWAY_STATION = "aerialway_station"
    AIRPORT = "airport"
    AIRPORT_GATE = "airport_gate"
    AIRSTRIP = "airstrip"
    APRON = "apron"
    AQUEDUCT = "aqueduct"
    ARTWORK = "artwork"
    ATM = "atm"
    BARRIER = "barrier"
    BELL_TOWER = "bell_tower"
    BENCH = "bench"
    BICYCLE_PARKING = "bicycle_parking"
    BICYCLE_RENTAL = "bicycle_rental"
    BLOCK = "block"
    BOARDWALK = "boardwalk"
    BOLLARD = "bollard"
    BORDER_CONTROL = "border_control"
    BREAKWATER = "breakwater"
    BRIDGE = "bridge"
    BRIDGE_SUPPORT = "bridge_support"
    BUMP_GATE = "bump_gate"
    BUS_ROUTE = "bus_route"
    BUS_STATION = "bus_station"
    BUS_STOP = "bus_stop"
    BUS_TRAP = "bus_trap"
    CABLE = "cable"
    CABLE_BARRIER = "cable_barrier"
    CABLE_CAR = "cable_car"
    CABLE_DISTRIBUTION = "cable_distribution"
    CAMP_SITE = "camp_site"
    CANTILEVER = "cantilever"
    CATENARY_MAST = "catenary_mast"
    CATTLE_GRID = "cattle_grid"
    CHAIN = "chain"
    CHAIR_LIFT = "chair_lift"
    CHARGING_STATION = "charging_station"
    CITY_WALL = "city_wall"
    COMMUNICATION_LINE = "communication_line"
    COMMUNICATION_POLE = "communication_pole"
    COMMUNICATION_TOWER = "communication_tower"
    CONNECTION = "connection"
    COOLING = "cooling"
    COVERED = "covered"
    CROSSING = "crossing"
    CUTLINE = "cutline"
    CYCLE_BARRIER = "cycle_barrier"
    DAM = "dam"
    DEFENSIVE = "defensive"
    DITCH = "ditch"
    DIVING = "diving"
    DRAG_LIFT = "drag_lift"
    DRAIN = "drain"
    DRINKING_WATER = "drinking_water"
    ENTRANCE = "entrance"
    FENCE = "fence"
    FERRY_TERMINAL = "ferry_terminal"
    FIRE_HYDRANT = "fire_hydrant"
    FOUNTAIN = "fountain"
    FULL_HEIGHT_TURNSTILE = "full-height_turnstile"
    GASOMETER = "gasometer"
    GATE = "gate"
    GENERATOR = "generator"
    GIVE_WAY = "give_way"
    GONDOLA = "gondola"
    GOODS = "goods"
    GUARD_RAIL = "guard_rail"
    HAMPSHIRE_GATE = "hampshire_gate"
    HANDRAIL = "handrail"
    HEDGE = "hedge"
    HEIGHT_RESTRICTOR = "height_restrictor"
    HELIOSTAT = "heliostat"
    HELIPAD = "helipad"
    HELIPORT = "heliport"
    HOSE = "hose"
    INFORMATION = "information"
    INSULATOR = "insulator"
    INTERNATIONAL_AIRPORT = "international_airport"
    J_BAR = "j-bar"
    JERSEY_BARRIER = "jersey_barrier"
    KERB = "kerb"
    KISSING_GATE = "kissing_gate"
    LAUNCHPAD = "launchpad"
    LIFT_GATE = "lift_gate"
    LIGHTING = "lighting"
    LIGHTNING_PROTECTION = "lightning_protection"
    MAGIC_CARPET = "magic_carpet"
    MANHOLE = "manhole"
    MILESTONE = "milestone"
    MILITARY_AIRPORT = "military_airport"
    MINARET = "minaret"
    MINOR_LINE = "minor_line"
    MIXED_LIFT = "mixed_lift"
    MOBILE_PHONE_TOWER = "mobile_phone_tower"
    MONITORING = "monitoring"
    MOTORCYCLE_PARKING = "motorcycle_parking"
    MOTORWAY_JUNCTION = "motorway_junction"
    MOVABLE = "movable"
    MUNICIPAL_AIRPORT = "municipal_airport"
    OBSERVATION = "observation"
    PARKING = "parking"
    PARKING_ENTRANCE = "parking_entrance"
    PARKING_SPACE = "parking_space"
    PEDESTRIAN_CROSSING = "pedestrian_crossing"
    PICNIC_TABLE = "picnic_table"
    PIER = "pier"
    PIPELINE = "pipeline"
    PLANT = "plant"
    PLANTER = "planter"
    PLATFORM = "platform"
    PLATTER = "platter"
    PORTAL = "portal"
    POST_BOX = "post_box"
    POWER_LINE = "power_line"
    POWER_POLE = "power_pole"
    POWER_TOWER = "power_tower"
    PRIVATE_AIRPORT = "private_airport"
    PYLON = "pylon"
    QUAY = "quay"
    RADAR = "radar"
    RAILWAY_HALT = "railway_halt"
    RAILWAY_STATION = "railway_station"
    RECYCLING = "recycling"
    REGIONAL_AIRPORT = "regional_airport"
    RESERVOIR_COVERED = "reservoir_covered"
    RETAINING_WALL = "retaining_wall"
    ROLLER_COASTER = "roller_coaster"
    ROPE_TOW = "rope_tow"
    RUNWAY = "runway"
    SALLY_PORT = "sally_port"
    SEAPLANE_AIRPORT = "seaplane_airport"
    SEWER = "sewer"
    SILO = "silo"
    SIREN = "siren"
    STILE = "stile"
    STOP = "stop"
    STOP_POSITION = "stop_position"
    STOPWAY = "stopway"
    STORAGE_TANK = "storage_tank"
    STREET_CABINET = "street_cabinet"
    STREET_LAMP = "street_lamp"
    SUBSTATION = "substation"
    SUBWAY_STATION = "subway_station"
    SWING_GATE = "swing_gate"
    SWITCH = "switch"
    T_BAR = "t-bar"
    TAXILANE = "taxilane"
    TAXIWAY = "taxiway"
    TERMINAL = "terminal"
    TOILETS = "toilets"
    TOLL_BOOTH = "toll_booth"
    TRAFFIC_SIGNALS = "traffic_signals"
    TRANSFORMER = "transformer"
    TRESTLE = "trestle"
    UTILITY_POLE = "utility_pole"
    VENDING_MACHINE = "vending_machine"
    VIADUCT = "viaduct"
    VIEWPOINT = "viewpoint"
    WALL = "wall"
    WASTE_BASKET = "waste_basket"
    WASTE_DISPOSAL = "waste_disposal"
    WATCHTOWER = "watchtower"
    WATER_TOWER = "water_tower"
    WEIR = "weir"
    ZIP_LINE = "zip_line"


class Infrastructure(
    OvertureFeature[Literal["base"], Literal["infrastructure"]],
    Named,
    Stacked,
    SourcedFromOpenStreetMap,
):
    """
    Infrastructure features provide basic information about real-world infrastructure entitites
    such as bridges, airports, runways, aerialways, communication towers, and power lines.
    """

    model_config = ConfigDict(title="infrastructure")

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
                Geometry of the infrastructure feature, which may be a point, line string, polygon, or
                multi-polygon.
            """).strip()
        ),
    ]

    # Required

    class_: Annotated[InfrastructureClass, Field(alias="class")]
    subtype: InfrastructureSubtype

    # Optional

    height: Height | None = None
    surface: SurfaceMaterial | None = None
