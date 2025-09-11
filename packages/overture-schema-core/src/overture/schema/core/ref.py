from dataclasses import dataclass
from enum import Enum

from .models import Feature


class Relationship(Enum):
    """
    Category of relationship between a value that refers to another value.

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
    Annotation class describing a relationship between two feature types.

    Parameters
    ----------
    relationship : Relationship
        The kind of relationship between the relator (the type annotated with an instance of this
        class that is said to "hold the reference") and the relatee.
    relatee : type[Feature]
        The feature type that is the object or target of the relationship ("the thing related to").

    Attributes
    ----------
    relationship : Relationship
        The kind of relationship between the relator (the type annotated with an instance of this
        class that is said to "hold the reference") and the relatee.
    relatee : type[Feature]
        The feature type that is the object or target of the relationship ("the thing related to").

    Examples
    --------
    A hypothetical ParkBench feature type that holds a foreign key relationship to the hypothetical
    Park feature type that the bench belongs to.

    >>> from typing import Annotated
    >>> from overture.schema.core.models import Feature
    >>> from overture.schema.core.ref import Reference, Relationship
    >>> from overture.schema.core.types import Id
    >>> class Park(Feature):
    >>>     pass
    >>> class ParkBench(Feature):
    >>>    park_id: Annotated[Id, Reference(Relationship.BELONGS_TO, Park)]
    """
    relationship: Relationship
    relatee: type[Feature]

    def __post_init__(self) -> None:
       if not isinstance(self.relationship, Relationship):
          raise TypeError(f"`relationship` must be a member of the `Relationship` enumeration, but {self.relationship} is a `{type(self.relationship).__name__}`")
       if not isinstance(self.relatee, type) or not issubclass(self.relatee, Feature):
          raise TypeError(f"`relatee` must be a `Feature` type, i.e. a type that subclasses `Feature`, but {self.relatee} is a `{type(self.relatee).__name__}`")
