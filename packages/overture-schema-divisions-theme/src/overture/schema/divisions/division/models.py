"""Division models for Overture Maps divisions theme."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from overture.schema.core import (
    OvertureFeature,
)
from overture.schema.core.models import (
    CartographicallyHinted,
    Named,
    Names,
    Perspectives,
)
from overture.schema.core.scoping.side import Side
from overture.schema.core.types import CommonNames
from overture.schema.system.field_constraint import (
    UniqueItemsConstraint,
)
from overture.schema.system.model_constraint import (
    forbid_if,
    no_extra_fields,
    require_if,
)
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
    int32,
)
from overture.schema.system.ref import Id
from overture.schema.system.string import CountryCodeAlpha2, RegionCode, WikidataId

from ..enums import IS_COUNTRY, DivisionClass, PlaceType
from ..models import CapitalOfDivisionItem
from ..types import Hierarchy


@no_extra_fields
class Norms(BaseModel):
    """Local norms and standards."""

    # Optional

    driving_side: Annotated[
        Side | None,
        Field(
            description="Side of the road on which vehicles drive in the division.",
        ),
    ] = None


@forbid_if(["parent_division_id"], IS_COUNTRY)
@require_if(["parent_division_id"], ~IS_COUNTRY)
class Division(
    OvertureFeature[Literal["divisions"], Literal["division"]],
    Named,
    CartographicallyHinted,
):
    """Divisions are recognized official or non-official organizations of people as seen
    from a given political perspective.

    Examples include countries, provinces, cities, towns, neighborhoods, etc.
    """

    model_config = ConfigDict(title="division")

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POINT),
        Field(
            description="""Approximate location of a position commonly associated with the real-world entity modeled by the division feature.""",
        ),
    ]

    # Required

    names: Names
    subtype: PlaceType
    country: Annotated[
        CountryCodeAlpha2,
        Field(
            description="""ISO 3166-1 alpha-2 country code of the country or country-like entity, that this division represents or belongs to.

If the entity this division represents has a country code, the country property contains it. If it does not, the country property contains the country code of the first division encountered by traversing the parent_division_id chain to the root.

For example:
    - The country value for the United States is 'US'
    - The country value for New York City is 'US'
    - The country value for Puerto Rico, a dependency of the US,
    is 'PR'.
    - The country value for San Juan, Puerto Rico is 'PR'.

If an entity has an internationally-recognized ISO 3166-1 alpha-2 country code, it should always be used. In cases where the schema requires the code but no internationally-recognized code is available, a synthetic code may be used provided it does not conflict with any internationally-recognized codes.""",
        ),
    ]
    hierarchies: Annotated[
        list[Hierarchy],
        Field(
            min_length=1,
            description="""Hierarchies in which this division participates.

Every division participates in at least one hierarchy. Most participate in only one. Some divisions may participate in more than one hierarchy, for example if they are claimed by different parent divisions from different political perspectives; or if there are other real-world reasons why the division or one of its ancestors has multiple parents.

The first hierarchy in the list is the default hierarchy, and the second-to-last entry in the default hierarchy (if there is such an entry) always corresponds to the `parent_division_id' property. The ordering of hierarchies after the first one is arbitrary.""",
        ),
        UniqueItemsConstraint(),
    ]
    parent_division_id: Annotated[
        Id | None,
        Field(
            min_length=1,
            description="""Division ID of this division's parent division.

Not allowed for top-level divisions (countries) and required for all other divisions.

The default parent division is the parent division as seen from the default political perspective, if there is one, and is otherwise chosen somewhat arbitrarily. The hierarchies property can be used to inspect the exhaustive list of parent divisions.""",
        ),
    ] = None

    # Optional

    class_: Annotated[DivisionClass | None, Field(alias="class")] = None
    local_type: Annotated[
        CommonNames | None,
        Field(
            description="""Local name for the subtype property, optionally localized.

For example, the Canadian province of Quebec has the subtype 'region', but in the local administrative hierarchy it is referred to as a 'province'. Similarly, the Canadian Yukon territory also has subtype 'region', but is locally called a 'territory'.

This property is localized using a standard Overture names structure. So for example, in Switzerland the top-level administrative subdivision corresponding to subtype 'region' is the canton, which is may be translated in each of Switzerland's official languages as, 'canton' in French, 'kanton' in German, 'cantone' in Italian, and 'chantun' in Romansh.""",
        ),
    ] = None
    region: Annotated[
        RegionCode | None,
        Field(
            description="""ISO 3166-2 principal subdivision code of the subdivision-like entity this division represents or belongs to.

If the entity this division represents has a principal subdivision code, the region property contains it. If it does not, the region property contains the principal subdivision code of the first division encountered by traversing the parent_division_id chain to the root.

For example:
    - The region value for the United States is omitted.
    - The region value for the U.S. state of New York is 'US-NY'.
    - The region value for New York City is 'US-NY', which it
    inherits from the state of New York.
    - The region value for Puerto Rico is 'US-PR'.""",
        ),
    ] = None
    perspectives: Annotated[
        Perspectives | None,
        Field(
            description="""Political perspectives from which this division is considered to be an accurate representation.

If this property is absent, then this division is not known to be disputed from any political perspective. Consequently, there is only one division feature representing the entire real world entity.

If this property is present, it means the division represents one of several alternative perspectives on the same real-world entity.

There are two modes of perspective:

1. `accepted_by` means the representation of the division is accepted by the listed entities and would be included on a map drawn from their perspective.

2. `disputed_by` means the representation of the division is disputed by the listed entities and would be excluded from a map drawn from their perspective.

When drawing a map from the perspective of a given country, one would start by gathering all the undisputed divisions (with no `perspectives` property), and then adding to that first all divisions explicitly accepted by the country, and second all divisions not explicitly disputed by the country.""",
        ),
    ] = None
    # If we decide to include default language, it will go here. But is it really generally-useful information?
    norms: Annotated[
        Norms | None,
        Field(
            description="""Collects information about local norms and rules within the division that are generally useful for mapping and map-related use cases.

If the norms property or a desired sub-property of the norms property is missing on a division, but at least one of its ancestor divisions has the norms property and the desired sub-property, then the value from the nearest ancestor division may be assumed.""",
        ),
    ] = None
    population: Annotated[
        int32 | None, Field(ge=0, description="Population of the division")
    ] = None
    capital_division_ids: Annotated[
        list[Id] | None,
        Field(
            min_length=1,
            description="""Division IDs of this division's capital divisions. If present, this property will refer to the division IDs of the capital cities, county seats, etc. of a division.""",
        ),
        UniqueItemsConstraint(),
    ] = None
    capital_of_divisions: Annotated[
        list[CapitalOfDivisionItem] | None,
        Field(
            min_length=1,
            description="Division IDs and subtypes of divisions this division is a capital of.",
        ),
        UniqueItemsConstraint(),
    ] = None
    wikidata: WikidataId | None = None
