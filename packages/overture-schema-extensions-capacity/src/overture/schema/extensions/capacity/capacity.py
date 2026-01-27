from inspect import cleandoc
from typing import Annotated, NewType

from pydantic import Field

from overture.schema.buildings import Building
from overture.schema.core import Extends
from overture.schema.places import Place
from overture.schema.system.primitive import uint8

Capacity = NewType(
    "Capacity",
    Annotated[
        uint8,
        Field(
            description=cleandoc(
                """
                The capacity Property indicates the capacity of a Place or a Building.
                """
            ),
        ),
        Extends(Place, Building),
    ],
)
