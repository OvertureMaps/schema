from typing import Annotated, NewType

from pydantic import Field

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
# todo - Vic - Pdoc string
