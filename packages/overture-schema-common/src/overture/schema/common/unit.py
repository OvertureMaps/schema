"""
Measurement units for speed, length, weight, and the like.
"""

from overture.schema.system.doc import DocumentedEnum


class SpeedUnit(str, DocumentedEnum):
    """Unit of speed."""

    MPH = ("mph", "Miles per hour")
    KMH = ("km/h", "Kilometers per hour")


class LengthUnit(str, DocumentedEnum):
    """Unit of length."""

    # Keep in sync with `combobulib/measure.py`.

    # Imperial units.
    IN = ("in", "One inch in the imperial and US customary systems")
    FT = ("ft", "One foot in the imperial and US customary systems (12 inches)")
    YD = ("yd", "One yard in the imperial and US customary systems (three feet)")
    MI = ("mi", "One mile in the imperial and US customary systems (1,760 yards)")

    # SI units.
    CM = ("cm", "One centimeter in the metric and SI systems")
    M = ("m", "One meter in the metric and SI systems")
    KM = ("km", "One kilometer in the metric and SI systems")


class WeightUnit(str, DocumentedEnum):
    """Unit of weight."""

    # Keep in sync with `combobulib/measure.py`.

    # Imperial units.
    OZ = ("oz", "One ounce in the imperial and US customary systems")
    LB = ("lb", "One pound in the imperial and US customary systems")
    ST = ("st", "One short ton, or one ton in the US customary system (2,000 pounds)")
    LT = ("lt", "One long ton, or one ton in the imperial system (2,400 pounds)")

    # SI units.
    G = ("g", "One gram in the metric and SI systems")
    KG = ("kg", "One kilogram in the metric and SI systems")
    T = ("t", "One tonne in the metric and SI systems")
