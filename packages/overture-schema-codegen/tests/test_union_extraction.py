"""Tests for union extraction."""

import pytest
from codegen_test_support import (
    RailSegment,
    RoadSegment,
    SegmentBase,
    TestSegment,
    WaterSegment,
)
from overture.schema.codegen.extraction.specs import FieldSpec, UnionSpec
from overture.schema.codegen.extraction.union_extraction import extract_union


class TestExtractUnion:
    """Tests for extract_union function."""

    @pytest.fixture
    def segment_spec(self) -> UnionSpec:
        return extract_union("TestSegment", TestSegment)

    def test_extracts_name_and_description(self, segment_spec: UnionSpec) -> None:
        """UnionSpec captures the union name and docstring."""
        assert segment_spec.name == "TestSegment"
        assert segment_spec.description == "Test segment union"

    def test_finds_common_base(self, segment_spec: UnionSpec) -> None:
        """Identifies SegmentBase as the common base class."""
        assert segment_spec.common_base is SegmentBase

    def test_shared_fields_first(self, segment_spec: UnionSpec) -> None:
        """Shared fields from common base come first with variant_sources=None."""
        shared = [
            af for af in segment_spec.annotated_fields if af.variant_sources is None
        ]
        shared_names = [af.field_spec.name for af in shared]
        assert "geometry" in shared_names
        assert "subtype" in shared_names
        # Shared fields are at the start
        first_variant_idx = next(
            (
                i
                for i, af in enumerate(segment_spec.annotated_fields)
                if af.variant_sources is not None
            ),
            len(segment_spec.annotated_fields),
        )
        for af in segment_spec.annotated_fields[:first_variant_idx]:
            assert af.variant_sources is None

    def test_variant_specific_fields_have_sources(
        self, segment_spec: UnionSpec
    ) -> None:
        """Variant-only fields carry their source class names."""
        speed = next(
            af
            for af in segment_spec.annotated_fields
            if af.field_spec.name == "speed_limit"
        )
        assert speed.variant_sources == ("RoadSegment",)
        gauge = next(
            af
            for af in segment_spec.annotated_fields
            if af.field_spec.name == "rail_gauge"
        )
        assert gauge.variant_sources == ("RailSegment",)

    def test_heterogeneous_same_name_produces_separate_rows(
        self, segment_spec: UnionSpec
    ) -> None:
        """class_ in Road (str) vs Rail (int): separate rows, not merged."""
        class_fields = [
            af for af in segment_spec.annotated_fields if af.field_spec.name == "class"
        ]
        assert len(class_fields) == 2
        sources = {af.variant_sources for af in class_fields}
        assert ("RoadSegment",) in sources
        assert ("RailSegment",) in sources

    def test_members_lists_all_member_classes(self, segment_spec: UnionSpec) -> None:
        """UnionSpec.members contains all union member classes."""
        assert set(segment_spec.members) == {RoadSegment, RailSegment, WaterSegment}

    def test_source_annotation_preserved(self, segment_spec: UnionSpec) -> None:
        """source_annotation holds the original Annotated[Union[...]]."""
        assert segment_spec.source_annotation is TestSegment

    def test_fields_property_returns_plain_list(self, segment_spec: UnionSpec) -> None:
        """spec.fields returns list[FieldSpec] without provenance."""
        for f in segment_spec.fields:
            assert isinstance(f, FieldSpec)
