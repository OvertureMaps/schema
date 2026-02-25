"""Tests for reverse reference computation."""

from typing import NewType

import pytest
from codegen_test_support import (
    FeatureWithAddress,
    Instrument,
    RoadSegment,
    TreeNode,
    Venue,
    make_union_spec,
)
from overture.schema.codegen.model_extraction import expand_model_tree, extract_model
from overture.schema.codegen.newtype_extraction import extract_newtype
from overture.schema.codegen.reverse_references import (
    UsedByKind,
    compute_reverse_references,
)
from overture.schema.codegen.type_collection import collect_all_supplementary_types
from overture.schema.system.ref import Id
from overture.schema.system.string import NoWhitespaceString


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
    model_spec = extract_model(model_class, entry_point=model_name)
    expand_model_tree(model_spec)
    all_specs = collect_all_supplementary_types([model_spec])

    assert target_name in all_specs

    result = compute_reverse_references([model_spec], all_specs)

    assert target_name in result
    entries = result[target_name]
    assert len(entries) == 1
    assert entries[0].name == model_name
    assert entries[0].kind == UsedByKind.MODEL


def test_newtype_inheriting_from_newtype_produces_used_by_entry() -> None:
    """NewType inheriting constraints from another NewType produces a 'used by' entry."""
    # Id wraps NoWhitespaceString, which is also a NewType
    # When we extract Id, its constraints include ConstraintSource(source="NoWhitespaceString", ...)
    id_spec = extract_newtype(Id)
    nws_spec = extract_newtype(NoWhitespaceString)

    all_specs = {"Id": id_spec, "NoWhitespaceString": nws_spec}

    result = compute_reverse_references([], all_specs)

    # NoWhitespaceString should have a used_by entry from Id
    assert "NoWhitespaceString" in result
    entries = result["NoWhitespaceString"]
    assert len(entries) == 1
    assert entries[0].name == "Id"
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
    road_spec = extract_model(RoadSegment)
    expand_model_tree(road_spec)
    all_specs = {"RoadSegment": road_spec}

    result = compute_reverse_references([union_spec], all_specs)

    assert "RoadSegment" in result
    entries = result["RoadSegment"]
    assert len(entries) == 1
    assert entries[0].name == "TestSegment"
    assert entries[0].kind == UsedByKind.MODEL


def test_self_references_filtered_out() -> None:
    """Self-references are filtered out (handles recursive types)."""
    tree_spec = extract_model(TreeNode, entry_point="TreeNode")
    expand_model_tree(tree_spec)

    # Manually add TreeNode to all_specs to test self-reference filtering
    all_specs = {"TreeNode": tree_spec}

    result = compute_reverse_references([tree_spec], all_specs)

    # TreeNode should not appear in result since it only references itself
    assert "TreeNode" not in result


def test_deduplication_same_type_multiple_fields() -> None:
    """Deduplication works when same type is referenced via multiple fields."""
    instrument_spec = extract_model(Instrument, entry_point="Instrument")
    venue_spec = extract_model(Venue, entry_point="Venue")
    expand_model_tree(instrument_spec)
    expand_model_tree(venue_spec)
    all_specs = collect_all_supplementary_types([instrument_spec, venue_spec])

    assert "Id" in all_specs

    result = compute_reverse_references([instrument_spec, venue_spec], all_specs)

    assert "Id" in result
    entries = result["Id"]
    # Both Instrument and Venue reference Id
    assert len(entries) == 2
    names = {e.name for e in entries}
    assert names == {"Instrument", "Venue"}
    # All should be MODELs
    assert all(e.kind == UsedByKind.MODEL for e in entries)


def test_sorting_models_before_newtypes() -> None:
    """Sorting produces models before NewTypes, alphabetical within groups."""
    # Create a test where the same type (Id) is referenced by:
    # - Two models (Instrument and Venue) - both MODEL referrers
    # - A NewType wrapper around Id
    # Create a synthetic NewType that wraps Id
    CustomId = NewType("CustomId", Id)

    instrument_spec = extract_model(Instrument, entry_point="Instrument")
    venue_spec = extract_model(Venue, entry_point="Venue")
    expand_model_tree(instrument_spec)
    expand_model_tree(venue_spec)
    all_specs = collect_all_supplementary_types([instrument_spec, venue_spec])

    # Add the CustomId NewType which references Id
    custom_id_spec = extract_newtype(CustomId)
    all_specs["CustomId"] = custom_id_spec

    result = compute_reverse_references([instrument_spec, venue_spec], all_specs)

    # Id should have entries from both Instrument and Venue (MODELs) and CustomId (NEWTYPE)
    entries = result["Id"]
    assert len(entries) == 3

    # Check sorting: MODELs first, then NEWTYPE
    # Within MODELs: alphabetical (Instrument, Venue)
    assert entries[0].kind == UsedByKind.MODEL
    assert entries[0].name == "Instrument"
    assert entries[1].kind == UsedByKind.MODEL
    assert entries[1].name == "Venue"
    assert entries[2].kind == UsedByKind.NEWTYPE
    assert entries[2].name == "CustomId"
