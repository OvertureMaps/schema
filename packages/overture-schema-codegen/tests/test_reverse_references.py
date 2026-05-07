"""Tests for reverse reference computation."""

from enum import Enum as PyEnum
from typing import NewType

import pytest
from codegen_test_support import (
    FeatureWithAddress,
    FeatureWithUrl,
    Instrument,
    RoadSegment,
    TreeNode,
    Venue,
    feature_spec_for_model,
    has_name,
    lookup_by_name,
    make_union_spec,
)
from overture.schema.codegen.extraction.enum_extraction import extract_enum
from overture.schema.codegen.extraction.newtype_extraction import extract_newtype
from overture.schema.codegen.extraction.specs import (
    ModelSpec,
    PydanticTypeSpec,
    TypeIdentity,
)
from overture.schema.codegen.layout.type_collection import (
    collect_all_supplementary_types,
)
from overture.schema.codegen.markdown.reverse_references import (
    UsedByKind,
    compute_reverse_references,
)
from overture.schema.system.ref import Id
from overture.schema.system.string import NoWhitespaceString
from pydantic import BaseModel


@pytest.mark.parametrize(
    ("model_class", "model_name", "target_name"),
    [
        (Instrument, "Instrument", "InstrumentFamily"),
        (Instrument, "Instrument", "HexColor"),
        (FeatureWithAddress, "FeatureWithAddress", "Address"),
    ],
    ids=["enum", "newtype", "sub-model"],
)
def test_model_referencing_type_produces_used_by_entry(
    model_class: type,
    model_name: str,
    target_name: str,
) -> None:
    """Model referencing a type produces a 'used by' entry on that type."""
    expanded = feature_spec_for_model(model_class, entry_point=model_name)
    all_specs = collect_all_supplementary_types([expanded])

    assert has_name(all_specs, target_name)

    result = compute_reverse_references([expanded], all_specs)

    entries = lookup_by_name(result, target_name)
    assert len(entries) == 1
    assert entries[0].identity.name == model_name
    assert entries[0].kind == UsedByKind.MODEL


def test_newtype_inheriting_from_newtype_produces_used_by_entry() -> None:
    """NewType inheriting constraints from another NewType produces a 'used by' entry."""
    # Id wraps NoWhitespaceString, which is also a NewType
    # When we extract Id, its constraints include ConstraintSource(source_ref=NoWhitespaceString, ...)
    id_spec = extract_newtype(Id)
    nws_spec = extract_newtype(NoWhitespaceString)

    all_specs = {
        TypeIdentity(Id, "Id"): id_spec,
        TypeIdentity(NoWhitespaceString, "NoWhitespaceString"): nws_spec,
    }

    result = compute_reverse_references([], all_specs)

    # NoWhitespaceString should have a used_by entry from Id
    entries = lookup_by_name(result, "NoWhitespaceString")
    assert len(entries) == 1
    assert entries[0].identity.name == "Id"
    assert entries[0].kind == UsedByKind.NEWTYPE


def test_union_members_have_used_by_entries() -> None:
    """Union members have 'used by' entries pointing to the union feature."""
    # Create a union spec with RoadSegment as a member
    union_spec = make_union_spec(
        name="TestSegment",
        description="Test segment union",
        members=[RoadSegment],
        entry_point="TestSegment",
    )

    # Extract the member
    road_spec = feature_spec_for_model(RoadSegment)
    assert isinstance(road_spec, ModelSpec)
    all_specs = {TypeIdentity(RoadSegment, "RoadSegment"): road_spec}

    result = compute_reverse_references([union_spec], all_specs)

    entries = lookup_by_name(result, "RoadSegment")
    assert len(entries) == 1
    assert entries[0].identity.name == "TestSegment"
    assert entries[0].kind == UsedByKind.MODEL


def test_self_references_filtered_out() -> None:
    """Self-references are filtered out (handles recursive types)."""
    tree_spec = feature_spec_for_model(TreeNode, entry_point="TreeNode")
    assert isinstance(tree_spec, ModelSpec)

    # Manually add TreeNode to all_specs to test self-reference filtering
    all_specs = {TypeIdentity(TreeNode, "TreeNode"): tree_spec}

    result = compute_reverse_references([tree_spec], all_specs)

    # TreeNode should not appear in result since it only references itself
    with pytest.raises(KeyError):
        lookup_by_name(result, "TreeNode")


