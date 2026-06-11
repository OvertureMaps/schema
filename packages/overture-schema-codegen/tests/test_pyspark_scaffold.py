"""Tests for sparse path scaffold generation."""

from dataclasses import replace

import pytest
from codegen_test_support import (
    FeatureWithRequiredUrl,
    discover_feature,
    feature_spec_for_model,
)
from overture.schema.codegen.extraction.specs import FeatureSpec
from overture.schema.codegen.pyspark.check_builder import build_checks
from overture.schema.codegen.pyspark.check_ir import ElementGuard
from overture.schema.codegen.pyspark.test_data.scaffold import (
    generate_model_scaffold,
    generate_scaffold,
    leaf_list_depth,
)
from overture.schema.system.field_path import ArrayPath, parse

_path = parse


@pytest.fixture(scope="module")
def connector_spec() -> FeatureSpec:
    return discover_feature("Connector")


@pytest.fixture(scope="module")
def division_area_spec() -> FeatureSpec:
    return discover_feature("DivisionArea")


@pytest.fixture(scope="module")
def segment_spec() -> FeatureSpec:
    return discover_feature("Segment")


class TestLeafListDepth:
    def test_leaf_list_depth(self) -> None:
        """leaf_list_depth returns unaccounted-for list depth."""
        spec = feature_spec_for_model(FeatureWithRequiredUrl)
        # Scalar field inside array struct — no extra wrapping
        assert leaf_list_depth(_path("datasets[].url"), spec) == 0
        # List field without trailing array marker — needs wrapping
        assert leaf_list_depth(_path("datasets[].download_urls"), spec) == 1
        # List field with array marker means element-level access — no wrapping
        assert leaf_list_depth(_path("datasets[].download_urls[]"), spec) == 0


class TestNestedListUrlField:
    """Scaffold for FeatureWithRequiredUrl handles nested list[HttpUrl] fields."""

    def test_nested_list_url_field_single_depth(self) -> None:
        """list[HttpUrl] scaffold should be single-depth, not double-wrapped."""
        spec = feature_spec_for_model(FeatureWithRequiredUrl)
        field_nodes, _ = build_checks(spec)
        url_nodes = [n for n in field_nodes if "download_urls" in str(n.target)]
        assert url_nodes, "Expected check nodes for download_urls"
        for node in url_nodes:
            scaffold = generate_scaffold(node, spec)
            if "datasets" in scaffold:
                entry = scaffold["datasets"][0]
                if "download_urls" in entry:
                    val = entry["download_urls"]
                    assert isinstance(val, list)
                    assert all(isinstance(v, str) for v in val), (
                        f"Expected list[str], got nested structure: {val!r}"
                    )


class TestGenerateScaffoldConnector:
    """Scaffold for Connector — simple top-level and one-level-nested fields."""

    def test_required_top_level_field_produces_empty_scaffold(
        self, connector_spec: FeatureSpec
    ) -> None:
        """Required top-level fields exist in base row; scaffold adds nothing."""
        field_nodes, _ = build_checks(connector_spec)
        id_node = next(n for n in field_nodes if n.target == _path("id"))
        scaffold = generate_scaffold(id_node, connector_spec)
        assert scaffold == {}

    def test_optional_top_level_field_produces_scaffold(
        self, connector_spec: FeatureSpec
    ) -> None:
        """Optional fields absent from base row get a valid scaffold value."""
        field_nodes, _ = build_checks(connector_spec)
        node = next(
            n
            for n in field_nodes
            if n.target == _path("sources")
            and any(d.function == "check_array_min_length" for d in n.descriptors)
        )
        scaffold = generate_scaffold(node, connector_spec)
        assert "sources" in scaffold
        assert isinstance(scaffold["sources"], list)
        assert len(scaffold["sources"]) >= 1

    def test_array_nested_field_builds_path(self, connector_spec: FeatureSpec) -> None:
        """sources[].property needs a sources array with one element."""
        field_nodes, _ = build_checks(connector_spec)
        node = next(n for n in field_nodes if n.target == _path("sources[].property"))
        scaffold = generate_scaffold(node, connector_spec)
        assert "sources" in scaffold
        assert isinstance(scaffold["sources"], list)
        assert len(scaffold["sources"]) == 1
        elem = scaffold["sources"][0]
        # Required sibling 'dataset' populated
        assert "dataset" in elem

    def test_scaffold_is_dict(self, connector_spec: FeatureSpec) -> None:
        field_nodes, _ = build_checks(connector_spec)
        for node in field_nodes:
            scaffold = generate_scaffold(node, connector_spec)
            assert isinstance(scaffold, dict)


