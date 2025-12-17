"""
OpenStreetMap opening hours type.
"""

from typing import Annotated, NewType

from pydantic import Field

OpeningHours = NewType(
    "OpeningHours",
    Annotated[
        str,
        Field(
            description="Time span or time spans during which something is open or active, specified in the OSM opening hours specification: https://wiki.openstreetmap.org/wiki/Key:opening_hours/specification"
        ),
    ],
)
"""
Time span or time spans during which something is open or active, specified in the OpenStreetMap
opening hours specification: https://wiki.openstreetmap.org/wiki/Key:opening_hours/specification.
"""
