"""
Shared building blocks common to all Overture theme packages.

The `OvertureFeature` base class and the reusable feature components — naming, sources,
cartographic hints, scoping, and more — that theme packages compose to define their
feature types.

Subpackages
-----------
- :mod:`cartography <overture.schema.common.cartography>` Cartographic display hints.
- :mod:`confidence <overture.schema.common.confidence>` The `ConfidenceScore` type.
- :mod:`feature <overture.schema.common.feature>` The `OvertureFeature` base class and its
  supporting types (`FeatureVersion`, `ThemeT`, `TypeT`).
- :mod:`level <overture.schema.common.level>` Feature Z-order / stacking (`Level`, `Stacked`).
- :mod:`names <overture.schema.common.names>` Multilingual naming with variants and rules.
- :mod:`perspectives <overture.schema.common.perspectives>` Political perspectives on disputed
  data.
- :mod:`scoping <overture.schema.common.scoping>` Scoped, conditionally-applicable field values.
- :mod:`sources <overture.schema.common.sources>` Data provenance and source attribution.
- :mod:`unit <overture.schema.common.unit>` Units of measure.
"""

from . import (
    cartography,
    confidence,
    feature,
    level,
    names,
    perspectives,
    scoping,
    sources,
    unit,
)
from .feature import FeatureVersion, OvertureFeature, ThemeT, TypeT

__all__ = [
    "cartography",
    "confidence",
    "feature",
    "FeatureVersion",
    "level",
    "names",
    "OvertureFeature",
    "perspectives",
    "scoping",
    "sources",
    "ThemeT",
    "TypeT",
    "unit",
]
