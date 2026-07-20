"""Tests for the PySpark generation pipeline."""

import ast
from pathlib import PurePosixPath
from typing import Annotated, Literal

import pytest
from annotated_types import Ge
from codegen_test_support import find_theme
from overture.schema.codegen.extraction.model_extraction import extract_model
from overture.schema.codegen.extraction.specs import (
    ModelSpec,
)
from overture.schema.codegen.pyspark.check_ir import Check
from overture.schema.codegen.pyspark.constraint_dispatch import ExpressionDescriptor
from overture.schema.codegen.pyspark.pipeline import (
    GeneratedModule,
    PipelineOutput,
    _extract_geometry_types,
    generate_pyspark_module,
    generate_pyspark_modules,
)
from overture.schema.codegen.spec_discovery import extract_model_spec
from overture.schema.system.field_path import Direct
from overture.schema.system.primitive import GeometryType
from pydantic import BaseModel


class SimpleModel(BaseModel):
    subtype: Literal["a", "b"]
    score: Annotated[float, Ge(0.0)] | None = None


class BoundsModel(BaseModel):
    value: Annotated[float, Ge(0.0)]


class TestGeneratePysparkModule:
    @pytest.fixture
    def simple_module(self) -> GeneratedModule:
        return generate_pyspark_module(
            extract_model(SimpleModel, entry_point="overture.schema.simple:SimpleModel")
        )

    def test_returns_generated_module(self, simple_module: GeneratedModule) -> None:
        assert isinstance(simple_module, GeneratedModule)

    def test_content_is_nonempty(self, simple_module: GeneratedModule) -> None:
        assert simple_module.content

    def test_content_is_valid_python(self, simple_module: GeneratedModule) -> None:
        ast.parse(simple_module.content)

    def test_path_uses_snake_case_model_name(
        self, simple_module: GeneratedModule
    ) -> None:
        assert simple_module.path == PurePosixPath(
            "overture/schema/simple/simple_model.py"
        )

    def test_path_for_bounds_model(self) -> None:
        result = generate_pyspark_module(
            extract_model(BoundsModel, entry_point="overture.schema.bounds:BoundsModel")
        )
        assert result.path == PurePosixPath("overture/schema/bounds/bounds_model.py")

    def test_content_contains_checks_function(
        self, simple_module: GeneratedModule
    ) -> None:
        assert "simple_model_checks" in simple_module.content

    def test_content_contains_schema_constant(
        self, simple_module: GeneratedModule
    ) -> None:
        assert "SIMPLE_MODEL_SCHEMA" in simple_module.content


def _two_specs() -> list[ModelSpec]:
    return [
        extract_model(SimpleModel, entry_point="overture.schema.simple:SimpleModel"),
        extract_model(BoundsModel, entry_point="overture.schema.bounds:BoundsModel"),
    ]


def _features(modules: list[GeneratedModule]) -> list[GeneratedModule]:
    return [m for m in modules if m.path.name != "__init__.py"]


class TestGeneratePysparkModules:
    @pytest.fixture
    def two_spec_modules(self) -> PipelineOutput:
        return generate_pyspark_modules(_two_specs())

    def test_empty_specs_returns_no_modules(self) -> None:
        result = generate_pyspark_modules([])
        assert result.source == []
        assert result.test == []

    def test_one_module_per_spec(self, two_spec_modules: PipelineOutput) -> None:
        assert len(_features(two_spec_modules.source)) == 2

    def test_paths_unique_per_tree(self, two_spec_modules: PipelineOutput) -> None:
        # source and test trees mirror the same dirs; uniqueness is
        # only required within each tree, not across them.
        for tree in (two_spec_modules.source, two_spec_modules.test):
            paths = [m.path for m in tree]
            assert len(paths) == len(set(paths))

    def test_all_content_is_valid_python(
        self, two_spec_modules: PipelineOutput
    ) -> None:
        for mod in (*two_spec_modules.source, *two_spec_modules.test):
            ast.parse(mod.content)

    def test_divisions_theme_produces_division_area(
        self, all_discovered_models: dict
    ) -> None:
        """divisions theme should produce a division_area.py module."""
        division_specs: list[ModelSpec] = []
        for key, entry in all_discovered_models.items():
            if find_theme(key.tags) != "divisions":
                continue
            spec = extract_model_spec(key, entry)
            if spec is not None:
                division_specs.append(spec)

        results = generate_pyspark_modules(division_specs)
        names = {r.path.stem for r in results.source}
        assert "division_area" in names


