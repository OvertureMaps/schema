import textwrap
from enum import Enum
from typing import Annotated, Any, NewType

from pydantic import BaseModel, Field

from overture.schema.system.primitive import float64, int32
from overture.schema.system.string import WikidataId

Depth = NewType(
    "Depth",
    Annotated[
        int32,
        Field(
            ge=0,
            description="Depth below surface level of the feature in meters.",
        ),
    ],
)

Elevation = NewType(
    "Elevation",
    Annotated[
        int32,
        Field(
            le=9000,
            description="Elevation above sea level of the feature in meters.",
        ),
    ],
)

Height = NewType(
    "Height",
    Annotated[float64, Field(gt=0, description="Height of the feature in meters.")],
)


SourceTags = NewType(
    "SourceTags",
    Annotated[
        dict[str, Any],
        Field(
            description=textwrap.dedent("""
                Key/value pairs imported directly from the source data without change.

                This field provides access to raw OSM entity tags for features sourced from
                OpenStreetMap.
            """).strip()
        ),
    ],
)


class SourcedFromOpenStreetMap(BaseModel):
    source_tags: SourceTags | None = None
    wikidata: WikidataId | None = None


class SurfaceMaterial(str, Enum):
    """Material that makes up the surface of `Infrastructure` and `Land` features."""

    ASPHALT = "asphalt"
    COBBLESTONE = "cobblestone"
    COMPACTED = "compacted"
    CONCRETE = "concrete"
    CONCRETE_PLATES = "concrete_plates"
    DIRT = "dirt"
    EARTH = "earth"
    FINE_GRAVEL = "fine_gravel"
    GRASS = "grass"
    GRAVEL = "gravel"
    GROUND = "ground"
    PAVED = "paved"
    PAVING_STONES = "paving_stones"
    PEBBLESTONE = "pebblestone"
    RECREATION_GRASS = "recreation_grass"
    RECREATION_PAVED = "recreation_paved"
    RECREATION_SAND = "recreation_sand"
    RUBBER = "rubber"
    SAND = "sand"
    SETT = "sett"
    TARTAN = "tartan"
    UNPAVED = "unpaved"
    WOOD = "wood"
    WOODCHIPS = "woodchips"
