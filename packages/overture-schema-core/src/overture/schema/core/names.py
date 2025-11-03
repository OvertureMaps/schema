"""
Names for features and their child attributes.

This module includes all Overture's standard naming types. It supports multi-language names,
multiple name variants, and naming rules for specifying conditional or partial names to things.

Examples
--------
Create a feature type that can have a name:

>>> from typing import Literal
>>> from overture.schema.core import OvertureFeature
>>> from overture.schema.system.primitive import Geometry
>>> class MyFeature(OvertureFeature[Literal["mytheme"], Literal["mytype"]], Named):
...     pass
...
>>> my_feature = MyFeature(
...    id='12345678-1234-5678-9abc-123456789012',
...    geometry=Geometry.from_wkt('POINT(0 0)'),
...    theme='mytheme',
...    type='mytype',
...    version=1,
...    names=Names(primary='my feature primary name')
... )

Create an arbitrary Pydantic model that can have a name:

>>> from pydantic import BaseModel
>>> from overture.schema.system.model_constraint import no_extra_fields
>>> @no_extra_fields
... class MyModel(Named):
...     myfield: int
...
>>> MyModel(names=Names(primary='foo'), myfield=42)
MyModel(names=Names(primary='foo', common=None, rules=None), myfield=42)

Create a simple names structure with names in multiple languages:

>>> names = Names(
...     primary='Le Léman',
...     common={
...         'de': 'Genfersee',
...         'en': 'Lake Geneva',
...         'fr': 'Le Léman',
...     }
... )

Create a name structure with official, alternate, and short names:

>>> names = Names(
...     primary='City of New York',
...     rules=[
...         NameRule(value='New York', variant='official', language='en'),
...         NameRule(value='New York City', variant='alternate', language='en'),
...         NameRule(value='The Big Apple', variant='alternate', language='en'),
...         NameRule(value='NYC', variant='alternate'),
...     ]
... )

Create a name structure for a street where the name changes based on the side of the street.

>>> from overture.schema.core.scoping import Side
>>> names = Names(
...     primary='Fir St',
...     rules=[
...         NameRule(value='2 Ave', variant='common', between=[0, 0.3], side=Side.LEFT),
...         NameRule(value='Fir St', variant='common', between=[0.3, 1], side=Side.LEFT),
...         NameRule(value='Fir St', variant='common', side=Side.RIGHT),
...     ]
... )
"""

import textwrap
from typing import Annotated, NewType

from pydantic import BaseModel, Field

from overture.schema.core.models import Perspectives
from overture.schema.core.scoping import Scope, scoped
from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.string import (
    LanguageTag,
    StrippedString,
)

CommonNames = NewType(
    "CommonNames",
    Annotated[
        dict[
            Annotated[
                LanguageTag,
                Field(
                    description=textwrap.dedent("""
                        A mapping from language to the most commonly used or recognized name in that
                        language.

                        Each entry consists of a key that is an IETF BCP 47 language tag; and a
                        value that reflects the common name in the language represented by the key's
                        language tag.

                        The validating regular expression for this property follows the pattern
                        described in https://www.rfc-editor.org/rfc/bcp/bcp47.txt with the exception
                        that private use tags are not supported.
                    """).strip(),
                ),
            ],
            StrippedString,
        ],
        Field(json_schema_extra={"additionalProperties": False}),
    ],
)
"""A mapping from language to the most commonly used or recognized name in that language."""


class NameVariant(str, DocumentedEnum):
    """
    Name variant used in a `NameRule`.
    """

    COMMON = (
        "common",
        textwrap.dedent("""
            The most commonly used or recognized name for a feature in the specified language.

            In a `Names` value, most common names will appear in the `Names.common` field and will
            not need to be specified as `NameRule` values in `Names.rules`. This member of the
            enumeration should only be used to construct a `NameRule` if the common name needs to
            be scoped in some way and therefore cannot be accurately represented in `CommonNames`.
        """).strip(),
    )
    OFFICIAL = (
        "official",
        textwrap.dedent("""
            The legally or administratively recognized name, often used by government agencies or
            official documents.
        """).strip(),
    )
    ALTERNATE = (
        "alternate",
        textwrap.dedent("""
            An alternative name, which may be a historical name, a local colloquial name, or some
            other well-known name is not the common name.
        """).strip(),
    )
    SHORT = (
        "short",
        textwrap.dedent("""
            An abbreviated or shortened version of the name, which may be an acronym or some other
            commonly-used short form. An example is "NYC" for New York City.
        """).strip(),
    )


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE, Scope.SIDE)
class NameRule(BaseModel):
    """
    A rule that can be evaluated to determine the name in advanced scenarios.

    Name rules are used for cases where the primary name is not sufficient; the common name is not
    the right fit for the use case and another variant is needed; or where the name only applies in
    certain specific circumstances.

    Examples might include:
    - An official, alternate, or short name.
    - A name that only applies to part of a linear path like a road segment (geometric range
      scoping).
    - A name that only applies to the left or right side of a linear path like a road segment (side
      scoping).
    - A name that is only accepted by some political perspectives.
    """

    # Required

    value: Annotated[
        StrippedString, Field(description="The actual name value.", min_length=1)
    ]
    variant: NameVariant = Field(description="The name variant for this name rule.")

    # Optional

    language: Annotated[
        LanguageTag | None,
        Field(
            description=textwrap.dedent("""
                The language in which the name `value` is specified, if known, as an IETF BCP 47
                language tag.
            """).strip()
        ),
    ] = None
    perspectives: (
        Annotated[
            Perspectives,
            Field(
                description="Political perspectives from which a named feature is viewed."
            ),
        ]
        | None
    ) = None


@no_extra_fields
class Names(BaseModel):
    """Multilingual names container."""

    # Required

    primary: Annotated[
        StrippedString, Field(min_length=1, description="The most commonly used name.")
    ]

    # Optional

    common: CommonNames | None = None
    rules: Annotated[
        list[NameRule] | None,
        Field(
            description="Rules for names that cannot be specified in the simple common names property. These rules can cover other name variants such as official, alternate, and short; and they can optionally include geometric scoping (linear referencing) and side-of-road scoping for complex cases.",
        ),
    ] = None


class Named(BaseModel):
    """Properties defining the names of a model."""

    names: Names | None = None
