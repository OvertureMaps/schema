"""Types and data classes for Overture schema discovery system."""

from collections.abc import Callable
from typing import TypeAlias

from pydantic import BaseModel

from .models import ModelKey, TagProviderKey

TagProvider: TypeAlias = Callable[[type[BaseModel], ModelKey, set[str]], set[str]]
ModelDict: TypeAlias = dict[ModelKey, type[BaseModel]]
TagProviderDict: TypeAlias = dict[TagProviderKey, TagProvider]
