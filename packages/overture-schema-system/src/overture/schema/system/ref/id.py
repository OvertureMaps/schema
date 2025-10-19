from typing import Annotated, NewType

from pydantic import BaseModel, Field

from overture.schema.system.string import NoWhitespaceString

Id = NewType(
    "Id",
    Annotated[
        NoWhitespaceString,
        Field(
            min_length=1,
            description="A unique identifier",
        ),
    ],
)
"""
A unique identifier.
"""


class Identified(BaseModel):
    """
    A Pydantic model with a mandatory unique ID field.

    Derive from this class to give your model a unique identifier and to make it compatible with
    the reference annotations:

    >>> from pydantic import Field
    >>>
    >>> class House(Identified):
    ...     '''A house.'''
    ...     address: str = Field(description = "Address of the house")
    ...
    >>> from typing import Annotated
    >>> from overture.schema.system.ref import Reference, Relationship
    >>>
    >>> class Room(Identified):
    ...     '''A room within a house.'''
    ...     name: str = Field(description = 'Name of the room')
    ...     house_id: Annotated[
    ...         Id,
    ...        Reference(Relationship.BELONGS_TO, House)
    ...     ] = Field(description = "Unique ID of the house the room belongs to.")

    When combining `Identified` with another Pydantic model that has an `id` field, such as a
    :class:`~overture.schema.system.feature.Feature`, you must derive from `Identified` first in
    order to correctly the *mandatory* `id` field.

    >>> from overture.schema.system.feature import Feature
    >>> class IdentifiedFeature(Identified, Feature):
    ...     pass
    >>> IdentifiedFeature.model_fields['id'].is_required()
    True
    """

    id: Id = Field(description="Unique identifier")
    """Unique identifier of the model."""
