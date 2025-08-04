from enum import Enum


class PlaceType(str, Enum):
    """Category of the division from a finite, hierarchical, ordered list of categories (e.g. country, region, locality, etc.) similar to a Who's on First placetype."""

    # Largest unit of independent sovereignty, e.g. the United States, France.
    COUNTRY = "country"

    # A place that is not exactly a sub-region of a country but is dependent on a parent country for
    # defence, passport control, etc., e.g. Puerto Rico.
    DEPENDENCY = "dependency"

    # A bundle of regions, e.g. England, Scotland, Île-de-France. These exist mainly in Europe.
    MACROREGION = "macroregion"

    # A state, province, region, etc. Largest sub-country administrative unit in most countries,
    # except those that have dependencies or macro-regions.
    REGION = "region"

    # A bundle of counties, e.g. Inverness. These exist mainly in Europe.
    MACROCOUNTY = "macrocounty"

    # Largest sub-region administrative unit in most countries, unless they have macrocounties.
    COUNTY = "county"

    # An administrative unit existing in some parts of the world that contains localities or
    # populated places, e.g. département de Paris. Often the contained places do not have
    # independent authority. Often, but not exclusively, found in Europe.
    LOCALADMIN = "localadmin"

    # A populated place that may or may not have its own administrative authority.
    LOCALITY = "locality"

    # A local government unit subordinate to a locality.
    BOROUGH = "borough"

    # A super-neighborhood that contains smaller divisions of type neighborhood, e.g. BoCaCa (Boerum
    # Hill, Cobble Hill, and Carroll Gardens).
    MACROHOOD = "macrohood"

    # A neighborhood. Most neighborhoods will be just this, unless there's enough granular detail to
    # justify incroducing macrohood or microhood divisions.
    NEIGHBORHOOD = "neighborhood"

    # A mini-neighborhood that is contained within a division of type neighborhood.
    MICROHOOD = "microhood"


class DivisionClass(str, Enum):
    """Division-specific class designations."""

    # A extensive, large human settlement.
    # Example: Tokyo, Japan.
    MEGACITY = "megacity"

    # A relatively large, permanent human settlement.
    # Example: Guadalajara, Mexico.
    CITY = "city"

    # A medium-sized human settlement that is smaller than a city, but larger than a village.
    # Example: Walldürn, Germany.
    TOWN = "town"

    # A smaller human settlement that is smaller than a town, but larger than a hamlet.
    # Example: Wadi El Karm, Lebanon.
    VILLAGE = "village"

    # A small, isolated human settlement in a rural area
    # Example: Tjarnabyggð, Iceland.
    HAMLET = "hamlet"
