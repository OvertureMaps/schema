"""Types and data classes for Overture schema discovery system."""

from collections.abc import Callable, Iterable
from typing import TypeAlias

from pydantic import BaseModel

from .keys import ModelKey, TagProviderKey

# Tag providers receive the concrete `BaseModel` subclasses for an entry
# point. For class entries this is a one-element iterable; for
# discriminated unions it is every arm collected by `model_types`.
TagProvider: TypeAlias = Callable[
    [Iterable[type[BaseModel]], ModelKey, set[str]],
    Iterable[str],
]
# Entry-point values are usually `BaseModel` subclasses, but discovery also stores
# union aliases (e.g. `Segment`) and `NewType` scalars verbatim -- use `model_types`
# to get at the concrete model classes behind a value. Keeping the unknown value as
# `object` forces consumers to narrow it before use instead of disabling type checking.
ModelDict: TypeAlias = dict[ModelKey, object]
TagProviderDict: TypeAlias = dict[TagProviderKey, TagProvider]
