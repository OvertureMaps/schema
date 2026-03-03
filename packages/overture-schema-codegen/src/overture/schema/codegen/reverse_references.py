"""Compute reverse references from types to their referrers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from .specs import (
    FeatureSpec,
    FieldSpec,
    ModelSpec,
    NewTypeSpec,
    SupplementarySpec,
    TypeIdentity,
    UnionSpec,
)
from .type_analyzer import TypeInfo, TypeKind, walk_type_info

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
    feature_specs : Sequence[FeatureSpec]
        Feature-level specs (ModelSpec or UnionSpec).
    all_specs : Mapping[TypeIdentity, SupplementarySpec]
        Supplementary types (enums, newtypes, sub-models).

    Returns
    -------
    dict[TypeIdentity, list[UsedByEntry]]
        Dict mapping TypeIdentity to sorted lists of UsedByEntry.
    """
    # Track references with sets to deduplicate
    references: dict[TypeIdentity, set[UsedByEntry]] = {}

    def add_reference(
        target: TypeIdentity, referrer: TypeIdentity, kind: UsedByKind
    ) -> None:
        """Add a reference from referrer to target, with deduplication."""
        if target == referrer or target not in all_specs:
            return
        references.setdefault(target, set()).add(UsedByEntry(referrer, kind))

    def collect_from_type_info(
        ti: TypeInfo, referrer: TypeIdentity, referrer_kind: UsedByKind
    ) -> None:
        """Collect references from a TypeInfo."""

        def _visit(node: TypeInfo) -> None:
            if node.newtype_ref is not None and node.newtype_name is not None:
                add_reference(
                    TypeIdentity(node.newtype_ref, node.newtype_name),
                    referrer,
                    referrer_kind,
                )

            if (
                node.kind in (TypeKind.ENUM, TypeKind.MODEL)
                and node.source_type is not None
            ):
                add_reference(
                    TypeIdentity.of(node.source_type),
                    referrer,
                    referrer_kind,
                )

            if node.union_members is not None:
                for member_cls in node.union_members:
                    add_reference(
                        TypeIdentity.of(member_cls),
                        referrer,
                        referrer_kind,
                    )

        walk_type_info(ti, _visit)

    def collect_from_fields(
        fields: list[FieldSpec], referrer: TypeIdentity, referrer_kind: UsedByKind
    ) -> None:
        """Collect references from model fields."""
        for field_spec in fields:
            collect_from_type_info(field_spec.type_info, referrer, referrer_kind)

    def collect_from_model_spec(spec: ModelSpec, referrer: TypeIdentity) -> None:
        """Collect references from a ModelSpec."""
        collect_from_fields(spec.fields, referrer, UsedByKind.MODEL)

    def collect_from_union_spec(spec: UnionSpec) -> None:
        """Collect references from a UnionSpec."""
        referrer = spec.identity
        # Union features reference their members
        for member_cls in spec.members:
            add_reference(
                TypeIdentity.of(member_cls),
                referrer,
                UsedByKind.MODEL,
            )
        # Also walk fields for other supplementary types
        collect_from_fields(spec.fields, referrer, UsedByKind.MODEL)

    def collect_from_newtype_spec(spec: NewTypeSpec, referrer: TypeIdentity) -> None:
        """Collect references from a NewTypeSpec."""
        collect_from_type_info(spec.type_info, referrer, UsedByKind.NEWTYPE)

        # Collect inherited NewTypes from constraint sources
        for cs in spec.type_info.constraints:
            if cs.source_ref is not None and cs.source_name is not None:
                ref_id = TypeIdentity(cs.source_ref, cs.source_name)
                add_reference(ref_id, referrer, UsedByKind.NEWTYPE)

    # Collect from features
    for spec in feature_specs:
        if isinstance(spec, ModelSpec):
            collect_from_model_spec(spec, spec.identity)
        elif isinstance(spec, UnionSpec):
            collect_from_union_spec(spec)

    # Collect from supplementary specs (NewTypes and sub-models reference
    # other types; enums do not, so they need no processing here)
    for tid, supp_spec in all_specs.items():
        if isinstance(supp_spec, NewTypeSpec):
            collect_from_newtype_spec(supp_spec, tid)
        elif isinstance(supp_spec, ModelSpec):
            collect_from_model_spec(supp_spec, tid)

    # Sort sets into lists
    result: dict[TypeIdentity, list[UsedByEntry]] = {}
    for target, ref_set in references.items():
        entries = sorted(ref_set, key=lambda e: (e.kind.value, e.identity.name))
        result[target] = entries

    return result
