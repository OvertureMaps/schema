import textwrap
from typing import Annotated, Generic, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from typing_extensions import Self

from overture.schema.core.sources import Sources
from overture.schema.system.feature import Feature
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.model_constraint import no_extra_fields
from overture.schema.system.primitive import (
    Geometry,
)
from overture.schema.system.ref import Id, Identified
from overture.schema.system.string import (
    CountryCodeAlpha2,
)

from .enums import PerspectiveMode
from .types import (
    FeatureVersion,
    Level,
    MaxZoom,
    MinZoom,
    Prominence,
    SortKey,
)

ThemeT = TypeVar("ThemeT", bound=str)
TypeT = TypeVar("TypeT", bound=str)


class OvertureFeature(Identified, Feature, Generic[ThemeT, TypeT]):
    """Base class for all Overture features."""

    # Only used to suport `ext_*` fields, which are on a deprecation path.
    model_config = ConfigDict(extra="allow")

    # Required

    id: Id = Field(
        description="A feature ID. This may be an ID associated with the Global Entity Reference System (GERS) if—and-only-if the feature represents an entity that is part of GERS."
    )  # type: ignore[assignment]
    theme: ThemeT
    # this is an enum in the JSON Schema, but that prevents Feature from being extended
    type: TypeT
    geometry: Geometry
    version: FeatureVersion

    # Optional

    sources: Sources | None = None

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        extra = self.model_extra
        invalid_extra_fields = (
            [f for f in extra.keys() if not f.startswith("ext_")] if extra else ()
        )
        if invalid_extra_fields:
            maybe_plural = "s" if len(invalid_extra_fields) > 1 else ""
            raise ValueError(
                f"invalid extra field name{maybe_plural}: {', '.join(invalid_extra_fields)} "
                "(extra fields are temporarily allowed, but only if their names start with 'ext_', "
                "but all extra field name support in {self.__class__.name} is on a deprecation path "
                "and will be removed)"
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

                    This feature is a on a deprecation path and will be removed once the schema is
                    fully migrated to Pydantic.
                """).strip(),
            }
        }
        properties_object_schema["additionalProperties"] = False

        return json_schema


@no_extra_fields
class Perspectives(BaseModel):
    """Political perspectives container."""

    # Required

    mode: Annotated[
        PerspectiveMode,
        Field(
            description="Whether the perspective holder accepts or disputes this name."
        ),
    ]
    countries: Annotated[
        list[CountryCodeAlpha2],
        Field(
            min_length=1, description="Countries holding the given mode of perspective."
        ),
        UniqueItemsConstraint(),
    ]


class Stacked(BaseModel):
    """Properties defining feature Z-order, i.e., stacking order."""

    level: Level | None = 0  # type: ignore[assignment]


@no_extra_fields
class CartographicHints(BaseModel):
    """Defines cartographic hints for optimal use of Overture features in map-making."""

    # Optional

    prominence: Prominence | None = None
    min_zoom: MinZoom | None = None
    max_zoom: MaxZoom | None = None
    sort_key: SortKey | None = None


class CartographicallyHinted(BaseModel):
    cartography: Annotated[CartographicHints | None, Field(title="cartography")] = None
