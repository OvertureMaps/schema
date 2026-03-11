import textwrap
from typing import Annotated, NewType

from pydantic import Field

from overture.schema.system.doc import DocumentedEnum
from overture.schema.system.model_constraint import FieldEqCondition
from overture.schema.system.primitive import int32

AdminLevel = NewType(
    "AdminLevel",
    Annotated[
        int32,
        Field(
            description=textwrap.dedent("""
                Integer representing the division's position in its country's administrative
                hierarchy, where lower numbers correspond to higher level administrative units.
            """).strip(),
            ge=0,
            le=16,
        ),
    ],
)


class DivisionSubtype(str, DocumentedEnum):
    """
    Category of the division from a finite, hierarchical, ordered list of categories (e.g., country,
    region, locality, etc.) similar to a Who's on First placetype.
    """

    COUNTRY = (
        "country",
        "Largest unit of independent sovereignty, e.g., the United States, France.",
    )

    DEPENDENCY = (
        "dependency",
        textwrap.dedent("""
            A place that is not exactly a sub-region of a country but is dependent on a parent
            country for defence, passport control, etc., e.g., Puerto Rico.
        """).strip(),
    )

    MACROREGION = (
        "macroregion",
        textwrap.dedent("""
            A bundle of regions, e.g., England, Scotland, Île-de-France. These exist mainly in
            Europe.
        """).strip(),
    )

    REGION = (
        "region",
        textwrap.dedent("""
            A state, province, region, etc. Largest sub-country administrative unit in most
            countries, except those that have dependencies or macro-regions.
        """).strip(),
    )

    MACROCOUNTY = (
        "macrocounty",
        "A bundle of counties, e.g. Inverness. These exist mainly in Europe.",
    )

    COUNTY = (
        "county",
        textwrap.dedent("""
            Largest sub-region administrative unit in most countries, unless they have
            macrocounties.
        """).strip(),
    )

    LOCALADMIN = (
        "localadmin",
        textwrap.dedent("""
            An administrative unit existing in some parts of the world that contains localities
            or populated places, e.g. département de Paris. Often the contained places do not
            have independent authority. Often, but not exclusively, found in Europe.
        """).strip(),
    )

    LOCALITY = (
        "locality",
        "A populated place that may or may not have its own administrative authority.",
    )

    BOROUGH = (
        "borough",
        "A local government unit subordinate to a locality.",
    )

    MACROHOOD = (
        "macrohood",
        textwrap.dedent("""
            A super-neighborhood that contains smaller divisions of type neighborhood, e.g.
            BoCaCa (Boerum Hill, Cobble Hill, and Carroll Gardens).
        """).strip(),
    )

    NEIGHBORHOOD = (
        "neighborhood",
        textwrap.dedent("""
            A neighborhood. Most neighborhoods will be just this, unless there's enough granular
            detail to justify introducing macrohood or microhood divisions.
        """).strip(),
    )

    MICROHOOD = (
        "microhood",
        "A mini-neighborhood that is contained within a division of type neighborhood.",
    )


IS_COUNTRY = FieldEqCondition("subtype", DivisionSubtype.COUNTRY)
