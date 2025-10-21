"""Transportation theme enums."""

from enum import Enum


class Subtype(str, Enum):
    """Transportation segment subtype classification."""

    ROAD = "road"
    RAIL = "rail"
    WATER = "water"


class DestinationLabelType(str, Enum):
    """Indicates what special symbol/icon is present on a signpost, visible as road
    marking or similar."""

    STREET = "street"
    COUNTRY = "country"
    ROUTE_REF = "route_ref"
    TOWARD_ROUTE_REF = "toward_route_ref"
    UNKNOWN = "unknown"


class RoadClass(str, Enum):
    """Captures the kind of road and its position in the road network hierarchy."""

    MOTORWAY = "motorway"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    RESIDENTIAL = "residential"
    LIVING_STREET = "living_street"  # Similar to residential but has implied legal restriction for motor vehicles (which can vary country by country)
    TRUNK = "trunk"
    UNCLASSIFIED = "unclassified"  # Known roads, paved, but subordinate to all of: motorway, trunk, primary, secondary, tertiary
    SERVICE = "service"  # Provides vehicle access to a feature (such as a building), typically not part of the public street network
    PEDESTRIAN = "pedestrian"
    FOOTWAY = "footway"  # Minor segments mainly used by pedestrians
    STEPS = "steps"
    PATH = "path"
    TRACK = "track"
    CYCLEWAY = "cycleway"
    BRIDLEWAY = "bridleway"  # Similar to track but has implied access only for horses
    UNKNOWN = "unknown"


class RailClass(str, Enum):
    """Captures the kind of rail segment."""

    FUNICULAR = "funicular"  # Inclined plane / cliff railway
    LIGHT_RAIL = (
        "light_rail"  # Higher-standard tram system, falls between 'tram' and 'rail'
    )
    MONORAIL = "monorail"
    NARROW_GAUGE = "narrow_gauge"
    STANDARD_GAUGE = (
        "standard_gauge"  # Standard-gauge rail, equivalent to OSM's railway=rail tag
    )
    SUBWAY = "subway"  # City passenger rail, often underground

    TRAM = "tram"  # 1-2 carriage rail vehicle tracks, often sharing road with vehicles
    UNKNOWN = "unknown"


# todo - Vic - delete this
class Heading(str, Enum):
    """Enumerates possible travel headings along segment geometry."""

    FORWARD = "forward"
    BACKWARD = "backward"


class DestinationSignSymbol(str, Enum):
    """Indicates what special symbol/icon is present on a signpost, visible as road
    marking or similar."""

    MOTORWAY = "motorway"
    AIRPORT = "airport"
    HOSPITAL = "hospital"
    CENTER = "center"  # center of a locality, city center or downtown, from centre in raw OSM value
    INDUSTRIAL = "industrial"
    PARKING = "parking"
    BUS = "bus"
    TRAIN_STATION = "train_station"
    REST_AREA = "rest_area"
    FERRY = "ferry"
    MOTORROAD = "motorroad"
    FUEL = "fuel"
    VIEWPOINT = "viewpoint"
    FUEL_DIESEL = "fuel_diesel"
    FOOD = "food"  # 'food', 'restaurant' in OSM
    LODGING = "lodging"
    INFO = "info"
    CAMP_SITE = "camp_site"
    INTERCHANGE = "interchange"
    RESTROOMS = "restrooms"  # 'toilets' in OSM


class RoadFlag(str, Enum):
    """Simple flags that can be on or off for a road segment.

    Specifies physical characteristics and can overlap.
    """

    IS_BRIDGE = "is_bridge"
    IS_LINK = "is_link"  # Note: `is_link` is deprecated and will be removed in a future release in favor of the link subclass
    IS_TUNNEL = "is_tunnel"
    IS_UNDER_CONSTRUCTION = "is_under_construction"
    IS_ABANDONED = "is_abandoned"
    IS_COVERED = "is_covered"
    IS_INDOOR = "is_indoor"


class RailFlag(str, Enum):
    """Simple flags that can be on or off for a railway segment.

    Specifies physical characteristics and can overlap.
    """

    IS_BRIDGE = "is_bridge"
    IS_TUNNEL = "is_tunnel"  # You may also be looking for the 'subway' class (though subways are occasionally above-ground)
    IS_UNDER_CONSTRUCTION = "is_under_construction"
    IS_ABANDONED = "is_abandoned"
    IS_COVERED = "is_covered"
    IS_PASSENGER = "is_passenger"
    IS_FREIGHT = "is_freight"
    IS_DISUSED = "is_disused"


class RoadSurface(str, Enum):
    """Physical surface of the road."""

    UNKNOWN = "unknown"
    PAVED = "paved"
    UNPAVED = "unpaved"
    GRAVEL = "gravel"
    DIRT = "dirt"
    PAVING_STONES = "paving_stones"
    METAL = "metal"


class Subclass(str, Enum):
    """Refines expected usage of the segment, must not overlap."""

    LINK = "link"  # Connecting stretch (sliproad or ramp) between two road types
    SIDEWALK = "sidewalk"  # Footway that lies along a road
    CROSSWALK = "crosswalk"  # Footway that intersects other roads
    PARKING_AISLE = "parking_aisle"  # Service road intended for parking
    DRIVEWAY = "driveway"  # Service road intended for deliveries
    ALLEY = "alley"  # Service road intended for rear entrances, fire exits
    CYCLE_CROSSING = "cycle_crossing"  # Cycleway that intersects with other roads


class AccessType(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    DESIGNATED = "designated"
