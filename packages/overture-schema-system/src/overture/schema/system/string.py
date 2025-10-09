"""
Fundamental string types.

This module provides a convenient set of reusable string types that can be used as field types in
Pydantic models to ensure the field values conform to well-known patterns, for example country
codes, language tags, and color codes.

While not considered "primitives", the fundamental string types are intended to provide specific,
well-defined behavior for a wide range of serialization targets including not just Pydantic models
and JSON, but also including targets such as the Parquet data formats and Spark dataframes.
"""

from typing import Annotated, NewType

from pydantic import Field

from overture.schema.system.field_constraint import (
    CountryCodeAlpha2Constraint,
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

CountryCodeAlpha2 = NewType(
    "CountryCodeAlpha2",
    Annotated[
        str,
        CountryCodeAlpha2Constraint(),
        Field(description="An ISO 3166-1 alpha-2 country code"),
    ],
)  # type: ignore [type-arg]
"""
An ISO-3166-1 alpha-2 country code.
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
"""
A color represented as an #RRGGBB or #RGB hexadecimal string.

For example:

- `"#ff0000"` for pure red 🟥
- `"#ffa500"` for bright orange 🟧
- `"#000000"` or `"#000"` for black ⬛
"""

JsonPointer = NewType(
    "JsonPointer",
    Annotated[
        str,
        JsonPointerConstraint(),
        Field(description="A JSON Pointer (as described in RFC-6901)"),
    ],
)  # type: ignore [type-arg]
"""
A JSON Pointer

As described in `the JSON Pointer specification, RFC-6901`_.

.. _the JSON Pointer specification, RFC-6901: https://rfc-editor.org/rfc/rfc6901.html

For example:

- `""` (root value)
- `"/connectors/"`
- `"/connectors/0/at"`
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
"""
A BCP-47 language tag.

As described in `Tags for Identifying Languages, BCP-47`_.

.. _Tags for Identifying Languages, BCP-47: https://www.rfc-editor.org/rfc/bcp/bcp47.txt

For example:

- `"en"`
- `"en-US"`
- `"fr-CA"`
- `"zh-Hant-TW"`
"""

NoWhitespaceString = NewType(
    "NoWhitespaceString",
    Annotated[
        str,
        NoWhitespaceConstraint(),
        Field(description="A string that contains no whitespace characters"),
    ],
)  # type: ignore [type-arg]
"""
A string that contains no whitespace characters.
"""

PhoneNumber = NewType(
    "PhoneNumber",
    Annotated[
        str, PhoneNumberConstraint(), Field(description="An international phone number")
    ],
)  # type: ignore [type-arg]
"""
An international phone number.
"""

RegionCode = NewType(
    "RegionCode",
    Annotated[
        str,
        RegionCodeConstraint(),
        Field(description="An ISO 3166-2 principal subdivision code"),
    ],
)  # type: ignore [type-arg]
"""
An ISO 3166-2 principal subdivision code.
"""

SnakeCaseString = NewType("SnakeCaseString", Annotated[str, SnakeCaseConstraint()])
"""
A string that looks like a snake case identifier, like a Python variable name (*e.g.*, `foo_bar`).
"""

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
"""
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
"""
A wikidata ID, as found on https://www.wikidata.org/.

- `"Q42"`
- `"Q11643"`
- `"Q116257497"`
"""
