from enum import Enum
from typing import Annotated, NewType

from pydantic import BaseModel, Field

from overture.schema.core.models import Perspectives
from overture.schema.core.scoping import Scope, scoped
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
                    description="""Each entry consists of a key that is an IETF-BCP47 language tag; and a value that reflects the common name in the language represented by the key's language tag.

The validating regular expression for this property follows the pattern described in https://www.rfc-editor.org/rfc/bcp/bcp47.txt with the exception that private use tags are not supported."""
                ),
            ],
            StrippedString,
        ],
        Field(json_schema_extra={"additionalProperties": False}),
    ],
)


class NameVariant(str, Enum):
    COMMON = "common"
    OFFICIAL = "official"
    ALTERNATE = "alternate"
    SHORT = "short"


@no_extra_fields
@scoped(Scope.GEOMETRIC_RANGE, Scope.SIDE)
class NameRule(BaseModel):
    """Name rule with variant and language specification."""

    # Required

    value: Annotated[StrippedString, Field(min_length=1)]
    variant: NameVariant

    # Optional

    language: LanguageTag | None = None
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
    """Properties defining the names of a feature."""

    names: Names | None = None
