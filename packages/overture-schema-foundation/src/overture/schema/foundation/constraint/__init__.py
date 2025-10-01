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
    Constraints for collections

"""

from .collection import (
    CollectionConstraint,
    UniqueItemsConstraint,
)
from .constraint import Constraint

__all__ = [
    "Constraint",
    "CollectionConstraint",
    "UniqueItemsConstraint",
]
