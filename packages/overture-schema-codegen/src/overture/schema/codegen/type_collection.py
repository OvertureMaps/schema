"""Supplementary type discovery by walking expanded feature trees.

Walks FieldSpec.model references for sub-models (already extracted),
and extracts enums and NewTypes on first encounter.
"""

from collections.abc import Sequence
from typing import Annotated, get_args, get_origin

from .enum_extraction import extract_enum
from .model_extraction import extract_model
from .newtype_extraction import extract_newtype
from .specs import FeatureSpec, FieldSpec, ModelSpec, SupplementarySpec
from .type_analyzer import TypeInfo, TypeKind, analyze_type, is_newtype
from .type_registry import is_semantic_newtype

__all__ = ["collect_all_supplementary_types"]


def collect_all_supplementary_types(
    feature_specs: Sequence[FeatureSpec],
) -> dict[str, SupplementarySpec]:
    """Collect supplementary types by walking expanded feature trees.

    Requires that expand_model_tree has been called on all feature specs
    first. Walks FieldSpec.model references for sub-models (already
    extracted), and extracts enums and NewTypes on first encounter.

    Returns a dict mapping type names to extracted specs.
    """
    feature_names = {spec.name for spec in feature_specs}
    all_specs: dict[str, SupplementarySpec] = {}
    visited_models: set[str] = set()

    def _collect_from_model(model_spec: ModelSpec) -> None:
        if model_spec.name in visited_models or model_spec.name in feature_names:
            return
        visited_models.add(model_spec.name)
        all_specs[model_spec.name] = model_spec
        _collect_from_fields(model_spec.fields)

    def _collect_inner_newtypes(newtype_ref: object) -> None:
        """Walk a NewType's __supertype__ chain for intermediate semantic NewTypes."""
        annotation = getattr(newtype_ref, "__supertype__", None)
        while annotation is not None:
            if get_origin(annotation) is Annotated:
                annotation = get_args(annotation)[0]
                continue
            if is_newtype(annotation):
                inner_ti = analyze_type(annotation)
                if (
                    inner_ti.newtype_name is not None
                    and is_semantic_newtype(inner_ti)
                    and inner_ti.newtype_name not in all_specs
                ):
                    all_specs[inner_ti.newtype_name] = extract_newtype(annotation)
                annotation = getattr(annotation, "__supertype__", None)
                continue
            break

    def _collect_from_type_info(ti: TypeInfo) -> None:
        """Collect supplementary types from a single TypeInfo."""
        if ti.kind == TypeKind.UNION:
            if not ti.union_members:
                return
            # Walk each member's fields for supplementary types.
            # Members that are also top-level feature specs are skipped
            # by the feature_names guard in _collect_from_model.
            for member_cls in ti.union_members:
                member_spec = extract_model(member_cls)
                _collect_from_model(member_spec)
            return
        if ti.kind == TypeKind.ENUM and ti.source_type is not None:
            name = ti.source_type.__name__
            if name not in all_specs:
                all_specs[name] = extract_enum(ti.source_type)

        # Semantic NewTypes always get extracted, including intermediate
        # NewTypes in the wrapping chain (e.g., Id wraps NoWhitespaceString
        # wraps str — both Id and NoWhitespaceString get pages).
        if (
            ti.newtype_ref is not None
            and ti.newtype_name is not None
            and is_semantic_newtype(ti)
            and ti.newtype_name not in all_specs
        ):
            all_specs[ti.newtype_name] = extract_newtype(ti.newtype_ref)
            _collect_inner_newtypes(ti.newtype_ref)

        # Dict key/value types can also reference supplementary types
        if ti.dict_key_type is not None:
            _collect_from_type_info(ti.dict_key_type)
        if ti.dict_value_type is not None:
            _collect_from_type_info(ti.dict_value_type)

    def _collect_from_fields(fields: list[FieldSpec]) -> None:
        # A single field can match multiple conditions (e.g., Sources is both
        # a semantic NewType and wraps a MODEL-kind type), so checks are
        # independent `if` statements, not `elif`.
        for field_spec in fields:
            ti = field_spec.type_info
            _collect_from_type_info(ti)

            # MODEL-kind fields (whether direct or via NewType wrapper) get expanded
            if ti.kind == TypeKind.MODEL and ti.source_type is not None:
                if field_spec.model is None:
                    msg = (
                        f"MODEL-kind field {field_spec.name!r} has source_type "
                        f"but model=None — call expand_model_tree first"
                    )
                    raise RuntimeError(msg)
                if not field_spec.starts_cycle:
                    _collect_from_model(field_spec.model)

    for spec in feature_specs:
        _collect_from_fields(spec.fields)

    return all_specs
