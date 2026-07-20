"""
Types supporting the vehicle scope.
"""

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from overture.schema.common.unit import LengthUnit, WeightUnit
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.primitive import float64


class VehicleDimension(str, Enum):
    """
    Dimension of a vehicle, such as length, weight, or number of axles, that can be constrained in a
    `VehicleParameter`.

    See also: `overture.schema.common.scoping.Scope.VEHICLE`.
    """

    AXLE_COUNT = "axle_count"
    HEIGHT = "height"
    LENGTH = "length"
    WEIGHT = "weight"
    WIDTH = "width"


class VehicleRelation(str, Enum):
    """Relational operator, such as less than or equal to."""

    GREATER_THAN = "greater_than"
    GREATER_THAN_EQUAL = "greater_than_equal"
    EQUAL = "equal"
    LESS_THAN = "less_than"
    LESS_THAN_EQUAL = "less_than_equal"


@no_extra_fields
class VehicleSelectorBase(BaseModel):
    """
    Common fields shared by all vehicle selector subtypes.

    See also: `VehicleSelector`.
    """

    dimension: VehicleDimension
    comparison: VehicleRelation


@no_extra_fields
class VehicleAxleCountSelector(VehicleSelectorBase):
    """Selects vehicles based on the number of axles they have."""

    dimension: Literal[VehicleDimension.AXLE_COUNT]
    # float64 to share the other vehicle dimensions' `value` type; `multiple_of`
    # is what holds axle count to a whole number.
    value: Annotated[
        float64,
        Field(
            ge=1,
            le=100,
            multiple_of=1,
            description="Number of axles on the vehicle",
        ),
    ]


@no_extra_fields
class VehicleHeightSelector(VehicleSelectorBase):
    """Selects vehicles based on their height."""

    dimension: Literal[VehicleDimension.HEIGHT]
    value: Annotated[
        float64,
        Field(
            ge=0, description="Vehicle height selection threshold in the given `unit`"
        ),
    ]
    unit: LengthUnit = Field(description="Height unit in which `value` is expressed")


@no_extra_fields
class VehicleLengthSelector(VehicleSelectorBase):
    """Selects vehicles based on their length."""

    dimension: Literal[VehicleDimension.LENGTH]
    value: Annotated[
        float64,
        Field(
            ge=0, description="Vehicle length selection threshold in the given `unit`"
        ),
    ]
    unit: LengthUnit = Field(description="Length unit in which `value` is expressed")


@no_extra_fields
class VehicleWeightSelector(VehicleSelectorBase):
    """Selects vehicles based on their weight."""

    dimension: Literal[VehicleDimension.WEIGHT]
    value: Annotated[
        float64,
        Field(
            ge=0, description="Vehicle weight selection threshold in the given `unit`"
        ),
    ]
    unit: WeightUnit = Field(description="Weight unit in which `value` is expressed")


@no_extra_fields
class VehicleWidthSelector(VehicleSelectorBase):
    """Selects vehicles based on their width."""

    dimension: Literal[VehicleDimension.WIDTH]
    value: Annotated[
        float64,
        Field(
            ge=0, description="Vehicle width selection threshold in the given `unit`"
        ),
    ]
    unit: LengthUnit = Field(description="Width unit in which `value` is expressed")


VehicleSelector = Annotated[
    VehicleAxleCountSelector
    | VehicleHeightSelector
    | VehicleLengthSelector
    | VehicleWeightSelector
    | VehicleWidthSelector,
    Field(
        discriminator="dimension",
        description="Selects vehicles that a scope applies to based on criteria such as height, weight, or axle count.",
    ),
]
"""
Selects vehicles that a scope applies to based on criteria such as height, weigh, or axle count.
"""
