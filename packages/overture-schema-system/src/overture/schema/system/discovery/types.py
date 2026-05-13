"""Types and data classes for Overture schema discovery system."""

from collections.abc import Callable, Iterable
from typing import TypeAlias

from pydantic import BaseModel

from .keys import ModelKey, TagProviderKey

# Tag providers receive the concrete `BaseModel` subclasses for an entry
# point. For class entries this is a one-element iterable; for
# discriminated unions it is every arm collected by `collect_types`.
TagProvider: TypeAlias = Callable[
    [Iterable[type[BaseModel]], ModelKey, set[str]],
    Iterable[str],
]
ModelDict: TypeAlias = dict[ModelKey, type[BaseModel]]
TagProviderDict: TypeAlias = dict[TagProviderKey, TagProvider]
