"""Supplementary type discovery by walking expanded feature trees.

Walks FieldSpec.model references for sub-models (already extracted),
and extracts enums and NewTypes on first encounter.
"""

from collections.abc import Sequence
from typing import Annotated, get_args, get_origin

from ..extraction.enum_extraction import extract_enum
from ..extraction.model_extraction import expand_model_tree, extract_model
from ..extraction.newtype_extraction import extract_newtype
from ..extraction.pydantic_extraction import extract_pydantic_type
from ..extraction.specs import (
    FeatureSpec,
    FieldSpec,
    ModelSpec,
    SupplementarySpec,
    TypeIdentity,
    is_pydantic_type,
)
from ..extraction.type_analyzer import (
    TypeInfo,
    TypeKind,
    analyze_type,
    is_newtype,
    walk_type_info,
)
from ..extraction.type_registry import is_semantic_newtype

__all__ = ["collect_all_supplementary_types"]


def collect_all_supplementary_types(
    feature_specs: Sequence[FeatureSpec],
) -> dict[TypeIdentity, SupplementarySpec]:
    """Collect supplementary types by walking expanded feature trees.

    Requires that expand_model_tree has been called on all feature specs
    first. Walks FieldSpec.model references for sub-models (already
    extracted), and extracts enums and NewTypes on first encounter.

    Returns a dict mapping TypeIdentity to extracted specs. Two types
    with the same class name from different modules are keyed separately.
    """
    feature_objs: set[object] = {spec.identity.obj for spec in feature_specs}
    all_specs: dict[TypeIdentity, SupplementarySpec] = {}
    visited_models: set[object] = set()

    def _register_newtype(newtype_ref: object, name: str) -> bool:
        """Register a NewType if not already present. Returns True if registered."""
        nt_id = TypeIdentity(newtype_ref, name)
        if nt_id in all_specs:
            return False
        all_specs[nt_id] = extract_newtype(newtype_ref)
        return True

    def _collect_from_model(model_spec: ModelSpec) -> None:
        if (
            model_spec.source_type in visited_models
            or model_spec.source_type in feature_objs
        ):
            return
        visited_models.add(model_spec.source_type)
        all_specs[model_spec.identity] = model_spec
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
                    inner_ti.newtype_ref is not None
                    and inner_ti.newtype_name is not None
                    and is_semantic_newtype(inner_ti)
                ):
                    _register_newtype(inner_ti.newtype_ref, inner_ti.newtype_name)
                annotation = getattr(annotation, "__supertype__", None)
                continue
            break

    def _collect_from_type_info(ti: TypeInfo) -> None:
        """Collect supplementary types from a single TypeInfo.

        Uses walk_type_info for dict key/value recursion. Handles all
        TypeKind variants without early returns so newtype extraction
        and dict recursion apply regardless of kind.
        """

        def _visit(node: TypeInfo) -> None:
            # UNION, ENUM, and pydantic (PRIMITIVE) are mutually exclusive
            # by TypeKind. NewType extraction is orthogonal -- a node can be
            # a NewType-wrapped ENUM, for instance.
            if node.kind == TypeKind.UNION and node.union_members:
                # Walk each member's fields for supplementary types.
                # Members that are also top-level feature specs are skipped
                # by the feature_objs guard in _collect_from_model.
                for member_cls in node.union_members:
                    member_spec = extract_model(member_cls)
                    expand_model_tree(member_spec)
                    _collect_from_model(member_spec)
            elif node.kind == TypeKind.ENUM and node.source_type is not None:
                enum_id = TypeIdentity.of(node.source_type)
                if enum_id not in all_specs:
                    all_specs[enum_id] = extract_enum(node.source_type)
            elif is_pydantic_type(node):
                if node.source_type is None:
                    raise TypeError(
                        "is_pydantic_type returned True but source_type is None"
                    )
                pid = TypeIdentity.of(node.source_type)
                if pid not in all_specs:
                    all_specs[pid] = extract_pydantic_type(node.source_type)

            # Semantic NewTypes always get extracted, including intermediate
            # NewTypes in the wrapping chain (e.g., Id wraps NoWhitespaceString
            # wraps str -- both Id and NoWhitespaceString get pages).
            if (
                node.newtype_ref is not None
                and node.newtype_name is not None
                and is_semantic_newtype(node)
            ):
                newly_registered = _register_newtype(
                    node.newtype_ref, node.newtype_name
                )
                if newly_registered:
                    _collect_inner_newtypes(node.newtype_ref)

        walk_type_info(ti, _visit)

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
