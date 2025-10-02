from typing import Annotated

from pydantic import BaseModel, Field

from overture.schema.buildings.enums import (
    FacadeMaterial,
    RoofMaterial,
    RoofOrientation,
    RoofShape,
)
from overture.schema.system.primitive import float64, int32
from overture.schema.system.string import HexColor


class Shape(BaseModel):
    """Properties of the buildings shape, such as height or roof type."""

    # Optional

    height: Annotated[
        float64 | None,
        Field(
            gt=0,
            description="""Height of the building or part in meters. The height is the distance from the lowest point to the highest point.""",
        ),
    ] = None
    is_underground: Annotated[
        bool | None,
        Field(
            description="""Whether the entire building or part is completely below ground. This is useful for rendering which typically omits these buildings or styles them differently because they are not visible above ground. This is different than the level column which is used to indicate z-ordering of elements and negative values may be above ground.""",
            strict=True,
        ),
    ] = None
    num_floors: Annotated[
        int32 | None,
        Field(
            gt=0,
            description="Number of above-ground floors of the building or part.",
        ),
    ] = None
    num_floors_underground: Annotated[
        int32 | None,
        Field(
            gt=0,
            description="Number of below-ground floors of the building or part.",
        ),
    ] = None
    min_height: Annotated[
        float64 | None,
        Field(
            description="The height of the bottom part of building in meters. Used if a building or part of building starts above the ground level.",
        ),
    ] = None
    min_floor: Annotated[
        int32 | None,
        Field(
            gt=0,
            description="""The "start" floor of this building or part. Indicates that the building or part is "floating" and its bottom-most floor is above ground level, usually because it is part of a larger building in which some parts do reach down to ground level. An example is a building that has an entry road or driveway at ground level into an interior courtyard, where part of the building bridges above the entry road. This property may sometimes be populated when min_height is missing and in these cases can be used as a proxy for min_height.""",
        ),
    ] = None
    facade_color: Annotated[
        HexColor | None,
        Field(
            description="The color (name or color triplet) of the facade of a building or building part in hexadecimal",
        ),
    ] = None
    facade_material: Annotated[
        FacadeMaterial | None,
        Field(description="The outer surface material of building facade."),
    ] = None
    roof_material: Annotated[
        RoofMaterial | None, Field(description="The outermost material of the roof.")
    ] = None
    roof_shape: Annotated[
        RoofShape | None, Field(description="The shape of the roof")
    ] = None
    roof_direction: Annotated[
        float64 | None,
        Field(
            ge=0,
            lt=360,
            description="Bearing of the roof ridge line in degrees.",
        ),
    ] = None
    roof_orientation: Annotated[
        RoofOrientation | None,
        Field(
            description="""Orientation of the roof shape relative to the footprint shape. Either "along" or "across".""",
        ),
    ] = None
    roof_color: Annotated[
        HexColor | None,
        Field(
            description="The color (name or color triplet) of the roof of a building or building part in hexadecimal",
        ),
    ] = None
    roof_height: Annotated[
        float64 | None,
        Field(
            description="""The height of the building roof in meters. This represents the distance from the base of the roof to the highest point of the roof.""",
        ),
    ] = None
