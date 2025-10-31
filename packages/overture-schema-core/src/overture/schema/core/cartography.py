import textwrap
from typing import Annotated, NewType

from pydantic import BaseModel, Field

from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.primitive import uint8

Prominence = NewType(
    "Prominence",
    Annotated[
        uint8,
        Field(
            ge=1,
            le=100,
            description=textwrap.dedent("""
                Subjective scale of feature significance or importance, with 1 being the least, and
                100 being the most, significant.

                This value can be used to help drive decisions about how and when to display a
                feature, and how to treat it relative to neighboring features.

                When populated by Overture, this value is derived from various factors including,
                but not limited to: feature and subtype, population, and capital status.
            """).strip(),
        ),
    ],
)

MinZoom = NewType(
    "MinZoom",
    Annotated[
        uint8,
        Field(
            ge=0,
            le=23,
            description=textwrap.dedent("""
                Recommended minimum tile zoom level in which this feature should be displayed.

                It is recommended that the feature be hidden at zoom levels below this value.

                Zoom levels follow the Slippy Maps convention, documented in the following
                references:
                - https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
                - https://www.maptiler.com/google-maps-coordinates-tile-bounds-projection
                """).strip(),
        ),
    ],
)

MaxZoom = NewType(
    "MaxZoom",
    Annotated[
        uint8,
        Field(
            ge=0,
            le=23,
            description=textwrap.dedent("""
                Recommended maximum tile zoom level in which this feature should be displayed.

                It is recommended that the feature be hidden at zoom levels above this value.

                Zoom levels follow the Slippy Maps convention, documented in the following
                references:
                - https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
                - https://www.maptiler.com/google-maps-coordinates-tile-bounds-projection
            """).strip(),
        ),
    ],
)

SortKey = NewType(
    "SortKey",
    Annotated[
        uint8,
        Field(
            description=textwrap.dedent("""
                Integer indicating the recommended order in which to draw features.

                Features with a lower number should be drawn "in front" of features with a higher
                number.
            """).strip(),
        ),
    ],
)


@no_extra_fields
class CartographicHints(BaseModel):
    """Cartographic hints for optimal use of Overture features in map-making."""

    # Optional

    prominence: Prominence | None = None
    min_zoom: MinZoom | None = None
    max_zoom: MaxZoom | None = None
    sort_key: SortKey | None = None


class CartographicallyHinted(BaseModel):
    cartography: Annotated[CartographicHints | None, Field(title="cartography")] = None
