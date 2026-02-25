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

    name: str
    kind: UsedByKind


def compute_reverse_references(
    feature_specs: Sequence[FeatureSpec],
    all_specs: Mapping[str, SupplementarySpec],
) -> dict[str, list[UsedByEntry]]:
    """Compute reverse references from types to their referrers.

    Returns a dict mapping type names to lists of UsedByEntry, sorted with
    models before NewTypes, alphabetical within each group.

    Parameters
    ----------
    feature_specs : Sequence[FeatureSpec]
        Feature-level specs (ModelSpec or UnionSpec).
    all_specs : Mapping[str, SupplementarySpec]
        Supplementary types (enums, newtypes, sub-models).

    Returns
    -------
    dict[str, list[UsedByEntry]]
        Dict mapping type names to sorted lists of UsedByEntry.
    """
    # Track references with sets to deduplicate
    references: dict[str, set[UsedByEntry]] = {}

    def add_reference(target: str, referrer_name: str, kind: UsedByKind) -> None:
        """Add a reference from referrer to target, with deduplication."""
        if target == referrer_name or target not in all_specs:
            return
        references.setdefault(target, set()).add(UsedByEntry(referrer_name, kind))

    def collect_from_type_info(
        ti: TypeInfo, referrer_name: str, referrer_kind: UsedByKind
    ) -> None:
        """Collect references from a TypeInfo."""

        def _visit(node: TypeInfo) -> None:
            if node.newtype_name is not None:
                add_reference(node.newtype_name, referrer_name, referrer_kind)

            if (
                node.kind in (TypeKind.ENUM, TypeKind.MODEL)
                and node.source_type is not None
            ):
                add_reference(node.source_type.__name__, referrer_name, referrer_kind)

            if node.union_members is not None:
                for member_cls in node.union_members:
                    add_reference(member_cls.__name__, referrer_name, referrer_kind)

        walk_type_info(ti, _visit)

    def collect_from_fields(
        fields: list[FieldSpec], referrer_name: str, referrer_kind: UsedByKind
    ) -> None:
        """Collect references from model fields."""
        for field_spec in fields:
            collect_from_type_info(field_spec.type_info, referrer_name, referrer_kind)

    def collect_from_model_spec(spec: ModelSpec) -> None:
        """Collect references from a ModelSpec."""
        collect_from_fields(spec.fields, spec.name, UsedByKind.MODEL)

    def collect_from_union_spec(spec: UnionSpec) -> None:
        """Collect references from a UnionSpec."""
        # Union features reference their members
        for member_cls in spec.members:
            add_reference(member_cls.__name__, spec.name, UsedByKind.MODEL)
        # Also walk fields for other supplementary types
        collect_from_fields(spec.fields, spec.name, UsedByKind.MODEL)

    def collect_from_newtype_spec(spec: NewTypeSpec, referrer_name: str) -> None:
        """Collect references from a NewTypeSpec."""
        collect_from_type_info(spec.type_info, referrer_name, UsedByKind.NEWTYPE)

        # Collect inherited NewTypes from constraint sources
        for cs in spec.type_info.constraints:
            if cs.source is not None:
                add_reference(cs.source, referrer_name, UsedByKind.NEWTYPE)

    # Collect from features
    for spec in feature_specs:
        if isinstance(spec, ModelSpec):
            collect_from_model_spec(spec)
        elif isinstance(spec, UnionSpec):
            collect_from_union_spec(spec)

    # Collect from supplementary specs (NewTypes and sub-models reference
    # other types; enums do not, so they need no processing here)
    for name, supp_spec in all_specs.items():
        if isinstance(supp_spec, NewTypeSpec):
            collect_from_newtype_spec(supp_spec, name)
        elif isinstance(supp_spec, ModelSpec):
            collect_from_model_spec(supp_spec)

    # Sort sets into lists
    result: dict[str, list[UsedByEntry]] = {}
    for target, ref_set in references.items():
        entries = sorted(ref_set, key=lambda e: (e.kind.value, e.name))
        result[target] = entries

    return result
