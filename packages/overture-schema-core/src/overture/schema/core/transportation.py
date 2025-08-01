"""Transportation-related models and enums for Overture Maps features."""

from enum import Enum
from typing import Literal

from pydantic import Field

from overture.schema.core.base import StrictBaseModel

# Linear Referencing Types
LinearlyReferencedPosition = float
LinearlyReferencedRange = list[LinearlyReferencedPosition]


class TravelMode(str, Enum):
    """Travel mode enumeration."""

    CAR = "car"
    FOOT = "foot"
    BIKE = "bike"
    HGV = "hgv"
    BUS = "bus"
    TAXI = "taxi"
    MOTORCYCLE = "motorcycle"
    EMERGENCY = "emergency"
    DELIVERY = "delivery"
    VEHICLE = "vehicle"
    MOTOR_VEHICLE = "motor_vehicle"
    TRUCK = "truck"
    BICYCLE = "bicycle"
    HOV = "hov"


class VehicleDimension(str, Enum):
    """Vehicle dimension types."""

    WEIGHT = "weight"
    HEIGHT = "height"
    WIDTH = "width"
    LENGTH = "length"
    AXLE_LOAD = "axle_load"
    AXLE_COUNT = "axle_count"


class VehicleComparison(str, Enum):
    """Vehicle comparison operators."""

    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    LESS_THAN = "less_than"
    LESS_THAN_EQUAL = "less_than_equal"
    GREATER_THAN = "greater_than"
    GREATER_THAN_EQUAL = "greater_than_equal"


class PurposeOfUse(str, Enum):
    """Purpose of use enumeration."""

    TO_DELIVER = "to_deliver"
    AT_DESTINATION = "at_destination"
    THROUGH_TRAFFIC = "through_traffic"
    AS_CUSTOMER = "as_customer"
    TO_FARM = "to_farm"


class RecognizedStatus(str, Enum):
    """Recognized status enumeration."""

    AS_PRIVATE = "as_private"
    AS_EMPLOYEE = "as_employee"
    AS_CUSTOMER = "as_customer"
    AS_RESIDENT = "as_resident"
    AS_PERMITTED = "as_permitted"


class Speed(StrictBaseModel):
    """Speed value with unit."""

    # Required

    value: float = Field(..., gt=0, description="Speed value")
    unit: Literal["km/h", "mph"] = Field(..., description="Speed unit")

    def __hash__(self) -> int:
        """Make Speed hashable."""
        return hash((self.value, self.unit))


class VehicleConstraint(StrictBaseModel):
    """Vehicle constraint specification."""

    # Required

    dimension: VehicleDimension = Field(..., description="Vehicle dimension")
    comparison: VehicleComparison = Field(..., description="Comparison operator")
    value: float = Field(..., description="Constraint value")

    # Optional

    unit: str | None = Field(default=None, description="Unit of measurement")

    def __hash__(self) -> int:
        """Make VehicleConstraint hashable."""
        return hash((self.dimension, self.comparison, self.value, self.unit))
