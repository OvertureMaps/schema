from dataclasses import dataclass
from enum import Enum

from overture.schema.core.models import Feature


class Relationship(Enum):
    """
    Category of relationship between a value that refers to another value.

    If we call the first value, the one that holds the reference, the referent; and the second
    value, the one that is referred to, as the referee; then this value represents the relationship
    from the perspective of the referent.
    """

    def __init__(self, value: str, doc: str) -> None:
        self._value_ = value
        self.__doc__ = doc

    BELONGS_TO = "belongs_to", "The referent belongs to the referee"
    BOUNDS = "bounds", "The referent bounds the referee"
    CONNECTED_TO = "is_connected_to", "The referent is connected to the referee"


@dataclass(frozen=True, slots=True)
class RefersTo:
    referee: type[Feature]
    relationship: Relationship

    def __post_init__(self) -> None:
       if not isinstance(self.referee, type) or not issubclass(self.referee, Feature):
          raise TypeError(f"`referee` must be a `Feature` type, i.e. a type that subclasses `Feature`, but {self.referee} is a `{type(self.referee).__name__}`")
       if not isinstance(self.relationship, Relationship):
          raise TypeError(f"`relationship` must be a member of the `Relationship` enumeration, but {self.relationship} is a `{type(self.relationship).__name__}`")
