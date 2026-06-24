"""Supplementary type discovery by walking feature trees.

Walks `FieldShape` trees to extract referenced enums, NewTypes,
Pydantic built-ins, and union member sub-models. `ModelRef` and
`UnionRef` carry their resolved specs structurally, so recursion
follows the shape directly.
"""

from collections.abc import Sequence
from enum import Enum
from typing import Annotated, get_args, get_origin

from pydantic import BaseModel

from ..extraction.enum_extraction import extract_enum
from ..extraction.field import (
    FieldShape,
    ModelRef,
    NewTypeShape,
    Primitive,
    UnionRef,
)
from ..extraction.field_walk import walk_shape
from ..extraction.newtype_extraction import extract_newtype
from ..extraction.pydantic_extraction import extract_pydantic_type
from ..extraction.specs import (
    FieldSpec,
    ModelSpec,
    RecordSpec,
    SupplementarySpec,
    TypeIdentity,
    is_pydantic_sourced,
)
from ..extraction.type_analyzer import analyze_type, is_newtype
from ..extraction.type_registry import is_semantic_newtype

__all__ = ["collect_all_supplementary_types"]


def collect_all_supplementary_types(
    model_specs: Sequence[ModelSpec],
) -> dict[TypeIdentity, SupplementarySpec]:
    """Collect supplementary types by walking expanded feature trees.

    Walks `ModelRef` references for sub-models (already extracted),
    and extracts enums and NewTypes on first encounter. Two types
    with the same class name from different modules are keyed
    separately.
    """
    feature_objs: set[object] = {spec.identity.obj for spec in model_specs}
    all_specs: dict[TypeIdentity, SupplementarySpec] = {}
    visited_models: set[object] = set()

    def _register_newtype(newtype_ref: object, name: str) -> bool:
        nt_id = TypeIdentity(newtype_ref, name)
        if nt_id in all_specs:
            return False
        all_specs[nt_id] = extract_newtype(newtype_ref)
        return True

    def _collect_from_model(model_spec: RecordSpec) -> None:
        if (
            model_spec.source_type in visited_models
            or model_spec.source_type in feature_objs
        ):
            return
        visited_models.add(model_spec.source_type)
        all_specs[model_spec.identity] = model_spec
        _collect_from_fields(model_spec.fields)

    def _collect_inner_newtypes(newtype_ref: object) -> None:
        """Walk a NewType's `__supertype__` chain for nested semantic NewTypes."""
        annotation = getattr(newtype_ref, "__supertype__", None)
        while annotation is not None:
            if get_origin(annotation) is Annotated:
                annotation = get_args(annotation)[0]
                continue
            if is_newtype(annotation):
                inner_shape, _, _ = analyze_type(annotation)
                if isinstance(inner_shape, NewTypeShape) and is_semantic_newtype(
                    inner_shape
                ):
                    _register_newtype(inner_shape.ref, inner_shape.name)
                annotation = getattr(annotation, "__supertype__", None)
                continue
            break

    def _collect_from_shape(shape: FieldShape) -> None:
        """Walk *shape* and register every supplementary type it touches."""

        def _visit(node: FieldShape) -> None:
            match node:
                case NewTypeShape(name=name, ref=ref) if is_semantic_newtype(node):
                    if _register_newtype(ref, name):
                        _collect_inner_newtypes(ref)
                case UnionRef(union=u):
                    for member in u.member_specs:
                        _collect_from_model(member.spec)
                case ModelRef(model=m, starts_cycle=False):
                    _collect_from_model(m)
                case Primitive(source_type=cls) if cls is not None and isinstance(
                    cls, type
                ):
                    if issubclass(cls, Enum):
                        eid = TypeIdentity.of(cls)
                        if eid not in all_specs:
                            all_specs[eid] = extract_enum(cls)
                    elif is_pydantic_sourced(cls) and not issubclass(cls, BaseModel):
                        pid = TypeIdentity.of(cls)
                        if pid not in all_specs:
                            all_specs[pid] = extract_pydantic_type(cls)

        walk_shape(shape, _visit)

    def _collect_from_fields(fields: list[FieldSpec]) -> None:
        for field_spec in fields:
            _collect_from_shape(field_spec.shape)

    for spec in model_specs:
        _collect_from_fields(spec.fields)

    return all_specs
