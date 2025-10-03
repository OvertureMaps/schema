from typing import Annotated, NewType

from pydantic import Field

from overture.schema.system.constraint import (
    CountryCodeConstraint,
    HexColorConstraint,
    JsonPointerConstraint,
    LanguageTagConstraint,
    NoWhitespaceConstraint,
    PhoneNumberConstraint,
    RegionCodeConstraint,
    SnakeCaseConstraint,
    StrippedConstraint,
    WikidataIdConstraint,
)

CountryCode = NewType(
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

HexColor = NewType(
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

JsonPointer = NewType(
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

LanguageTag = NewType(
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

NoWhitespaceString = NewType(
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

PhoneNumber = NewType(
    "PhoneNumber",
    Annotated[
        str, PhoneNumberConstraint(), Field(description="An international phone number")
    ],
)  # type: ignore [type-arg]
PhoneNumber.__doc__ = """
PhoneNumber : NewType
    An international telephone number.
"""

RegionCode = NewType(
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

SnakeCaseString = NewType("SnakeCaseString", Annotated[str, SnakeCaseConstraint()])

StrippedString = NewType(
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

WikidataId = NewType(
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
