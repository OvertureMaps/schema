"""Name-related models for Overture Maps features."""

from enum import Enum
from typing import Annotated, Literal

from pydantic import Field

from overture.schema.core.base import StrictBaseModel
from overture.schema.core.perspectives import Perspectives
from overture.schema.validation import (
    PatternPropertiesDictConstraint,
)
from overture.schema.validation.types import (
    LanguageTag,
    LinearReferenceRange,
    TrimmedString,
)


class NameVariant(str, Enum):
    """Name variant types."""

    COMMON = "common"
    OFFICIAL = "official"
    ALTERNATE = "alternate"
    SHORT = "short"


class NameRule(StrictBaseModel):
    """Name rule with variant and language specification."""

    # Required

    value: TrimmedString = Field(..., min_length=1, description="Name value")
    variant: NameVariant = Field(..., description="Name variant type")

    # Optional

    between: LinearReferenceRange = Field(
        default=None, description="Linear referencing range"
    )
    language: LanguageTag = Field(default=None, description="IETF BCP-47 language tag")
    perspectives: Perspectives = Field(
        default=None, description="Political perspectives"
    )
    side: Literal["left", "right"] = Field(
        default=None, description="Side specification"
    )


class NamesContainer(StrictBaseModel):
    """Multilingual names container."""

    # Required

    primary: TrimmedString = Field(..., min_length=1, description="Primary name")

    # Optional

    common: Annotated[
        dict[LanguageTag, TrimmedString], PatternPropertiesDictConstraint()
    ] = Field(default=None, description="Common names by language")
    rules: list[NameRule] = Field(default=None, description="Name rules")