class TestTestModuleGeneration:
    @pytest.fixture
    def all_modules(self) -> PipelineOutput:
        return generate_pyspark_modules(_two_specs())

    def test_generates_test_modules(self, all_modules: PipelineOutput) -> None:
        assert len(_features(all_modules.test)) == 2  # one per feature spec

    def test_test_module_paths(self, all_modules: PipelineOutput) -> None:
        paths = {m.path.name for m in _features(all_modules.test)}
        assert "test_simple_model.py" in paths
        assert "test_bounds_model.py" in paths

    def test_test_modules_are_valid_python(self, all_modules: PipelineOutput) -> None:
        for mod in all_modules.test:
            ast.parse(mod.content)

    def test_test_module_contains_imports(self, all_modules: PipelineOutput) -> None:
        for mod in _features(all_modules.test):
            assert "_support.harness import" in mod.content
            assert "_support.scenarios import" in mod.content


def _extract_scenarios_block(content: str) -> str:
    """Extract the SCENARIOS list literal from generated test source."""
    start = content.index("SCENARIOS:")
    end = content.index("]", start) + 1
    return content[start:end]


class TestPerArmTestGeneration:
    """Union features with multiple examples produce per-arm test modules."""

    @pytest.fixture
    def segment_modules(self, all_discovered_models: dict) -> PipelineOutput:
        specs: list[ModelSpec] = []
        for key, entry in all_discovered_models.items():
            if key.name != "segment":
                continue
            spec = extract_model_spec(key, entry)
            if spec is not None:
                specs.append(spec)
        return generate_pyspark_modules(specs)

    def test_produces_per_arm_test_files(self, segment_modules: PipelineOutput) -> None:
        paths = {m.path.name for m in _features(segment_modules.test)}
        assert "test_segment_road.py" in paths
        assert "test_segment_rail.py" in paths

    def test_no_monolithic_test_file(self, segment_modules: PipelineOutput) -> None:
        """When per-arm tests exist, no undifferentiated test_segment.py."""
        paths = {m.path.name for m in _features(segment_modules.test)}
        assert "test_segment.py" not in paths

    def test_per_arm_modules_are_valid_python(
        self, segment_modules: PipelineOutput
    ) -> None:
        for mod in segment_modules.test:
            ast.parse(mod.content)

    def test_road_module_has_road_checks(self, segment_modules: PipelineOutput) -> None:
        road = next(
            m for m in segment_modules.test if m.path.name == "test_segment_road.py"
        )
        assert "road_surface" in road.content

    def test_rail_module_has_rail_checks(self, segment_modules: PipelineOutput) -> None:
        rail = next(
            m for m in segment_modules.test if m.path.name == "test_segment_rail.py"
        )
        assert "rail_flags" in rail.content

    def test_road_module_no_rail_field_scenarios(
        self, segment_modules: PipelineOutput
    ) -> None:
        road = next(
            m for m in segment_modules.test if m.path.name == "test_segment_road.py"
        )
        scenarios = _extract_scenarios_block(road.content)
        assert "rail_flags[].values" not in scenarios

    def test_rail_module_no_road_field_scenarios(
        self, segment_modules: PipelineOutput
    ) -> None:
        rail = next(
            m for m in segment_modules.test if m.path.name == "test_segment_rail.py"
        )
        scenarios = _extract_scenarios_block(rail.content)
        assert "road_surface" not in scenarios

    def test_non_union_still_gets_single_test(self) -> None:
        """Non-union features produce a single test module (unchanged)."""
        modules = generate_pyspark_modules(
            [
                extract_model(
                    SimpleModel, entry_point="overture.schema.simple:SimpleModel"
                )
            ]
        )
        tests = _features(modules.test)
        assert len(tests) == 1
        assert tests[0].path.name == "test_simple_model.py"


class TestNestedSourcePaths:
    def test_module_path_mirrors_entry_point(self) -> None:
        spec = extract_model(
            SimpleModel, entry_point="overture.schema.simple:SimpleModel"
        )
        modules = generate_pyspark_modules([spec])
        features = _features(modules.source)
        assert len(features) == 1
        assert features[0].path == PurePosixPath(
            "overture/schema/simple/simple_model.py"
        )

    def test_two_packages_no_collision(self) -> None:
        a = extract_model(SimpleModel, entry_point="overture.schema.places:Place")
        b = extract_model(SimpleModel, entry_point="annex.schema.places:Place")
        modules = generate_pyspark_modules([a, b])
        paths = {m.path for m in _features(modules.source)}
        assert PurePosixPath("overture/schema/places/place.py") in paths
        assert PurePosixPath("annex/schema/places/place.py") in paths


