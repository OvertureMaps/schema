"""Geography enums for Overture Maps divisions theme."""

from enum import Enum


class GeographicAreaSubtype(str, Enum):
    """
    The type of geographic area feature.
    
    - functional: Regions defined by functional characteristics or usage patterns
      (e.g., postal codes, economic zones).
    
    - cultural: Regions defined by cultural identity, colloquial usage, or shared
      cultural characteristics (e.g., "East Asia", "California Wine Country").
    """

    FUNCTIONAL = "functional"
    CULTURAL = "cultural"


class GeographicAreaClass(str, Enum):
    """
    Classification of the geographic area feature.
    """

    # Colloquial regions are informal, culturally defined, or commonly referenced areas
    # that do not correspond to official administrative boundaries. Unlike countries,
    # states, counties, or cities—whose boundaries are legally defined—colloquial regions
    # evolve from cultural, historical, economic, or linguistic identity.
    # Examples include South Florida, East Asia, and California Wine Country.
    # Only applicable to cultural subtype.
    COLLOQUIAL = "colloquial"

    # Postal code regions used for mail delivery and routing.
    # Examples include US ZIP codes, UK postcodes, and Canadian postal codes.
    # Only applicable to functional subtype.
    POSTAL = "postal"
