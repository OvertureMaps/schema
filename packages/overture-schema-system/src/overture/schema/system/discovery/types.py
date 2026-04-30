"""Types and data classes for Overture schema discovery system."""

from collections.abc import Callable, Iterable
from typing import TypeAlias

from pydantic import BaseModel

from .models import ModelKey, TagProviderKey

TagProvider: TypeAlias = Callable[[type[BaseModel], ModelKey, set[str]], Iterable[str]]
ModelDict: TypeAlias = dict[ModelKey, type[BaseModel]]
TagProviderDict: TypeAlias = dict[TagProviderKey, TagProvider]
