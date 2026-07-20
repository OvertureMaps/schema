"""Integration tests against real Overture models.

These tests validate the extraction layer against actual models from
the installed Overture schema packages.
"""

import pytest
from codegen_test_support import assert_literal_field, spec_for_model
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.extraction.specs import (
    ModelSpec,
    RecordSpec,
    UnionSpec,
    filter_model_classes,
)
from overture.schema.codegen.extraction.union_extraction import extract_union
from overture.schema.codegen.markdown.pipeline import generate_markdown_pages
from overture.schema.codegen.markdown.renderer import render_model
from overture.schema.codegen.spec_discovery import extract_model_spec
from overture.schema.system.discovery import discover_models
from overture.schema.transportation import Segment
from overture.schema.transportation.segment.models import RoadSegment
from pydantic import BaseModel


class TestDiscoverModels:
    """Tests for model discovery."""

    def test_discover_models_returns_multiple_themes(self) -> None:
        """Should discover models from multiple themes."""
        models = discover_models()
        assert len(models) >= 3, f"Expected at least 3 models, got {len(models)}"


class TestExtractBuildingModel:
    """Tests for extracting the Building model."""

    def test_extract_building_has_name(self, building_spec: RecordSpec) -> None:
        """Building model spec should have correct name."""
        assert building_spec.name == "Building"

    def test_extract_building_has_theme_type(self, building_spec: RecordSpec) -> None:
        """Building should have theme='buildings', type='building' as Literal fields."""
        assert_literal_field(building_spec, "theme", "buildings")
        assert_literal_field(building_spec, "type", "building")

    def test_extract_building_has_fields(self, building_spec: RecordSpec) -> None:
        """Building should have multiple fields."""
        assert len(building_spec.fields) > 0, "Building should have at least one field"
        field_names = {f.name for f in building_spec.fields}
        assert "id" in field_names

    def test_building_field_shapes_are_present(self, building_spec: RecordSpec) -> None:
        """Every Building field has a `FieldShape`."""
        for field in building_spec.fields:
            assert field.shape is not None


class TestExtractPlaceModel:
    """Tests for extracting the Place model."""

    def test_extract_place_has_theme_type(self, place_class: type[BaseModel]) -> None:
        """Place should have theme='places', type='place' as Literal fields."""
        spec = extract_model(place_class)
        assert_literal_field(spec, "theme", "places")
        assert_literal_field(spec, "type", "place")

    def test_place_has_fields(self, place_class: type[BaseModel]) -> None:
        """Place model should have fields."""
        spec = extract_model(place_class)
        assert len(spec.fields) > 0


class TestExtractDivisionModel:
    """Tests for extracting Division model."""

    def test_extract_division_theme_type(self, division_class: type[BaseModel]) -> None:
        """Division should have theme='divisions', type='division' as Literal fields."""
        spec = extract_model(division_class)
        assert_literal_field(spec, "theme", "divisions")
        assert_literal_field(spec, "type", "division")


class TestFieldTypeAnalysis:
    """Tests that analyze_type handles real model field types correctly."""

    def test_no_analyze_type_crashes(self, all_discovered_models: dict) -> None:
        """extract_model should not crash on any discovered model."""
        for model_class in filter_model_classes(all_discovered_models):
            spec = extract_model(model_class)
            assert spec.name == model_class.__name__

    def test_all_field_shapes_resolved(self, all_discovered_models: dict) -> None:
        """Every field of every discovered model carries a `FieldShape`."""
        for model_class in filter_model_classes(all_discovered_models):
            spec = extract_model(model_class)
            for field in spec.fields:
                assert field.shape is not None, f"No shape for {spec.name}.{field.name}"


class TestMarkdownRenderingRealModels:
    """Tests for markdown rendering with real models."""

    def test_render_building_content(self, building_class: type[BaseModel]) -> None:
        """Building renders with title, field table, and expected fields."""
        markdown = render_model(spec_for_model(building_class))

        assert "# Building" in markdown
        assert "| Name |" in markdown
        assert "| Type |" in markdown
        assert "id" in markdown
        assert "geometry" in markdown

    def test_render_all_models_without_crash(self, all_discovered_models: dict) -> None:
        """render_model should not crash on any discovered model."""
        for model_class in filter_model_classes(all_discovered_models):
            render_model(spec_for_model(model_class))


