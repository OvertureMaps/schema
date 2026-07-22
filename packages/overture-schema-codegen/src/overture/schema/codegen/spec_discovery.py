"""Bridge discovered models to extracted specs.

`discover_models` yields `(ModelKey, entry)` pairs where each entry is either
a concrete Pydantic model class, a discriminated-union type alias, or a
`RootModel`. This module turns one such pair into a spec, splitting by output:
`extract_model_spec` yields the feature/union `ModelSpec` the pipelines
generate from, while `extract_alias_spec` documents a `RootModel` as a named
alias for markdown. It sits at the orchestration tier (alongside `cli`),
importing downward into extraction and layout.
"""

from __future__ import annotations

from overture.schema.system.discovery import ModelKey

from .extraction.model_extraction import extract_model
from .extraction.newtype_extraction import extract_rootmodel_alias
from .extraction.specs import (
    ModelSpec,
    NewTypeSpec,
    is_model_class,
    is_rootmodel,
    is_union_alias,
    partitions_from_tags,
)
from .extraction.union_extraction import extract_union
from .layout.module_layout import entry_point_class

__all__ = ["extract_alias_spec", "extract_model_spec"]


def extract_model_spec(key: ModelKey, entry: object) -> ModelSpec | None:
    """Extract the feature/union `ModelSpec` for a discovered `(key, entry)`.

    Returns None when `entry` generates no feature or union spec: a
    non-model, non-union entry, or a `RootModel`. A RootModel serializes as
    its bare root value and has no record structure, so extracting it as a
    top-level `RecordSpec` would invent a spurious `root` column;
    `extract_alias_spec` documents it instead. Wherever a RootModel is used
    as a field, `analyze_type` unwraps it to that bare shape.
    """
    if is_rootmodel(entry):
        return None
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


def extract_alias_spec(entry: object) -> NewTypeSpec | None:
    """Extract the markdown alias spec for a `RootModel` entry point.

    A RootModel is a named alias over its bare root value -- like a NewType
    -- so it documents as a `NewTypeSpec`. Returns None for any other entry;
    only RootModels contribute a standalone alias page.
    """
    if is_rootmodel(entry):
        return extract_rootmodel_alias(entry)
    return None
