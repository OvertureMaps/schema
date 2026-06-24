"""End-to-end generation tests: verify generated modules match hand-written references."""

import ast
from pathlib import Path
from typing import Annotated, Literal

import pytest
from annotated_types import Ge
from codegen_test_support import discover_feature
from overture.schema.codegen.cli import _generate_pyspark
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.pyspark.pipeline import (
    GeneratedModule,
    generate_pyspark_module,
)
from pydantic import BaseModel


class SimpleModel(BaseModel):
    subtype: Literal["a", "b"]
    score: Annotated[float, Ge(0.0)] | None = None


class TestDivisionAreaGeneration:
    @pytest.fixture
    def generated(self) -> GeneratedModule:
        spec = discover_feature("DivisionArea")
        return generate_pyspark_module(spec)

    def test_generates_valid_python(self, generated: GeneratedModule) -> None:
        ast.parse(generated.content)

    def test_has_builder_function(self, generated: GeneratedModule) -> None:
        assert "def division_area_checks()" in generated.content

    def test_has_schema_constant(self, generated: GeneratedModule) -> None:
        assert "DIVISION_AREA_SCHEMA" in generated.content

    def test_output_path(self, generated: GeneratedModule) -> None:
        assert generated.path.name == "division_area.py"

    def test_checks_cover_expected_fields(self, generated: GeneratedModule) -> None:
        """Generated checks should cover the fields from the hand-written module."""
        content = generated.content
        # Hand-written checks: subtype, class, country, region, radio_group (is_land, is_territorial), admin_level
        for field in ["subtype", "class", "country", "region"]:
            assert f'field="{field}"' in content, f"Missing check for {field}"

    def test_schema_has_expected_fields(self, generated: GeneratedModule) -> None:
        """Schema should contain all expected DivisionArea fields."""
        content = generated.content
        expected_fields = [
            "id",
            "geometry",
            "bbox",
            "country",
            "version",
            "subtype",
            "class",
            "names",
            "is_land",
            "is_territorial",
            "region",
            "admin_level",
            "division_id",
            "theme",
            "type",
        ]
        for field in expected_fields:
            assert f'"{field}"' in content, f"Missing schema field: {field}"

    def test_uses_bbox_shared_struct(self, generated: GeneratedModule) -> None:
        """Should reference BBOX_STRUCT from _schema_structs (BBox is not a BaseModel)."""
        assert "BBOX_STRUCT" in generated.content

    def test_imports_constraint_expressions(self, generated: GeneratedModule) -> None:
        """Should import constraint expression functions."""
        content = generated.content
        assert (
            "from overture.schema.pyspark.expressions.constraint_expressions import"
            in content
        )

    def test_radio_group_constraint(self, generated: GeneratedModule) -> None:
        """Should have a radio_group check for is_land/is_territorial."""
        content = generated.content
        assert "check_radio_group" in content
        assert "is_land" in content
        assert "is_territorial" in content

    def test_subtype_has_check_enum(self, generated: GeneratedModule) -> None:
        """Subtype (ENUM-kind field) should produce a check_enum with member values."""
        assert "check_enum" in generated.content

    def test_country_uses_check_pattern(self, generated: GeneratedModule) -> None:
        """Country field (required newtype) produces both check_required and check_pattern."""
        assert "check_pattern" in generated.content
        # Bug #1 regression: check_required must not be skipped for required newtype fields.
        # With split checks, each descriptor produces its own function; both must appear.
        assert "check_required" in generated.content

    def test_region_uses_check_pattern(self, generated: GeneratedModule) -> None:
        """Region field produces check_pattern with the region-code label."""
        assert "ISO 3166-2 subdivision code" in generated.content


@pytest.mark.parametrize(
    "class_name,builder_name,schema_name",
    [
        ("DivisionArea", "division_area_checks", "DIVISION_AREA_SCHEMA"),
        ("Division", "division_checks", "DIVISION_SCHEMA"),
        ("DivisionBoundary", "division_boundary_checks", "DIVISION_BOUNDARY_SCHEMA"),
        ("Place", "place_checks", "PLACE_SCHEMA"),
    ],
)
class TestModelFeatureGeneration:
    @pytest.fixture
    def generated(self, class_name: str) -> GeneratedModule:
        spec = discover_feature(class_name)
        return generate_pyspark_module(spec)

    def test_generates_valid_python(
        self,
        generated: GeneratedModule,
        class_name: str,
        builder_name: str,
        schema_name: str,
    ) -> None:
        ast.parse(generated.content)

    def test_has_builder_function(
        self,
        generated: GeneratedModule,
        class_name: str,
        builder_name: str,
        schema_name: str,
    ) -> None:
        assert f"def {builder_name}()" in generated.content

    def test_has_schema_constant(
        self,
        generated: GeneratedModule,
        class_name: str,
        builder_name: str,
        schema_name: str,
    ) -> None:
        assert schema_name in generated.content

    def test_has_shared_bbox_struct(
        self,
        generated: GeneratedModule,
        class_name: str,
        builder_name: str,
        schema_name: str,
    ) -> None:
        assert "BBOX_STRUCT" in generated.content


class TestSegmentGeneration:
    @pytest.fixture
    def generated(self) -> GeneratedModule:
        spec = discover_feature("Segment")
        return generate_pyspark_module(spec)

    def test_generates_valid_python(self, generated: GeneratedModule) -> None:
        ast.parse(generated.content)

    def test_has_builder_and_schema(self, generated: GeneratedModule) -> None:
        assert "def segment_checks()" in generated.content
        assert "SEGMENT_SCHEMA" in generated.content

    def test_has_shared_bbox_struct(self, generated: GeneratedModule) -> None:
        assert "BBOX_STRUCT" in generated.content

    def test_has_variant_conditional_checks(self, generated: GeneratedModule) -> None:
        """Segment has subtype-gated fields using runtime values like 'road'."""
        assert "F.when" in generated.content
        assert "isin" in generated.content
        # Variant values must use the runtime string value, not the enum repr
        assert '"road"' in generated.content or "'road'" in generated.content
        assert "Subtype.ROAD" not in generated.content

    def test_array_discriminator_outside_lambda(
        self, generated: GeneratedModule
    ) -> None:
        """Top-level discriminator must wrap array_check, not appear inside the lambda."""
        # el["subtype"] must never appear — subtype is a top-level column, not an element field
        assert 'el["subtype"]' not in generated.content, (
            'el["subtype"] found — top-level discriminator placed inside array lambda'
        )
        # F.col("subtype") must appear as the discriminator reference
        assert 'F.col("subtype")' in generated.content


def test_cli_writes_init_modules(tmp_path: Path) -> None:
    spec = extract_model(SimpleModel, entry_point="overture.schema.simple:SimpleModel")
    out = tmp_path / "src"
    test_out = tmp_path / "tests"
    _generate_pyspark([spec], out, test_out)
    assert (out / "overture" / "schema" / "simple" / "__init__.py").exists()
    assert (out / "overture" / "schema" / "simple" / "simple_model.py").exists()
    assert (test_out / "overture" / "schema" / "simple" / "__init__.py").exists()
    assert (
        test_out / "overture" / "schema" / "simple" / "test_simple_model.py"
    ).exists()
