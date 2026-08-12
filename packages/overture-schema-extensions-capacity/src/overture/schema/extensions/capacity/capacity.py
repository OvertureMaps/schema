"""
Capacity extension for Overture Place and Building models.

Demonstrates a *non-model* extension: `Capacity` is a scalar `NewType` that declares its targets via
`Extends(...)` metadata attached with `typing.Annotated`.
"""

from inspect import cleandoc
from typing import Annotated, NewType

from pydantic import Field

from overture.schema.buildings import Building
from overture.schema.places import Place
from overture.schema.system.extension import Extends
from overture.schema.system.numeric import uint8

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
