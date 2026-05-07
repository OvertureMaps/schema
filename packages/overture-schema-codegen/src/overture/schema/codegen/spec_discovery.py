"""Bridge discovered models to extracted specs.

`discover_models` yields `(ModelKey, entry)` pairs where each entry is either
a concrete Pydantic model class or a discriminated-union type alias. This
module turns one such pair into its `ModelSpec`, applying the partition layout
and entry point uniformly so every call site shares the same extraction. It
sits at the orchestration tier (alongside `cli`), importing downward into
extraction and layout.
"""

from __future__ import annotations

from overture.schema.system.discovery import ModelKey

from .extraction.model_extraction import extract_model
from .extraction.specs import (
    ModelSpec,
    is_model_class,
    is_union_alias,
    partitions_from_tags,
)
from .extraction.union_extraction import extract_union
from .layout.module_layout import entry_point_class

__all__ = ["extract_model_spec"]


def extract_model_spec(key: ModelKey, entry: object) -> ModelSpec | None:
    """Extract the `ModelSpec` for one discovered `(key, entry)` pair.

    Returns None when `entry` is neither a concrete model class nor a union
    alias, so callers can skip non-model entries with a single check.
    """
    partitions = partitions_from_tags(key.tags)
    if is_model_class(entry):
        return extract_model(entry, entry_point=key.entry_point, partitions=partitions)
    if is_union_alias(entry):
        return extract_union(
            entry_point_class(key.entry_point),
            entry,
            entry_point=key.entry_point,
            partitions=partitions,
        )
    return None
