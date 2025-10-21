# Validating the opening hours value is going to have to happen outside of JSON Schema.
#
# Reasons for using the OSM opening hours specification for transportation rule time
# restrictions are documented in https://github.com/OvertureMaps/schema-wg/pull/10
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
