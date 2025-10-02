from datetime import datetime
from typing import Annotated, NewType

from pydantic import Field

from overture.schema.system.constraint.string import (
    CountryCodeConstraint,
)
from overture.schema.system.primitive import int32, pct
from overture.schema.system.string import (
    HexColor,
    JsonPointer,
    LanguageTag,
    NoWhitespaceString,
    PhoneNumber,
    RegionCode,
    StrippedString,
    WikidataId,
)
from overture.schema.validation.constraints import (
    LinearReferenceRangeConstraint,
)
from overture.schema.validation.types import (
    ConfidenceScore,
)

Id = NewType(
    "Id",
    Annotated[
        NoWhitespaceString,
        Field(
            min_length=1,
            description="A feature ID. This may be an ID associated with the Global Entity Reference System (GERS) if—and-only-if the feature represents an entity that is part of GERS.",
        ),
    ],
)

# One possible advantage to using percentages over absolute distances is being able to
# trivially validate that the position lies "on" its segment (i.e. is between zero and
# one). Of course, this level of validity doesn't mean the number isn't nonsense
LinearlyReferencedPosition = NewType(
    "LinearlyReferencedPosition",
    Annotated[
        pct,
        Field(
            description="Represents a linearly-referenced position between 0% and 100% of the distance along a path such as a road segment or a river center-line segment.",
        ),
    ],
)
LinearlyReferencedRange = NewType(
    "LinearlyReferencedRange",
    Annotated[
        list[LinearlyReferencedPosition],
        LinearReferenceRangeConstraint(),
        Field(
            description="Represents a non-empty range of positions along a path as a pair linearly-referenced positions. For example, the pair [0.25, 0.5] represents the range beginning 25% of the distance from the start of the path and ending 50% of the distance from the path",
        ),
    ],
)

# Validating the opening hours value is going to have to happen outside of JSON Schema.
#
# Reasons for using the OSM opening hours specification for transportation rule time
# restrictions are documented in https://github.com/OvertureMaps/schema-wg/pull/10
OpeningHours = NewType(
    "OpeningHours",
    Annotated[
        str,
        Field(
            description="Time span or time spans during which something is open or active, specified in the OSM opening hours specification: https://wiki.openstreetmap.org/wiki/Key:opening_hours/specification"
        ),
    ],
)

Level = NewType(
    "Level",
    Annotated[
        int32,
        Field(default=0, description="Z-order of the feature where 0 is visual level"),
    ],
)

CountryCode = NewType(
    "CountryCode",
    Annotated[
        str,
        CountryCodeConstraint(),
        Field(description="ISO 3166-1 alpha-2 country code"),
    ],
)

CommonNames = NewType(
    "CommonNames",
    Annotated[
        dict[
            Annotated[
                LanguageTag,
                Field(
                    description="""Each entry consists of a key that is an IETF-BCP47 language tag; and a value that reflects the common name in the language represented by the key's language tag.

The validating regular expression for this property follows the pattern described in https://www.rfc-editor.org/rfc/bcp/bcp47.txt with the exception that private use tags are not supported."""
                ),
            ],
            StrippedString,
        ],
        Field(json_schema_extra={"additionalProperties": False}),
    ],
)

# It might be reasonable to combine "update_time" and "version" in a single
# "updateVersion" field which gives the last Overture version number in which the
# feature changed. The downside to doing this is that the number would cease to be
# indicative of the "rate of change" of the feature.
FeatureVersion = NewType(
    "FeatureVersion", Annotated[int32, Field(ge=0, description="")]
)

# A somewhat more compact approach would be to reference the Overture version where the
# feature last changed instead of the update time, and expect clients to do a lookup if
# they really care about the time
FeatureUpdateTime = NewType(
    "FeatureUpdateTime",
    Annotated[
        datetime,
        Field(
            description="Timestamp when the feature was last updated",
        ),
    ],
)

Prominence = NewType(
    "Prominence",
    Annotated[
        int,
        Field(
            ge=1,
            lt=100,
            description="Represents Overture's view of a place's significance or importance.  This value can be used to help drive cartographic display of a place and is derived from various factors including, but not limited to: population, capital status, place tags, and type.",
        ),
    ],
)

MinZoom = NewType(
    "MinZoom",
    Annotated[
        int,
        Field(
            ge=0,
            le=23,
            description="""Recommended minimum tile zoom per the Slippy Maps convention.

The Slippy Maps zooms are explained in the following references:
- https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
- https://www.maptiler.com/google-maps-coordinates-tile-bounds-projection""",
        ),
    ],
)

MaxZoom = NewType(
    "MaxZoom",
    Annotated[
        int,
        Field(
            ge=0,
            le=23,
            description="""Recommended maximum tile zoom per the Slippy Maps convention.

The Slippy Maps zooms are explained in the following references:
- https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
- https://www.maptiler.com/google-maps-coordinates-tile-bounds-projection""",
        ),
    ],
)

SortKey = NewType(
    "SortKey",
    Annotated[
        int,
        Field(
            default=0,
            description="An ascending numeric that defines the recommended order features should be drawn in. Features with lower number should be shown on top of features with a higher number.",
        ),
    ],
)

# this is an enum in the JSON Schema, but that prevents OvertureFeature from being extended
Theme = Annotated[
    str, Field(description="Top-level Overture theme this feature belongs to")
]

# this is an enum in the JSON Schema, but that prevents OvertureFeature from being extended
Type = Annotated[str, Field(description="Specific feature type within the theme")]

__all__ = [
    "CommonNames",
    "ConfidenceScore",
    "CountryCode",
    "CountryCodeConstraint",
    "FeatureUpdateTime",
    "FeatureVersion",
    "HexColor",
    "Id",
    "JsonPointer",
    "LanguageTag",
    "Level",
    "LinearlyReferencedPosition",
    "LinearlyReferencedRange",
    "LinearReferenceRangeConstraint",
    "MaxZoom",
    "MinZoom",
    "NoWhitespaceString",
    "OpeningHours",
    "PhoneNumber",
    "Prominence",
    "RegionCode",
    "SortKey",
    "Theme",
    "StrippedString",
    "Type",
    "WikidataId",
]
