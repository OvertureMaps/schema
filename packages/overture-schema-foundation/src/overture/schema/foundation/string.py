from typing import Annotated, NewType, TypeAlias

from pydantic import Field

from overture.schema.foundation.constraint import (
    CountryCodeConstraint,
    HexColorConstraint,
    JsonPointerConstraint,
    LanguageTagConstraint,
    NoWhitespaceConstraint,
    PhoneNumberConstraint,
    RegionCodeConstraint,
    StrippedConstraint,
    WikidataIdConstraint,
)

HexColor: TypeAlias = NewType(
    "HexColor",
    Annotated[
        str,
        HexColorConstraint(),
        Field(
            description="A color represented as an #RRGGBB or #RGB hexadecimal string, for example #ff0000 for pure red."
        ),
    ],
)  # type: ignore [type-arg]
HexColor.__doc__ = """
HexColor : NewType
    A color represented as an #RRGGBB or #RGB hexadecimal string.

    For example:

    - "#ff0000" for pure red 🟥
    - "#ffa500" for bright orange 🟧
    - "#000000" or "#000" for black ⬛
"""


JsonPointer: TypeAlias = NewType(
    "JsonPointer",
    Annotated[
        str,
        JsonPointerConstraint(),
        Field(description="A JSON Pointer (as described in RFC-6901)"),
    ],
)  # type: ignore [type-arg]
JsonPointer.__doc__ = """
JsonPointer : NewType
    A JSON Pointer

    As described in `the JSON Pointer specification, RFC-6901 <https://rfc-editor.org/rfc/rfc6901.html>`
"""


LanguageTag: TypeAlias = NewType(
    "LanguageTag",
    Annotated[
        str,
        LanguageTagConstraint(),
        Field(
            description="A BCP-47 language tag",
        ),
    ],
)  # type: ignore [type-arg]
LanguageTag.__doc__ = """
LanguageTag : NewType
    A BCP-47 language tag.

    As described in `Tags for Identifying Languages, BCP-47 <https://www.rfc-editor.org/rfc/bcp/bcp47.txt>`
"""


StrippedString: TypeAlias = NewType(
    "StrippedString",
    Annotated[
        str,
        StrippedConstraint(),
        Field(
            description="A string without leading or trailing whitespace",
        ),
    ],
)  # type: ignore [type-arg]
StrippedString.__doc__ = """
StrippedString : NewType
    A string without leading or trailing whitespace.
"""


NoWhitespaceString: TypeAlias = NewType(
    "NoWhitespaceString",
    Annotated[
        str,
        NoWhitespaceConstraint(),
        Field(description="A string that contains no whitespace characters"),
    ],
)  # type: ignore [type-arg]
NoWhitespaceString.__doc__ = """
NoWhitespaceString : NewType
    A string that contains no whitespace characters.
"""


CountryCode: TypeAlias = NewType(
    "CountryCode",
    Annotated[
        str,
        CountryCodeConstraint(),
        Field(description="An ISO 3166-1 alpha-2 country code"),
    ],
)  # type: ignore [type-arg]
CountryCode.__doc__ = """
CountryCode : NewType
    An ISO-316601 alpha-2 country code.
"""

RegionCode: TypeAlias = NewType(
    "RegionCode",
    Annotated[
        str,
        RegionCodeConstraint(),
        Field(description="An ISO 3166-2 principal subdivision code"),
    ],
)  # type: ignore [type-arg]
RegionCode.__doc__ = """
RegionCode : NewType
    An ISO 3166-2 principal subdivision code.
"""

WikidataId: TypeAlias = NewType(
    "WikidataId",
    Annotated[
        str,
        WikidataIdConstraint(),
        Field(description="A wikidata ID, as found on https://www.wikidata.org/"),
    ],
)  # type: ignore [type-arg]
WikidataId.__doc__ = """
WikidataId : NewType
    A wikidata ID, as found on https://www.wikidata.org/.
"""


PhoneNumber: TypeAlias = NewType(
    "PhoneNumber",
    Annotated[
        str, PhoneNumberConstraint(), Field(description="An international phone number")
    ],
)  # type: ignore [type-arg]
PhoneNumber.__doc__ = """
PhoneNumber : NewType
    An international telephone number.
"""
