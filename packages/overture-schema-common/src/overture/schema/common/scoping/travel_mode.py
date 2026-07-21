"""
Types supporting the travel mode scope.
"""

from overture.schema.system.doc import DocumentedEnum


class TravelMode(str, DocumentedEnum):
    """Enumerates possible travel modes.

    Some modes represent groups of modes.
    """

    VEHICLE = "vehicle"
    MOTOR_VEHICLE = ("motor_vehicle", "Includes car, truck and motorcycle")
    CAR = "car"
    TRUCK = "truck"
    MOTORCYCLE = "motorcycle"
    FOOT = "foot"
    BICYCLE = "bicycle"
    BUS = "bus"
    HGV = "hgv"
    HOV = "hov"
    EMERGENCY = "emergency"
