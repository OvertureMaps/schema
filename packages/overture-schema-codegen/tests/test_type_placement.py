"""Tests for type placement module."""

from collections.abc import Sequence
from pathlib import PurePosixPath

import overture.schema.system.primitive as _system_primitive
from codegen_test_support import STR_TYPE, flat_specs_from_discovery, make_union_spec
from overture.schema.codegen.link_computation import relative_link
from overture.schema.codegen.model_extraction import expand_model_tree
from overture.schema.codegen.path_assignment import (
    GEOMETRY_PAGE,
    PRIMITIVES_PAGE,
    build_placement_registry,
)
from overture.schema.codegen.primitive_extraction import (
    partition_primitive_and_geometry_names,
)
from overture.schema.codegen.specs import (
    AnnotatedField,
    FeatureSpec,
    FieldSpec,
    ModelSpec,
    SupplementarySpec,
)
from overture.schema.codegen.type_collection import collect_all_supplementary_types

_PRIMITIVE_NAMES, _GEOMETRY_NAMES = partition_primitive_and_geometry_names(
    _system_primitive
)

_SCHEMA_ROOT = "overture.schema"


def _build_registry(
    feature_specs: list[ModelSpec],
) -> tuple[dict[str, PurePosixPath], dict[str, SupplementarySpec]]:
    """Build placement registry with standard aggregate names."""
    cache: dict[type, ModelSpec] = {}
    for spec in feature_specs:
        expand_model_tree(spec, cache)
    all_specs = collect_all_supplementary_types(feature_specs)
    registry = build_placement_registry(
        feature_specs, all_specs, _PRIMITIVE_NAMES, _GEOMETRY_NAMES, _SCHEMA_ROOT
    )
    return registry, all_specs


class TestRelativeLink:
    """Test relative path computation between pages."""

    def test_same_directory(self) -> None:
        source = PurePosixPath("buildings/building.md")
        target = PurePosixPath("buildings/facade_material.md")
        assert relative_link(source, target) == "facade_material.md"

    def test_sibling_directory(self) -> None:
        source = PurePosixPath("buildings/building.md")
        target = PurePosixPath("core/names/names.md")
        assert relative_link(source, target) == "../core/names/names.md"

    def test_within_core(self) -> None:
        source = PurePosixPath("core/names/names.md")
        target = PurePosixPath("core/sources/sources.md")
        assert relative_link(source, target) == "../sources/sources.md"

    def test_to_aggregate_page(self) -> None:
        source = PurePosixPath("core/names/names.md")
        target = PurePosixPath("system/primitive/primitives.md")
        assert relative_link(source, target) == "../../system/primitive/primitives.md"


class TestBuildPlacementRegistry:
    """Test the full placement registry builder with module-mirrored paths."""

    def test_features_at_theme_level(self) -> None:
        """Features land directly in their theme directory."""
        specs = flat_specs_from_discovery("buildings")
        registry, _ = _build_registry(specs)

        assert registry["Building"] == PurePosixPath("buildings/building.md")
        assert registry["BuildingPart"] == PurePosixPath("buildings/building_part.md")

    def test_shared_types_mirror_source_modules(self) -> None:
        """Core/system types land in directories matching their module path."""
        specs = flat_specs_from_discovery("buildings")
        registry, _ = _build_registry(specs)

        if "Names" in registry:
            assert str(registry["Names"]).startswith("core/")

    def test_no_duplicate_paths(self) -> None:
        """No two individual types share an output path."""
        specs = flat_specs_from_discovery()
        registry, _ = _build_registry(specs)

        aggregate_pages = {
            PurePosixPath("system/primitive/primitives.md"),
            PurePosixPath("system/primitive/geometry.md"),
        }
        individual = [p for p in registry.values() if p not in aggregate_pages]
        assert len(individual) == len(set(individual)), (
            "Duplicate output paths detected"
        )

    def test_aggregate_pages_at_system_primitive(self) -> None:
        """Primitive and geometry aggregate pages under system/primitive/."""
        assert PRIMITIVES_PAGE == PurePosixPath("system/primitive/primitives.md")
        assert GEOMETRY_PAGE == PurePosixPath("system/primitive/geometry.md")

    def test_supplementary_types_nested_under_types(self) -> None:
        """Supplementary types in a feature directory go under types/."""
        specs = flat_specs_from_discovery("buildings")
        registry, _ = _build_registry(specs)

        # BuildingClass is a supplementary type from the buildings module
        assert registry["BuildingClass"] == PurePosixPath(
            "buildings/types/building_class.md"
        )

    def test_submodule_supplementary_types_nested_under_types(self) -> None:
        """Supplementary types in a feature subdirectory go under types/."""
        specs = flat_specs_from_discovery("divisions")
        registry, _ = _build_registry(specs)

        # AreaClass is from overture.schema.divisions.division_area.enums,
        # a subdirectory of the divisions feature directory.
        assert registry["AreaClass"] == PurePosixPath(
            "divisions/types/division_area/area_class.md"
        )

    def test_shared_types_not_nested(self) -> None:
        """Core/system supplementary types stay at their module-mirrored path."""
        specs = flat_specs_from_discovery("buildings")
        registry, _ = _build_registry(specs)

        # Names is from overture.schema.core -- no features there, no nesting
        if "Names" in registry:
            path = str(registry["Names"])
            assert path.startswith("core/")
            assert "/types/" not in path


class TestPlacementWithUnionSpec:
    """Tests for placement registry with UnionSpec."""

    def test_union_spec_gets_placement(self) -> None:
        """UnionSpec is placed alongside ModelSpec in the registry."""
        from pydantic import BaseModel

        class Base(BaseModel):
            name: str

        class A(Base):
            x: int

        union_spec = make_union_spec(
            annotated_fields=[
                AnnotatedField(
                    field_spec=FieldSpec(
                        name="name",
                        type_info=STR_TYPE,
                        description=None,
                        is_required=True,
                    ),
                    variant_sources=None,
                ),
            ],
            members=[A],
            common_base=Base,
            entry_point="test.package:TestUnion",
        )

        feature_specs: Sequence[FeatureSpec] = [union_spec]
        all_specs = collect_all_supplementary_types(feature_specs)
        registry = build_placement_registry(
            feature_specs, all_specs, [], [], "test.package"
        )
        assert "TestUnion" in registry