class TestDiscriminatedUnions:
    """Tests for discriminated union types like Segment.

    Segment is registered as a discriminated union (type alias), not a class.
    The extraction layer handles the individual union members (RoadSegment,
    RailSegment, WaterSegment) but not the union itself.
    """

    def test_segment_is_not_a_class(self) -> None:
        """Segment discovery returns a type alias, not a class."""
        models = discover_models()
        segment_entries = [
            (k, v) for k, v in models.items() if "segment" in str(k).lower()
        ]

        assert len(segment_entries) == 1
        _key, segment = segment_entries[0]

        assert not isinstance(segment, type)

    def test_individual_segment_types_extractable(self) -> None:
        """Individual segment member types have expected theme/type literals."""
        spec = extract_union("Segment", Segment)
        for member_cls in spec.members:
            member_spec = extract_model(member_cls)
            assert_literal_field(member_spec, "theme", "transportation")
            assert_literal_field(member_spec, "type", "segment")

    def test_road_segment_has_road_specific_fields(self) -> None:
        """RoadSegment should have road-specific fields."""
        spec = extract_model(RoadSegment)
        field_names = {f.name for f in spec.fields}

        assert "subtype" in field_names


class TestSegmentUnionExtraction:
    """Tests for extracting the real Segment discriminated union."""

    @pytest.fixture
    def segment_spec(self) -> UnionSpec:
        """Extract Segment union spec."""
        return extract_union("Segment", Segment)

    def test_segment_extract_union_succeeds(self, segment_spec: UnionSpec) -> None:
        """extract_union works on the real Segment type alias."""
        assert segment_spec.name == "Segment"
        assert len(segment_spec.members) == 3

    def test_segment_has_shared_fields(self, segment_spec: UnionSpec) -> None:
        """Segment UnionSpec has shared fields from TransportationSegment."""
        shared = [
            af for af in segment_spec.annotated_fields if af.variant_sources is None
        ]
        shared_names = {af.field_spec.name for af in shared}
        # All segments share these base fields
        assert "geometry" in shared_names
        assert "subtype" in shared_names
        assert "id" in shared_names

    def test_segment_has_variant_fields(self, segment_spec: UnionSpec) -> None:
        """Segment UnionSpec has variant-specific fields."""
        variant = [
            af for af in segment_spec.annotated_fields if af.variant_sources is not None
        ]
        variant_names = {af.field_spec.name for af in variant}
        # RoadSegment has these specific fields
        assert "road_flags" in variant_names
        assert "road_surface" in variant_names
        assert len(variant_names) > 0

    def test_segment_discriminator_extracted_from_callable(
        self, segment_spec: UnionSpec
    ) -> None:
        """Segment callable discriminator is resolved via _field_name."""
        assert segment_spec.discriminator_field == "subtype"
        assert segment_spec.discriminator_mapping is not None
        assert len(segment_spec.discriminator_mapping) == 3
        # Keys are runtime string values, e.g. "road"
        assert segment_spec.discriminator_mapping["road"] is RoadSegment

    def test_segment_common_base_is_base_model(self, segment_spec: UnionSpec) -> None:
        """Segment common_base is the shared base class."""
        assert segment_spec.common_base is not None
        assert issubclass(segment_spec.common_base, BaseModel)
        # Verify common base has expected fields
        assert "geometry" in segment_spec.common_base.model_fields
        assert "id" in segment_spec.common_base.model_fields


class TestPydanticTypePages:
    """End-to-end: pipeline produces pages for referenced Pydantic built-in types."""

    _SCHEMA_ROOT = "overture.schema"

    @pytest.fixture(scope="class")
    @classmethod
    def pages(cls) -> list:
        """Generate all pages from real discovered models."""
        models = discover_models()
        model_specs: list[ModelSpec] = [
            spec
            for key, entry in models.items()
            if (spec := extract_model_spec(key, entry)) is not None
        ]
        return generate_markdown_pages(model_specs, cls._SCHEMA_ROOT)

    def test_http_url_page_exists(self, pages: list) -> None:
        """Pipeline produces a page for HttpUrl under pydantic/networks/."""
        paths = {str(p.path) for p in pages}
        assert any("pydantic/networks/http_url" in path for path in paths)

    def test_email_str_page_exists(self, pages: list) -> None:
        """Pipeline produces a page for EmailStr under pydantic/networks/."""
        paths = {str(p.path) for p in pages}
        assert any("pydantic/networks/email_str" in path for path in paths)

    def test_http_url_page_content(self, pages: list) -> None:
        """HttpUrl page has expected heading and Pydantic docs link."""
        page = next(p for p in pages if "pydantic/networks/http_url" in str(p.path))
        assert "# HttpUrl" in page.content
        assert "docs.pydantic.dev" in page.content

    def test_place_links_to_http_url(self, pages: list) -> None:
        """Place feature page links to the HttpUrl type page."""
        place_page = next(p for p in pages if p.path.stem == "place" and p.is_model)
        assert "HttpUrl" in place_page.content
