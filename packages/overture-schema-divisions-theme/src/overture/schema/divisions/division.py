"""
The `Division` feature type model and supporting types.
"""

from __future__ import annotations

import textwrap
from typing import Annotated, Literal, NewType

from pydantic import BaseModel, ConfigDict, Field

from overture.schema.common import (
    OvertureFeature,
)
from overture.schema.common.cartography import CartographicallyHinted
from overture.schema.common.models import (
    Perspectives,
)
from overture.schema.common.names import CommonNames, Named, Names
from overture.schema.common.scoping.side import Side
from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.field_constraint import (
    UniqueItemsConstraint,
)
from overture.schema.system.model_constraint import (
    FieldEqCondition,
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
from overture.schema.system.ref import Id, Reference, Relationship
from overture.schema.system.string import (
    CountryCodeAlpha2,
    RegionCode,
    StrippedString,
    WikidataId,
)

from ._common import (
    IS_COUNTRY,
    AdminLevel,
    DivisionSubtype,
)


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


class DivisionClass(str, DocumentedEnum):
    """
    Further classification of a division that is more specific than its `subtype`.

    A division's `class` adds detail to the broad classification found in `DivisionSubtype`.
    """

    MEGACITY = (
        "megacity",
        textwrap.dedent("""
            A very large city or metropolitan area, typically having a population of 10 million or
            more. Example: Tokyo, Japan.
        """).strip(),
    )

    CITY = (
        "city",
        "A large, permanent human settlement. Example: Guadalajara, Mexico.",
    )

    TOWN = (
        "town",
        textwrap.dedent("""
            A medium-sized permanent human settlement that is smaller than a city, but larger than a
            village. Example: Walldürn, Germany.
        """).strip(),
    )

    VILLAGE = (
        "village",
        textwrap.dedent("""
            A smallish permanent human settlement that is smaller than a town, but larger than a
            hamlet. Example: Wadi El Karm, Lebanon.
        """).strip(),
    )

    HAMLET = (
        "hamlet",
        "A very small, isolated human settlement in a rural area. Example: Tjarnabyggð, Iceland.",
    )


@no_extra_fields
class CapitalOfDivisionItem(BaseModel):
    """A division of which the owning division is the capital, together with its subtype."""

    model_config = ConfigDict(frozen=True)

    # Required

    division_id: Annotated[
        Id,
        Field(description="ID of the division whose capital is the current division."),
        Reference(Relationship.HIERARCHY, Division, role="capital_of"),
    ]
    subtype: DivisionSubtype


@no_extra_fields
class HierarchyItem(BaseModel):
    """One division in a hierarchy."""

    model_config = ConfigDict(frozen=True)

    # Required

    division_id: Annotated[
        Id,
        Field(
            description=textwrap.dedent("""
            ID of a division that is an ancestor of the current division.

            In the context of division hierarchies, the ancestor divisions of a division include
            the division itself, and any other division that is an ancestor of the division's parent.
        """).strip()
        ),
        Reference(Relationship.HIERARCHY, Division, role="descendant_of"),
    ]
    subtype: DivisionSubtype
    name: Annotated[
        StrippedString, Field(min_length=1, description="Primary name of the division")
    ]


Hierarchy = NewType(
    "Hierarchy",
    Annotated[
        list[HierarchyItem],
        Field(
            min_length=1,
            description=textwrap.dedent("""
                A hierarchy of divisions, with the first entry being a country; each subsequent
                entry, if any, being a division that is a direct child of the previous entry; and
                the last entry representing the division that contains the hierarchy.

                For example, a hierarchy for the United States is simply [United States]. A
                hierarchy for the U.S. state of New Hampshire would be
                [United States, New Hampshire], and a hierarchy for the city of Concord, NH would be
                [United States, New Hampshire, Merrimack County, Concord].
            """).strip(),
        ),
        UniqueItemsConstraint(),
    ],
)


@forbid_if(["parent_division_id"], IS_COUNTRY)
@require_if(["parent_division_id"], ~IS_COUNTRY)
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.COUNTRY))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.DEPENDENCY))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.MACROREGION))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.REGION))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.MACROCOUNTY))
@require_if(["admin_level"], FieldEqCondition("subtype", DivisionSubtype.COUNTY))
class Division(
    OvertureFeature[Literal["divisions"], Literal["division"]],
    Named,
    CartographicallyHinted,
):
    """
    Divisions are recognized official or non-official organizations of people as seen from a given
    political perspective.

    Examples include countries, provinces, cities, towns, neighborhoods, etc.
    """

    model_config = ConfigDict(title="division")

    # Core
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POINT),
        Field(
            description=textwrap.dedent("""
                Approximate location of a position commonly associated with the real-world entity
                modeled by the division feature.
            """).strip(),
        ),
    ]

    # Required

    names: Annotated[
        Names, Field(description="All known names by which the division is called")
    ]
    subtype: Annotated[
        DivisionSubtype,
        Field(
            description=textwrap.dedent("""
                A broad classification of the division (e.g., country, region, locality, etc.).
            """).strip()
        ),
    ]
    country: Annotated[
        CountryCodeAlpha2,
        Field(
            description=textwrap.dedent("""
                ISO 3166-1 alpha-2 country code of the country or country-like entity, that this
                division represents or belongs to.

                If the entity this division represents has a country code, the country property
                contains it. If it does not, the country property contains the country code of the
                first division encountered by traversing the parent_division_id chain to the root.

                For example:
                - The country value for the United States is 'US'
                - The country value for New York City is 'US'
                - The country value for Puerto Rico, a dependency of the US, is 'PR'.
                - The country value for San Juan, Puerto Rico is 'PR'.

                If an entity has an internationally-recognized ISO 3166-1 alpha-2 country code, it
                should always be used. In cases where the schema requires the code but no
                internationally-recognized code is available, a synthetic code may be used provided
                it does not conflict with any internationally-recognized codes.
            """).strip(),
        ),
    ]
    hierarchies: Annotated[
        list[Hierarchy],
        Field(
            min_length=1,
            description=textwrap.dedent("""
                Hierarchies in which this division participates.

                Every division participates in at least one hierarchy. Most participate in only one.
                Some divisions may participate in more than one hierarchy, for example if they are
                claimed by different parent divisions from different political perspectives; or if
                there are other real-world reasons why the division or one of its ancestors has
                multiple parents.

                The first hierarchy in the list is the default hierarchy, and the second-to-last
                entry in the default hierarchy (if there is such an entry) always corresponds to the
                `parent_division_id` property. The ordering of hierarchies after the first one is
                arbitrary.
            """).strip(),
        ),
        UniqueItemsConstraint(),
    ]
    parent_division_id: Annotated[
        Id | None,
        Field(
            description=textwrap.dedent("""
                Division ID of this division's parent division.

                Not allowed for top-level divisions (countries) and required for all other
                divisions.

                The default parent division is the parent division as seen from the default
                political perspective, if there is one, and is otherwise chosen somewhat
                arbitrarily. The hierarchies property can be used to inspect the exhaustive list of
                parent divisions.
        """).strip()
        ),
        Reference(Relationship.HIERARCHY, Division, role="child_of"),
    ] = None
    admin_level: AdminLevel | None = None

    # Optional

    class_: Annotated[
        DivisionClass | None,
        Field(
            alias="class",
            description=textwrap.dedent("""
                A more specific classification of the division than is provided by `subtype`.
            """).strip(),
        ),
    ] = None
    local_type: Annotated[
        CommonNames | None,
        Field(
            description=textwrap.dedent("""
                Local name for the subtype property, optionally localized.

                For example, the Canadian province of Quebec has the subtype `"region"`, but in the
                local administrative hierarchy it is referred to as a province. Similarly, the
                Canadian Yukon territory also has subtype `"region"`, but is locally called a
                territory.

                This property is localized using a standard Overture names structure. So for
                example, in Switzerland the top-level administrative subdivision corresponding to
                subtype 'region' is the canton, which may be translated in each of Switzerland's
                official languages as, 'canton' in French, 'kanton' in German, 'cantone' in Italian,
                and 'chantun' in Romansh.
            """).strip(),
        ),
    ] = None
    region: Annotated[
        RegionCode | None,
        Field(
            description=textwrap.dedent("""
                ISO 3166-2 principal subdivision code of the subdivision-like entity this division
                represents or belongs to.

                If the entity this division represents has a principal subdivision code, the region
                property contains it. If it does not, the region property contains the principal
                subdivision code of the first division encountered by traversing the
                `parent_division_id` chain to the root.

                For example:
                - The region value for the United States is omitted.
                - The region value for the U.S. state of New York is 'US-NY'.
                - The region value for New York City is 'US-NY', which it inherits from the state
                  of New York.
                - The region value for Puerto Rico is 'US-PR'.
            """).strip(),
        ),
    ] = None
    perspectives: Annotated[
        Perspectives | None,
        Field(
            description=textwrap.dedent("""
                Political perspectives from which this division is considered to be an accurate
                representation.

                If this property is absent, then this division is not known to be disputed from
                any political perspective. Consequently, there is only one division feature
                representing the entire real world entity.

                If this property is present, it means the division represents one of several
                alternative perspectives on the same real-world entity.

                There are two modes of perspective:

                1. `accepted_by` means the representation of the division is accepted by the
                   listed entities and would be included on a map drawn from their perspective.

                2. `disputed_by` means the representation of the division is disputed by the
                   listed entities and would be excluded from a map drawn from their perspective.

                When drawing a map from the perspective of a given country, one would start by
                gathering all the undisputed divisions (with no `perspectives` property), and then
                adding to that first all divisions explicitly accepted by the country, and second
                all divisions not explicitly disputed by the country.
            """).strip(),
        ),
    ] = None
    # If we decide to include default language, it will go here. But is it really generally-useful information?
    norms: Annotated[
        Norms | None,
        Field(
            description=textwrap.dedent("""
                Collects information about local norms and rules within the division that are
                generally useful for mapping and map-related use cases.

                If the norms property or a desired sub-property of the norms property is missing
                on a division, but at least one of its ancestor divisions has the norms property
                and the desired sub-property, then the value from the nearest ancestor division
                may be assumed.
            """).strip(),
        ),
    ] = None
    population: Annotated[
        int32 | None, Field(ge=0, description="Population of the division")
    ] = None
    capital_division_ids: Annotated[
        list[
            Annotated[
                Id,
                Reference(Relationship.HIERARCHY, Division, role="has_as_capital"),
            ]
        ]
        | None,
        Field(
            min_length=1,
            description=textwrap.dedent("""
                Division IDs of this division's capital divisions. If present, this property will
                refer to the division IDs of the capital cities, county seats, etc. of a division.
            """).strip(),
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


# Materialize forward references to `Division`.
def __materialize_forward_refs(model_class: type[BaseModel]) -> None:
    rebuilt: bool | None = model_class.model_rebuild()
    assert rebuilt, (
        f"expected `{model_class.__name__}` to be rebuilt to materialize forward references to `{Division.__name__}`, but it wasn't"
    )


__materialize_forward_refs(CapitalOfDivisionItem)
__materialize_forward_refs(HierarchyItem)
