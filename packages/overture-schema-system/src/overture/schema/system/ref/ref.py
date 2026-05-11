"""
Relationships and references between related entities.
"""

import re
from dataclasses import dataclass

from overture.schema.system.doc import DocumentedEnum

from .id import Identified

_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


class Relationship(str, DocumentedEnum):
    """
    The kind of relationship that exists between two entities.

    Relationships represent connections between different features or models. Think of them as links
    that connect related pieces of information, like a building part that is structurally part of a
    building; or a division area that is administratively nested under a division.

    Every kind of relationship between two entities says something about how tightly those entities
    are connected, for example: whether one depends on the other to exist (composition); whether
    both members are strongly-connected but independently viable (aggregation); whether one of the
    two is superior while the other is subordinate (hierarchy); or whether they are simply peers
    with a loose affiliation to one another (association).

    The kinds of relationship can be thought of as forming a diamond-shaped hierarchy where
    composition, the strongest form of relationship, appears at the top; aggregation and hierarchy
    as independent relationship types that are weaker than composition but stronger than
    association, appears in the middle; and association, the weakest and least well-defined form of
    relationship, is at the bottom.

               COMPOSITION
               /         \\
         AGGREGATION   HIERARCHY
               \\          /
               ASSOCIATION

    Note that the *kind* of a relationship does not say anything about the *directionality* of the
    relationship. The fact that F is in a hierarchy relationship with G does not, without outside
    information, tell you whether F is the parent or the child.
    """

    COMPOSITION = (
        "composition",
        "A structural whole-part relationship with lifecycle dependency",
    )
    AGGREGATION = "aggregation", "A grouping relationship without lifecycle dependency"
    HIERARCHY = (
        "hierarchy",
        "A parent/child relationship within a hierarchy such as an organization or taxonomy",
    )
    ASSOCIATION = "association", "A peer-level reference without ownership or nesting"


@dataclass(frozen=True, slots=True)
class Reference:
    """
    Annotation class describing a relationship between two values where the relator refers to the
    relatee by the latter's unique ID.

    The relator, which is the subject or source of the relationship, is the type annotated with an
    instance of this class ("the thing that relates"). The relatee is type that is the object or
    target of the relationship ("the thing related to").

    Parameters
    ----------
    relationship : Relationship
        The category of the relationship between the relator and the relatee.
    relatee : type[Identified]
        The type that is the target of the relationship.
    role : str | None
        An optional snake_case descriptor that further describes the relationship from the
        perspective of the relator. This field has no effect on schema validation; it is
        informational metadata for documentation and tooling.

    Examples
    --------
    A hypothetical ParkBench model holds a foreign key relationship to the model of the park that
    contains it.

    >>> from typing import Annotated
    >>> from overture.schema.system.ref import Id, Identified
    >>> class Park(Identified):
    ...     pass
    >>> class ParkBench(Identified):
    ...    park_id: Annotated[Id, Reference(Relationship.COMPOSITION, Park, role="located_in")]
    """

    relationship: Relationship
    relatee: type[Identified]
    role: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.relationship, Relationship):
            raise TypeError(
                f"`relationship` must be a member of the `Relationship` enumeration, "
                f"but {self.relationship} is a `{type(self.relationship).__name__}`"
            )
        if not isinstance(self.relatee, type) or not issubclass(
            self.relatee, Identified
        ):
            raise TypeError(
                f"`relatee` must be a type derived from `Identified`, "
                f"but {self.relatee} is a `{type(self.relatee).__name__}`"
            )
        if self.role is not None and not _SNAKE_CASE_RE.match(self.role):
            raise ValueError(
                f"`role` must be a non-empty snake_case string, but got {self.role!r}"
            )
