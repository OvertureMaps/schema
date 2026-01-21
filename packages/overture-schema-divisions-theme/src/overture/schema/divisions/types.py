from typing import Annotated, NewType

from pydantic import Field

from overture.schema.system.field_constraint import UniqueItemsConstraint
from overture.schema.system.primitive import uint8

from .models import HierarchyItem

AdminLevel = NewType(
    "AdminLevel",
    Annotated[
        uint8 | None,
        Field(
            description="Integer representing the division's position in its country's administrative hierarchy, where lower numbers correspond to higher level administrative units.",
        ),
    ],
)

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
