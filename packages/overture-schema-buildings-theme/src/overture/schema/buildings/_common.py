import textwrap
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field

from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.primitive import float64, int32
from overture.schema.system.string import HexColor


class FacadeMaterial(str, Enum):
    """The outer surface material of building facade."""

    BRICK = "brick"
    CEMENT_BLOCK = "cement_block"
    CLAY = "clay"
    CONCRETE = "concrete"
    GLASS = "glass"
    METAL = "metal"
    PLASTER = "plaster"
    PLASTIC = "plastic"
    STONE = "stone"
    TIMBER_FRAMING = "timber_framing"
    WOOD = "wood"


class RoofMaterial(str, Enum):
    """The outermost material of the roof."""

    CONCRETE = "concrete"
    COPPER = "copper"
    ETERNIT = "eternit"
    GLASS = "glass"
    GRASS = "grass"
    GRAVEL = "gravel"
    METAL = "metal"
    PLASTIC = "plastic"
    ROOF_TILES = "roof_tiles"
    SLATE = "slate"
    SOLAR_PANELS = "solar_panels"
    TAR_PAPER = "tar_paper"
    THATCH = "thatch"
    WOOD = "wood"


class RoofShape(str, Enum):
    """The shape of the roof."""

    DOME = "dome"
    FLAT = "flat"
    GABLED = "gabled"
    GAMBREL = "gambrel"
    HALF_HIPPED = "half_hipped"
    HIPPED = "hipped"
    MANSARD = "mansard"
    ONION = "onion"
    PYRAMIDAL = "pyramidal"
    ROUND = "round"
    SALTBOX = "saltbox"
    SAWTOOTH = "sawtooth"
    SKILLION = "skillion"
    SPHERICAL = "spherical"


class RoofOrientation(str, DocumentedEnum):
    """
    Orientation of the roof shape relative to the footprint shape.

    The members of this enumeration, `"across"` and `"along"`, are borrowed from the OpenStreetMap
    `roof:orientation=*` tag and have the same meanings as they do in OSM.
    """

    ACROSS = (
        "across",
        "The roof ridge runs perpendicular to the longer of the two building edges, parallel to the shorter",
    )
    ALONG = (
        "along",
        "The roof ridge runs parallel to the longer of the two building edges",
    )


class Appearance(BaseModel):
    """
    Physical and visual properties of a building, including dimensions, materials, and colors.
    """

    # Optional

    height: Annotated[
        float64 | None,
        Field(
            gt=0,
            description=textwrap.dedent("""
                Height of the building or part in meters.

                This is the distance from the lowest point to the highest point.
            """).strip(),
        ),
    ] = None
    is_underground: Annotated[
        bool | None,
        Field(
            description=textwrap.dedent("""
                Whether the entire building or part is completely below ground.

                The underground flag is useful for display purposes. Buildings and building parts
                that are entirely below ground can be styled differently or omitted from the
                rendered image.

                This flag is conceptually different from the `level` field, which indicates
                relative z-ordering and, notably, can be negative even if the building is entirely
                above-ground.
            """).strip(),
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
            description=textwrap.dedent("""
                Altitude above ground where the bottom of the building or building part starts.

                If present, this value indicates that the lowest part of the building or building
                part starts is above ground level.
            """).strip(),
        ),
    ] = None
    min_floor: Annotated[
        int32 | None,
        Field(
            gt=0,
            description=textwrap.dedent("""
                Start floor of this building or part.

                If present, this value indicates that the building or part is "floating" and its
                bottom-most floor is above ground level, usually because it is part of a larger
                building in which some parts do reach down to ground level. An example is a building
                that has an entry road or driveway at ground level into an interior courtyard, where
                part of the building bridges above the entry road. This property may sometimes be
                populated when `min_height` is missing and in these cases can be used as a proxy for
                `min_height`.
            """).strip(),
        ),
    ] = None
    facade_color: Annotated[
        HexColor | None,
        Field(
            description="Facade color in `#rgb` or `#rrggbb` hex notation",
        ),
    ] = None
    facade_material: Annotated[
        FacadeMaterial | None,
        Field(description="Outer surface material of the facade"),
    ] = None
    roof_material: Annotated[
        RoofMaterial | None, Field(description="Outer surface material of the roof")
    ] = None
    roof_shape: Annotated[RoofShape | None, Field(description="Shape of the roof")] = (
        None
    )
    roof_direction: Annotated[
        float64 | None,
        Field(
            ge=0,
            lt=360,
            description="Bearing of the roof ridge line in degrees",
        ),
    ] = None
    roof_orientation: Annotated[
        RoofOrientation | None,
        Field(
            description="""Orientation of the roof shape relative to the footprint shape""",
        ),
    ] = None
    roof_color: Annotated[
        HexColor | None,
        Field(
            description="The roof color in `#rgb` or `#rrggbb` hex notation",
        ),
    ] = None
    roof_height: Annotated[
        float64 | None,
        Field(
            description=textwrap.dedent("""
                Height of the roof in meters.

                This is the distance from the base of the roof to its highest point.
            """).strip(),
        ),
    ] = None