_EXPECTED_INIT_PATHS = {
    PurePosixPath("__init__.py"),
    PurePosixPath("overture/__init__.py"),
    PurePosixPath("overture/schema/__init__.py"),
    PurePosixPath("overture/schema/simple/__init__.py"),
}


def _init_paths(modules: list[GeneratedModule]) -> set[PurePosixPath]:
    return {m.path for m in modules if m.path.name == "__init__.py"}


class TestInitModuleEmission:
    def test_intermediate_dirs_get_init_modules(self) -> None:
        spec = extract_model(
            SimpleModel, entry_point="overture.schema.simple:SimpleModel"
        )
        modules = generate_pyspark_modules([spec])
        assert _init_paths(modules.source) == _EXPECTED_INIT_PATHS

    def test_init_modules_are_empty(self) -> None:
        spec = extract_model(
            SimpleModel, entry_point="overture.schema.simple:SimpleModel"
        )
        modules = generate_pyspark_modules([spec])
        init = next(m for m in modules.source if m.path.name == "__init__.py")
        assert init.content == ""

    def test_shared_dirs_emitted_once(self) -> None:
        a = extract_model(SimpleModel, entry_point="overture.schema.simple:SimpleModel")
        b = extract_model(BoundsModel, entry_point="overture.schema.simple:BoundsModel")
        modules = generate_pyspark_modules([a, b])
        init_paths = [m.path for m in modules.source if m.path.name == "__init__.py"]
        assert len(init_paths) == len(set(init_paths))


class TestNoRegistryEmitted:
    def test_registry_module_is_no_longer_generated(self) -> None:
        # The runtime builds the registry via entry-point discovery; codegen
        # must not emit `_registry.py`.
        spec = extract_model(
            SimpleModel, entry_point="overture.schema.simple:SimpleModel"
        )
        modules = generate_pyspark_modules([spec])
        for tree in (modules.source, modules.test):
            assert all(m.path.name != "_registry.py" for m in tree)


class TestNestedTestPaths:
    def test_test_module_path_mirrors_source(self) -> None:
        spec = extract_model(
            SimpleModel, entry_point="overture.schema.simple:SimpleModel"
        )
        modules = generate_pyspark_modules([spec])
        tests = _features(modules.test)
        assert len(tests) == 1
        assert tests[0].path == PurePosixPath(
            "overture/schema/simple/test_simple_model.py"
        )

    def test_test_module_imports_nested_expression(self) -> None:
        spec = extract_model(
            SimpleModel, entry_point="overture.schema.simple:SimpleModel"
        )
        modules = generate_pyspark_modules([spec])
        test_mod = next(iter(_features(modules.test)))
        assert (
            "from overture.schema.pyspark.expressions.generated.overture.schema.simple.simple_model import"
            in test_mod.content
        )

    def test_test_dirs_get_init_modules(self) -> None:
        spec = extract_model(
            SimpleModel, entry_point="overture.schema.simple:SimpleModel"
        )
        modules = generate_pyspark_modules([spec])
        # Source-tree init modules already covered in TestInitModuleEmission.
        # The test tree must mirror the same package layout.
        assert _init_paths(modules.test) == _EXPECTED_INIT_PATHS


class TestExtractGeometryTypes:
    """`_extract_geometry_types` aggregates across descriptors and checks."""

    def test_aggregates_across_descriptors(self) -> None:
        checks = [
            Check(
                descriptors=(
                    ExpressionDescriptor(
                        function="check_geometry_type",
                        args=(GeometryType.POINT,),
                    ),
                ),
                target=Direct(),
            ),
            Check(
                descriptors=(
                    ExpressionDescriptor(
                        function="check_geometry_type",
                        args=(GeometryType.POLYGON, GeometryType.LINE_STRING),
                    ),
                ),
                target=Direct(),
            ),
        ]
        assert _extract_geometry_types(checks) == (
            GeometryType.LINE_STRING,
            GeometryType.POINT,
            GeometryType.POLYGON,
        )

    def test_returns_empty_when_absent(self) -> None:
        assert _extract_geometry_types([]) == ()
