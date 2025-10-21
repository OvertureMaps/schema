from enum import Enum


class SpeedUnit(str, Enum):
    """Unit of speed."""

    MPH = "mph"
    KPH = "km/h"


class LengthUnit(str, Enum):
    """Unit of length."""

    # Keep in sync with `combobulib/measure.py`.

    # Imperial units.
    IN = "in"  # Imperial: Inch.
    FT = "ft"  # Imperial: Foot.
    YD = "yd"  # Imperial: Yard.
    MI = "mi"  # Imperial: Mile.

    # SI units.
    CM = "cm"  # SI: centimeter.
    M = "m"  # SI: meter.
    KM = "km"  # SI: kilometer.


class WeightUnit(str, Enum):
    """Unit of weight."""

    # Keep in sync with `combobulib/measure.py`.

    # Imperial units.
    OZ = "oz"  # Imperial: Ounce.
    LB = "lb"  # Imperial: Pound.
    ST = "st"  # Imperial: Short Ton.
    LT = "lt"  # Imperial: Long Ton.

    # SI units.
    G = "g"  # SI: gram.
    KG = "kg"  # SI: kilogram.
    T = "t"  # SI: tonne.