def test_deduplication_same_type_multiple_fields() -> None:
    """Deduplication works when same type is referenced via multiple fields."""
    instrument_spec = feature_spec_for_model(Instrument, entry_point="Instrument")
    venue_spec = feature_spec_for_model(Venue, entry_point="Venue")
    all_specs = collect_all_supplementary_types([instrument_spec, venue_spec])

    assert has_name(all_specs, "Id")

    result = compute_reverse_references([instrument_spec, venue_spec], all_specs)

    entries = lookup_by_name(result, "Id")
    # Both Instrument and Venue reference Id
    assert len(entries) == 2
    names = {e.identity.name for e in entries}
    assert names == {"Instrument", "Venue"}
    # All should be MODELs
    assert all(e.kind == UsedByKind.MODEL for e in entries)


def test_pydantic_type_has_used_by_from_feature() -> None:
    """Pydantic type in all_specs gets used-by entries from features referencing it."""
    expanded = feature_spec_for_model(FeatureWithUrl, entry_point="FeatureWithUrl")
    all_specs = collect_all_supplementary_types([expanded])

    assert has_name(all_specs, "HttpUrl")
    assert isinstance(lookup_by_name(all_specs, "HttpUrl"), PydanticTypeSpec)

    result = compute_reverse_references([expanded], all_specs)

    entries = lookup_by_name(result, "HttpUrl")
    assert any(e.identity.name == "FeatureWithUrl" for e in entries)


def test_sort_tiebreaker_uses_module_for_same_name_referrers() -> None:
    """Referrers with the same name sort deterministically by module."""

    # Two model classes named "Feature" from different modules.
    class SharedEnum(PyEnum):
        A = "a"

    class FeatureAlpha(BaseModel):
        value: SharedEnum

    class FeatureBeta(BaseModel):
        value: SharedEnum

    FeatureAlpha.__name__ = "Feature"
    FeatureAlpha.__module__ = "alpha.models"
    FeatureBeta.__name__ = "Feature"
    FeatureBeta.__module__ = "beta.models"

    spec_a = feature_spec_for_model(FeatureAlpha, entry_point="Feature")
    spec_b = feature_spec_for_model(FeatureBeta, entry_point="Feature")

    enum_id = TypeIdentity(SharedEnum, "SharedEnum")
    all_specs = {enum_id: extract_enum(SharedEnum)}

    result = compute_reverse_references([spec_a, spec_b], all_specs)

    entries = lookup_by_name(result, "SharedEnum")
    assert len(entries) == 2
    # Both named "Feature" — module provides the tiebreaker
    modules = [e.identity.module for e in entries]
    assert modules == ["alpha.models", "beta.models"]


def test_sorting_models_before_newtypes() -> None:
    """Sorting produces models before NewTypes, alphabetical within groups."""
    # Create a test where the same type (Id) is referenced by:
    # - Two models (Instrument and Venue) - both MODEL referrers
    # - A NewType wrapper around Id
    # Create a synthetic NewType that wraps Id
    CustomId = NewType("CustomId", Id)

    instrument_spec = feature_spec_for_model(Instrument, entry_point="Instrument")
    venue_spec = feature_spec_for_model(Venue, entry_point="Venue")
    all_specs = collect_all_supplementary_types([instrument_spec, venue_spec])

    # Add the CustomId NewType which references Id
    custom_id_spec = extract_newtype(CustomId)
    all_specs[TypeIdentity(CustomId, "CustomId")] = custom_id_spec

    result = compute_reverse_references([instrument_spec, venue_spec], all_specs)

    # Id should have entries from both Instrument and Venue (MODELs) and CustomId (NEWTYPE)
    entries = lookup_by_name(result, "Id")
    assert len(entries) == 3

    # Check sorting: MODELs first, then NEWTYPE
    # Within MODELs: alphabetical (Instrument, Venue)
    assert entries[0].kind == UsedByKind.MODEL
    assert entries[0].identity.name == "Instrument"
    assert entries[1].kind == UsedByKind.MODEL
    assert entries[1].identity.name == "Venue"
    assert entries[2].kind == UsedByKind.NEWTYPE
    assert entries[2].identity.name == "CustomId"
