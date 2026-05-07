"""Compute reverse references from types to their referrers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel

from ..extraction.field import (
    FieldShape,
    ModelRef,
    NewTypeShape,
    Primitive,
    Scalar,
    UnionRef,
)
from ..extraction.field_walk import terminal_of, walk_shape
from ..extraction.specs import (
    FeatureSpec,
    FieldSpec,
    ModelSpec,
    NewTypeSpec,
    SupplementarySpec,
    TypeIdentity,
    UnionSpec,
    is_pydantic_sourced,
)

__all__ = [
    "UsedByEntry",
    "UsedByKind",
    "compute_reverse_references",
]


class UsedByKind(Enum):
    """Kind of referrer in a 'used by' entry."""

    MODEL = 0
    NEWTYPE = 1


@dataclass(frozen=True, slots=True)
class UsedByEntry:
    """A single 'used by' entry pointing to a referrer."""

    identity: TypeIdentity
    kind: UsedByKind


def compute_reverse_references(
    feature_specs: Sequence[FeatureSpec],
    all_specs: Mapping[TypeIdentity, SupplementarySpec],
) -> dict[TypeIdentity, list[UsedByEntry]]:
    """Compute reverse references from types to their referrers.

    Returns a dict mapping TypeIdentity to lists of UsedByEntry, sorted with
    models before NewTypes, alphabetical within each group.

    Parameters
    ----------
    feature_specs
        Feature-level specs (ModelSpec or UnionSpec).
    all_specs
        Supplementary types (enums, newtypes, sub-models).
    """
    references: dict[TypeIdentity, set[UsedByEntry]] = {}

    def add_reference(
        target: TypeIdentity, referrer: TypeIdentity, kind: UsedByKind
    ) -> None:
        if target == referrer or target not in all_specs:
            return
        references.setdefault(target, set()).add(UsedByEntry(referrer, kind))

    def collect_from_shape(
        shape: FieldShape,
        referrer: TypeIdentity,
        referrer_kind: UsedByKind,
    ) -> None:
        """Walk a shape and add references for every type it touches."""

        def _visit(node: FieldShape) -> None:
            match node:
                case NewTypeShape(name=name, ref=ref):
                    add_reference(TypeIdentity(ref, name), referrer, referrer_kind)
                case ModelRef(model=m) if m.source_type is not None:
                    add_reference(
                        TypeIdentity.of(m.source_type), referrer, referrer_kind
                    )
                case UnionRef(union=u):
                    for member_cls in u.members:
                        add_reference(
                            TypeIdentity.of(member_cls), referrer, referrer_kind
                        )
                case Primitive(source_type=cls) if cls is not None:
                    if isinstance(cls, type) and (
                        issubclass(cls, Enum)
                        or issubclass(cls, BaseModel)
                        or is_pydantic_sourced(cls)
                    ):
                        add_reference(TypeIdentity.of(cls), referrer, referrer_kind)

        walk_shape(shape, _visit)

    def collect_from_fields(
        fields: list[FieldSpec],
        referrer: TypeIdentity,
        referrer_kind: UsedByKind,
    ) -> None:
        """Collect references from each field's shape."""
        for field_spec in fields:
            collect_from_shape(field_spec.shape, referrer, referrer_kind)

    def collect_from_model_spec(spec: ModelSpec, referrer: TypeIdentity) -> None:
        collect_from_fields(spec.fields, referrer, UsedByKind.MODEL)

    def collect_from_union_spec(spec: UnionSpec) -> None:
        referrer = spec.identity
        # Union features reference their members
        for member_cls in spec.members:
            add_reference(TypeIdentity.of(member_cls), referrer, UsedByKind.MODEL)
        collect_from_fields(spec.fields, referrer, UsedByKind.MODEL)

    def collect_from_newtype_spec(spec: NewTypeSpec, referrer: TypeIdentity) -> None:
        # The NewType's own identity isn't added here (self-reference).
        # spec.shape already has the outer NewTypeShape stripped.
        collect_from_shape(spec.shape, referrer, UsedByKind.NEWTYPE)

        # Inherited NewTypes from constraint sources (constraint chains).
        terminal = terminal_of(spec.shape)
        if isinstance(terminal, Scalar):
            for cs in terminal.constraints:
                if cs.source_ref is not None and cs.source_name is not None:
                    add_reference(
                        TypeIdentity(cs.source_ref, cs.source_name),
                        referrer,
                        UsedByKind.NEWTYPE,
                    )

    # Collect from features
    for spec in feature_specs:
        if isinstance(spec, ModelSpec):
            collect_from_model_spec(spec, spec.identity)
        elif isinstance(spec, UnionSpec):
            collect_from_union_spec(spec)

    # Collect from supplementary specs (enums have no outgoing references)
    for tid, supp_spec in all_specs.items():
        if isinstance(supp_spec, NewTypeSpec):
            collect_from_newtype_spec(supp_spec, tid)
        elif isinstance(supp_spec, ModelSpec):
            collect_from_model_spec(supp_spec, tid)

    # Sort into deterministic lists.
    result: dict[TypeIdentity, list[UsedByEntry]] = {}
    for target, ref_set in references.items():
        entries = sorted(
            ref_set,
            key=lambda e: (e.kind.value, e.identity.name, e.identity.module),
        )
        result[target] = entries

    return result
