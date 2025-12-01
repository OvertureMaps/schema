"""
Types supporting the trravel mode scope.
"""

from enum import Enum


class TravelMode(str, Enum):
    """Enumerates possible travel modes.

    Some modes represent groups of modes.
    """

    VEHICLE = "vehicle"
    MOTOR_VEHICLE = "motor_vehicle"  # includes car, truck and motorcycle
    CAR = "car"
    TRUCK = "truck"
    MOTORCYCLE = "motorcycle"
    FOOT = "foot"
    BICYCLE = "bicycle"
    BUS = "bus"
    HGV = "hgv"
    HOV = "hov"
    EMERGENCY = "emergency"
