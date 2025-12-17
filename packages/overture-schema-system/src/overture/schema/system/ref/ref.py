"""
Relationships and references between related entities.
"""

from dataclasses import dataclass
from enum import Enum

from .id import Identified


class Relationship(Enum):
    """
    Category of relationship between two values, where the first value refers to the second one.

    If we call the first value, the one that holds the reference, the relator; and the second value,
    value, the one that is referred to, as the relatee; then this value represents the relationship
    from the perspective of the relator.
    """

    def __init__(self, value: str, doc: str) -> None:
        self._value_ = value
        self.__doc__ = doc

    BELONGS_TO = "belongs_to", "The relator belongs to the relatee"
    BOUNDARY_OF = "boundary_of", "The relator is a boundary of the relatee"
    CONNECTS_TO = "connects_to", "The relator connects to the relatee"


@dataclass(frozen=True, slots=True)
class Reference:
    """
    Annotation class describing a relationship between two values where the relatee is referenced
    by its unique ID.

    Parameters
    ----------
    relationship : Relationship
        The kind of relationship between the relator (the type annotated with an instance of this
        class that is said to "hold the reference") and the relatee.
    relatee : type[Identified]
        The type that is the object or target of the relationship ("the thing related to").

    Attributes
    ----------
    relationship : Relationship
        The kind of relationship between the relator (the type annotated with an instance of this
        class that is said to "hold the reference") and the relatee.
    relatee : type[Identifier]
        The type that is the object or target of the relationship ("the thing related to").

    Examples
    --------
    A hypothetical ParkBench model holds a foreign key relationship to the model of the park the
    bench belongs to.

    >>> from typing import Annotated
    >>> from overture.schema.system.ref import Id, Identified
    >>> class Park(Identified):
    ...     pass
    >>> class ParkBench(Identified):
    ...    park_id: Annotated[Id, Reference(Relationship.BELONGS_TO, Park)]
    """

    relationship: Relationship
    relatee: type[Identified]

    def __post_init__(self) -> None:
        if not isinstance(self.relationship, Relationship):
            raise TypeError(
                f"`relationship` must be a member of the `Relationship` enumeration, but {self.relationship} is a `{type(self.relationship).__name__}`"
            )
        if not isinstance(self.relatee, type) or not issubclass(
            self.relatee, Identified
        ):
            raise TypeError(
                f"`relatee` must be a type derived from `Identified`, but {self.relatee} is a `{type(self.relatee).__name__}`"
            )
