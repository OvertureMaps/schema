from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from overture.schema.core.unit import LengthUnit, WeightUnit
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.primitive import float32, uint8


class VehicleDimension(str, Enum):
    """
    Dimension of a vehicle, such as length, weight, or number of axles, that can be constrained in a
    `VehicleParameter`.

    See also: `overture.schema.core.scoping.Scope.VEHICLE`.
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
class VehicleAxleCountSelector(BaseModel):
    """
    Selects vehicles based on the number of axles they have.
    """

    dimension: Literal[VehicleDimension.AXLE_COUNT]
    comparison: VehicleRelation
    value: uint8 = Field(description="Number of axles on the vehicle")


@no_extra_fields
class VehicleHeightSelector(BaseModel):
    """
    Selects vehicles based on their height.
    """

    dimension: Literal[VehicleDimension.HEIGHT]
    comparison: VehicleRelation
    value: Annotated[
        float32,
        Field(
            ge=0, decription="Vehicle height selection threshold in the given `unit`"
        ),
    ]
    unit: LengthUnit = Field(description="Height unit in which `value` is expressed")


@no_extra_fields
class VehicleLengthSelector(BaseModel):
    """
    Selects vehicles based on their length.
    """

    dimension: Literal[VehicleDimension.LENGTH]
    comparison: VehicleRelation
    value: Annotated[
        float32,
        Field(
            ge=0, description="Vehicle length selection threshold in the given `unit`"
        ),
    ]
    unit: LengthUnit = Field(description="Length unit in which `value` is expressed")


@no_extra_fields
class VehicleWeightSelector(BaseModel):
    """
    Selects vehicles based on their weight.
    """

    dimension: Literal[VehicleDimension.WEIGHT]
    comparison: VehicleRelation
    value: Annotated[
        float32,
        Field(
            ge=0, description="Vehicle weight selection threshold in the given `unit`"
        ),
    ]
    unit: WeightUnit = Field(description="Weight unit in which `value` is expressed")


@no_extra_fields
class VehicleWidthSelector(BaseModel):
    """
    Selects vehicles based on their width.
    """

    dimension: Literal[VehicleDimension.WIDTH]
    comparison: VehicleRelation
    value: Annotated[
        float32,
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
        description="Selects vehicles that a scope applies to based on criteria such as height, weight, or axle count."
    ),
]
"""
Selects vehicles that a scope applies to based on criteria such as height, weigh, or axle count.
"""