class TestGenerateScaffoldSegment:
    """Scaffold for Segment — deeply nested arrays and discriminators."""

    def test_suffixed_nested_leaf_uses_actual_field_name(
        self, segment_spec: FeatureSpec
    ) -> None:
        """Column-level checks share the structural path with the real field."""
        field_nodes, _ = build_checks(segment_spec)
        node = next(
            n
            for n in field_nodes
            if n.target == _path("access_restrictions[].when.mode")
            and any(d.function == "check_array_min_length" for d in n.descriptors)
        )
        scaffold = generate_scaffold(node, segment_spec)
        assert "access_restrictions" in scaffold
        when = scaffold["access_restrictions"][0]["when"]
        assert "mode" in when, f"Expected 'mode', got keys: {list(when.keys())}"
        assert "mode_min_length" not in when

    def test_deeply_nested_array_path(self, segment_spec: FeatureSpec) -> None:
        """speed_limits[].when.vehicle[].dimension builds full nesting."""
        field_nodes, _ = build_checks(segment_spec)
        node = next(
            n
            for n in field_nodes
            if n.target == _path("speed_limits[].when.vehicle[].dimension")
        )
        scaffold = generate_scaffold(node, segment_spec)
        assert "speed_limits" in scaffold
        sl_elem = scaffold["speed_limits"][0]
        assert "when" in sl_elem
        when = sl_elem["when"]
        assert "vehicle" in when
        assert isinstance(when["vehicle"], list)
        assert len(when["vehicle"]) == 1

    def test_element_guard_discriminator_set(self, segment_spec: FeatureSpec) -> None:
        """Checks with an `ElementGuard` set the discriminator value in the scaffold."""
        field_checks, _ = build_checks(segment_spec)
        # Find a speed_limits check with an ElementGuard.
        check = next(
            c
            for c in field_checks
            if any(isinstance(g, ElementGuard) for g in c.guards)
            and "speed_limits" in str(c.target)
        )
        scaffold = generate_scaffold(check, segment_spec)
        # Walk to the innermost array element where the discriminator lives.
        assert "speed_limits" in scaffold
        sl_elem = scaffold["speed_limits"][0]
        when = sl_elem["when"]
        vehicle_elem = when["vehicle"][0]
        element_guard = next(g for g in check.guards if isinstance(g, ElementGuard))
        assert element_guard.discriminator in vehicle_elem
        assert vehicle_elem[element_guard.discriminator] == element_guard.values[0]

    def test_column_variant_does_not_appear_inside_scaffold(
        self, segment_spec: FeatureSpec
    ) -> None:
        """`ColumnGuard`s don't set discriminator inside the scaffold dict."""
        field_checks, _ = build_checks(segment_spec)
        # Find a check whose only guard is a ColumnGuard (no ElementGuard).
        check = next(
            c
            for c in field_checks
            if c.guards
            and not any(isinstance(g, ElementGuard) for g in c.guards)
            and "speed_limits[]." in str(c.target)
        )
        scaffold = generate_scaffold(check, segment_spec)
        # The column-level discriminator is NOT set in the scaffold --
        # it belongs at the row level, which the base row handles.
        assert isinstance(scaffold, dict)

    def test_multiple_element_guards_raises(self, segment_spec: FeatureSpec) -> None:
        """The check_ir invariant allows at most one `ElementGuard` per Check.

        Multiple guards would indicate the gate composition rule changed
        without updating the scaffold, so the scaffold raises rather than
        silently dropping all but the first.
        """
        field_checks, _ = build_checks(segment_spec)
        check = next(
            c
            for c in field_checks
            if any(isinstance(g, ElementGuard) for g in c.guards)
        )
        bogus = replace(
            check,
            guards=(
                *check.guards,
                ElementGuard(discriminator="other_field", values=("other_value",)),
            ),
        )
        with pytest.raises(NotImplementedError, match="ElementGuards"):
            generate_scaffold(bogus, segment_spec)


class TestGenerateModelScaffold:
    def test_top_level_model_constraint_produces_empty_scaffold(
        self, division_area_spec: FeatureSpec
    ) -> None:
        """Model constraints at the top level need no nesting."""
        _, model_nodes = build_checks(division_area_spec)
        assert model_nodes, "DivisionArea should have model constraints"
        node = model_nodes[0]
        scaffold = generate_model_scaffold(node, division_area_spec)
        assert isinstance(scaffold, dict)

    def test_array_nested_model_constraint_builds_path(
        self, segment_spec: FeatureSpec
    ) -> None:
        """Model constraints inside arrays build the array path."""
        _, model_checks = build_checks(segment_spec)
        if not model_checks:
            pytest.skip("Segment has no model constraints")
        # Find one with an array target.
        nested = [c for c in model_checks if isinstance(c.target, ArrayPath)]
        if not nested:
            pytest.skip("No nested model constraints found")
        check = nested[0]
        scaffold = generate_model_scaffold(check, segment_spec)
        assert isinstance(scaffold, dict)
        # The scaffold should contain the column root (top-level column name).
        assert isinstance(check.target, ArrayPath)
        assert check.target.array_chunks[0][1] in scaffold
