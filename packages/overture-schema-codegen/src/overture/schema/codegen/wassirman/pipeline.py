"""Validation IR generation pipeline."""

from __future__ import annotations

from collections.abc import Sequence

from ..extraction.model_extraction import expand_model_tree
from ..extraction.specs import FeatureSpec, ModelSpec
from ..extraction.type_analyzer import TypeKind
from .ir import DatasetIR, ValidationIR
from .walker import walk_feature

__all__ = ["generate_validation_ir"]


def _dataset_name(spec: FeatureSpec) -> str:
    """Derive dataset name from the model's type Literal field."""
    for field_spec in spec.fields:
        if field_spec.name == "type" and field_spec.type_info.kind == TypeKind.LITERAL:
            vals = field_spec.type_info.literal_values
            if vals and len(vals) == 1:
                return str(vals[0])
    return spec.name.lower()


def _source_model_fqn(spec: FeatureSpec) -> str:
    """Fully qualified name of the source model."""
    src = spec.source_type
    if src is None:
        return spec.name
    return f"{src.__module__}.{src.__qualname__}"


def generate_validation_ir(
    feature_specs: Sequence[FeatureSpec],
) -> ValidationIR:
    """Generate validation IR from feature specs.

    Parameters
    ----------
    feature_specs
        Extracted feature specs to convert to validation IR.

    Returns
    -------
    ValidationIR
        Full validation IR with one dataset per feature spec.
    """
    cache: dict[type, ModelSpec] = {}
    for spec in feature_specs:
        expand_model_tree(spec, cache)

    datasets: list[DatasetIR] = []
    for spec in feature_specs:
        name = _dataset_name(spec)
        rules = walk_feature(spec, name)
        datasets.append(
            DatasetIR(
                name=name,
                source_model=_source_model_fqn(spec),
                id_column="id",
                rules=rules,
            )
        )

    return ValidationIR(datasets=datasets)
