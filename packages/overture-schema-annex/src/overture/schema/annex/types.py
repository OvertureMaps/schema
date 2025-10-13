from typing import Annotated, NewType

from pydantic import Field

LicenseShortname = NewType(
    "LicenseShortname",
    Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9._+\-]+$"),
    ],
)
