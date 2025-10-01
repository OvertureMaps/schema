"""
constraint
==========
Reusable constraints.

todo - vic


Modules
-------
constraint : module
    Base constraint type.
collection : module
    Constraints for collection fields.
string : module
    Constraints for string fields.

"""

from .collection import (
    CollectionConstraint,
    UniqueItemsConstraint,
)
from .constraint import Constraint
from .string import (
    CountryCodeConstraint,
    HexColorConstraint,
    JsonPointerConstraint,
    LanguageTagConstraint,
    NoWhitespaceConstraint,
    PatternConstraint,
    PhoneNumberConstraint,
    RegionCodeConstraint,
    StringConstraint,
    StrippedConstraint,
    WikidataIdConstraint,
)

__all__ = [
    "Constraint",
    "CollectionConstraint",
    "UniqueItemsConstraint",
    "CountryCodeConstraint",
    "HexColorConstraint",
    "JsonPointerConstraint",
    "LanguageTagConstraint",
    "NoWhitespaceConstraint",
    "PatternConstraint",
    "PhoneNumberConstraint",
    "RegionCodeConstraint",
    "StringConstraint",
    "StrippedConstraint",
    "WikidataIdConstraint",
]
