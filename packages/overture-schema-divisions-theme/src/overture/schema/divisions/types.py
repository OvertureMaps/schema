from typing import Annotated, NewType

from pydantic import Field

from overture.schema.system.constraint import UniqueItemsConstraint

from .models import HierarchyItem

Hierarchy = NewType(
    "Hierarchy",
    Annotated[
        list[HierarchyItem],
        Field(
            min_length=1,
            description="""A hierarchy of divisions, with the first entry being a country; each subsequent entry, if any, being a division that is a direct child of the previous entry; and the last entry representing the division that contains the hierarchy.

For example, a hierarchy for the United States is simply [United States]. A hierarchy for the U.S. state of New Hampshire would be [United States, New Hampshire], and a hierarchy for the city of Concord, NH would be [United States, New Hampshire, Merrimack County, Concord].""",
        ),
        UniqueItemsConstraint(),
    ],
)
