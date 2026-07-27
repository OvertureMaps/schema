"""
The Overture feature, an Overture-specific refinement of the base `Feature` type defined in the
system package.
"""

import textwrap
from typing import Annotated, Generic, NewType, TypeVar

from pydantic import (
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from typing_extensions import Self

from overture.schema.system.feature import Feature
from overture.schema.system.numeric import int32
from overture.schema.system.ref import Id, Identified

from .sources import Sources

ThemeT = TypeVar("ThemeT", bound=str)
TypeT = TypeVar("TypeT", bound=str)

FeatureVersion = NewType(
    "FeatureVersion", Annotated[int32, Field(ge=0, description="")]
)


class OvertureFeature(Identified, Feature, Generic[ThemeT, TypeT]):
    """
    Overture feature, the base class for all Overture features types.

    An `OvertureFeature` extends the fundamental `Feature` type by:
    - Making the basic ``id`` field required instead of optional.
    - Adding required fields ``theme``, ``type``, and ``version``.
    - Adding the optional field ``sources``.
    """

    # Only used to support `ext_*` fields, which are on a deprecation path.
    model_config = ConfigDict(extra="allow")

    # Required

    # Repeating `id` from the superclass `Feature` to make it mandatory: it is optional in the
    # superclass.
    id: Id = Field(
        description="A feature ID. This may be an ID associated with the Global Entity Reference System (GERS) if—and-only-if the feature represents an entity that is part of GERS."
    )  # type: ignore[assignment]
    theme: ThemeT
    type: TypeT
    # Superclass `Feature` provides `geometry` and `bbox`.
    version: FeatureVersion

    # Optional

    sources: Sources | None = None

    @model_validator(mode="after")
    def __validate_ext_fields__(self) -> Self:
        extra = self.model_extra
        invalid_extra_fields = (
            [f for f in extra.keys() if not f.startswith("ext_")] if extra else ()
        )
        if invalid_extra_fields:
            maybe_plural = "s" if len(invalid_extra_fields) > 1 else ""
            raise ValueError(
                f"invalid extra field name{maybe_plural}: {', '.join(invalid_extra_fields)} "
                f"(extra fields are temporarily allowed, but only if their names start with 'ext_', "
                f"but all extra field name support in {self.__class__.__name__} is on a deprecation path "
                f"and will be removed)"
            )
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        schema: core_schema.CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        # Get the main Feature JSON schema.
        json_schema = super().__get_pydantic_json_schema__(schema, handler)

        # Explicitly allow `ext_*` properties, but no other properties, in the properties object.
        # This feature only exists to get to initial parity between the hand-written JSON Schema and
        # the Pydantic port. Once Pydantic is the primary, it will be deprecated.
        properties_object_schema = json_schema["properties"]["properties"]
        properties_object_schema["patternProperties"] = {
            "^ext_.*$": {
                "description": textwrap.dedent("""
                    Additional top-level properties are allowed if prefixed by `ext_`.

                    This feature is on a deprecation path and will be removed once the schema is
                    fully migrated to Pydantic.
                """).strip(),
            }
        }
        properties_object_schema["additionalProperties"] = False

        return json_schema
