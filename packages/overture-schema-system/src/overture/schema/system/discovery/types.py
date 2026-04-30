"""Types and data classes for Overture schema discovery system."""

from collections.abc import Callable, Iterable
from typing import Any, TypeAlias

from pydantic import BaseModel

from .models import ModelKey, TagProviderKey

# The first argument is the value loaded from an `overture.models` entry
# point. That is usually a `type[BaseModel]`, but discriminated-union
# features (e.g. `Segment`) load as `Annotated[Union[...], Field(...)]`
# expressions, which are not `type` objects. Providers should use
# `overture.schema.system.typing_util.collect_types` to walk to concrete
# classes.
TagProvider: TypeAlias = Callable[[Any, ModelKey, set[str]], Iterable[str]]
ModelDict: TypeAlias = dict[ModelKey, type[BaseModel]]
TagProviderDict: TypeAlias = dict[TagProviderKey, TagProvider]
