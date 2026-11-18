"""Bridge discovered models to extracted specs.

`discover_models` yields `(ModelKey, entry)` pairs where each entry is either
a concrete Pydantic model class, a discriminated-union type alias, or a
`RootModel`. This module turns one such pair into a spec, splitting by output:
`extract_model_spec` yields the feature/union `ModelSpec` the pipelines
generate from, while `extract_alias_spec` documents a scalar- or
container-rooted `RootModel` as a named alias for markdown. A `RootModel`
whose root is a union or a model is that feature, published under the
wrapper's name.

Its only caller outside tests is `cli`, which hands the specs built here to
the Markdown or PySpark pipeline. It imports `extraction` and `layout` only.
It must not import `cli`, which imports it, nor `markdown` or `pyspark`:
both pipelines consume these specs, so building one must not depend on
either output format.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Annotated, get_args, get_origin

from pydantic import BaseModel

from overture.schema.system.discovery import ModelKey
from overture.schema.system.typing_util import denoted_type

from .extraction.docstring import clean_docstring
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

    A `RootModel` is extracted as what its root denotes, published under the
    entry point's name with the wrapper's docstring: a union root as a
    `UnionSpec`, a model root as that model's `RecordSpec`. Returns None
    for any other entry, including a scalar- or container-rooted RootModel,
    which has no record structure -- extracting it as a `RecordSpec` would
    invent a spurious `root` column -- and which `extract_alias_spec`
    documents instead.
    """
    partitions = partitions_from_tags(key.tags)
    name = entry_point_class(key.entry_point)
    if is_rootmodel(entry):
        spec = _extract_feature(name, denoted_type(entry), key.entry_point, partitions)
        if spec is None:
            return None
        return dataclasses.replace(
            spec,
            name=name,
            description=clean_docstring(entry.__doc__) or spec.description,
        )
    return _extract_feature(name, entry, key.entry_point, partitions)


def extract_alias_spec(entry: object) -> NewTypeSpec | None:
    """Extract the markdown alias spec for a scalar- or container-rooted `RootModel`.

    Such a RootModel is a named alias over its bare root value -- like a
    NewType -- so it documents as a `NewTypeSpec`. Returns None for any
    other entry; a union- or model-rooted RootModel is a feature, which
    `extract_model_spec` extracts.
    """
    if is_rootmodel(entry) and not _is_feature(denoted_type(entry)):
        return extract_rootmodel_alias(entry)
    return None


def _extract_feature(
    name: str, annotation: object, entry_point: str, partitions: Mapping[str, str]
) -> ModelSpec | None:
    """Extract *annotation* as a record or union, or None if it is neither."""
    model = _bare_model(annotation)
    if model is not None:
        return extract_model(model, entry_point=entry_point, partitions=partitions)
    if is_union_alias(annotation):
        return extract_union(
            name, annotation, entry_point=entry_point, partitions=partitions
        )
    return None


def _is_feature(annotation: object) -> bool:
    return _bare_model(annotation) is not None or is_union_alias(annotation)


def _bare_model(annotation: object) -> type[BaseModel] | None:
    """Return the plain model class *annotation* names, if it names one.

    Looks through `Annotated`, which `denoted_type` wraps a RootModel's root
    in. A RootModel is not a plain model: it has no record structure.
    """
    if get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    if is_model_class(annotation) and not is_rootmodel(annotation):
        return annotation
    return None
