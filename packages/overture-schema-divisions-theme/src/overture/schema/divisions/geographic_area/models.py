"""Geography models for Overture Maps divisions theme."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from overture.schema.core import OvertureFeature
from overture.schema.core.cartography import CartographicallyHinted
from overture.schema.core.names import Named, Names
from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
    int32,
)
from overture.schema.system.ref import Id, Reference, Relationship

from ..division.models import Division
from .enums import GeographicAreaClass, GeographicAreaSubtype


class GeographicArea(
    OvertureFeature[Literal["divisions"], Literal["geographic_area"]],
    Named,
    CartographicallyHinted,
):
    """Geographic area features represent functional or cultural regions that may span across
    multiple administrative divisions.

    These regions capture areas defined by shared characteristics, usage patterns, or
    cultural identity rather than formal administrative boundaries.

    Examples include postal code regions (functional) or colloquial regions like "East Asia"
    or "California Wine Country" (cultural).
    """

    model_config = ConfigDict(title="geographic_area")

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
        Field(
            description="Geography geometry MUST be a Polygon or MultiPolygon as defined by GeoJSON schema. The geometry is constructed from associated divisions or available sources.",
        ),
    ]

    # Required

    names: Names
    subtype: Annotated[
        GeographicAreaSubtype,
        Field(
            description="""The type of geography feature.

- functional: Regions defined by functional characteristics or usage patterns (e.g., postal codes, economic zones).

- cultural: Regions defined by cultural identity, colloquial usage, or shared cultural characteristics (e.g., "East Asia", "California Wine Country")."""
        ),
    ]

    class_: Annotated[
        GeographicAreaClass,
        Field(
            alias="class",
            description="Classification of the geography feature. Colloquial class is only allowed for cultural subtype. Postal class is only allowed for functional subtype.",
        ),
    ]

    # Optional

    associated_division_ids: Annotated[
        list[Id] | None,
        UniqueItemsConstraint(),
        Field(
            description="Optional list of division IDs representing the set of divisions that make up this geography region. This property links the geography to the underlying administrative divisions it encompasses or relates to. May be null if the region cannot be precisely mapped to specific administrative divisions.",
            min_length=1,
        ),
        Reference(Relationship.BOUNDARY_OF, Division),
    ] = None

    population: Annotated[
        int32 | None,
        Field(
            description="Optional population represented in the region, if inferable from associated divisions or available sources.",
            ge=0,
        ),
    ] = None

    @model_validator(mode="after")
    def validate_class_rules(self) -> "GeographicArea":
        """Validate class field rules."""
        # Colloquial class only allowed for cultural subtype
        if (
            self.class_ == GeographicAreaClass.COLLOQUIAL
            and self.subtype != GeographicAreaSubtype.CULTURAL
        ):
            raise ValueError("colloquial class is only allowed for cultural subtype")

        # Postal class only allowed for functional subtype
        if (
            self.class_ == GeographicAreaClass.POSTAL
            and self.subtype != GeographicAreaSubtype.FUNCTIONAL
        ):
            raise ValueError("postal class is only allowed for functional subtype")

        return self
