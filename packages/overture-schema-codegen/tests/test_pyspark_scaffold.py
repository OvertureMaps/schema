"""Tests for sparse path scaffold generation."""

import copy
from dataclasses import replace
from typing import Any

import pytest
from codegen_test_support import (
    FeatureWithRequiredUrl,
    discover_feature,
    spec_for_model,
)
from overture.schema.codegen.extraction.specs import ModelSpec, UnionSpec
from overture.schema.codegen.pyspark.check_builder import build_checks
from overture.schema.codegen.pyspark.check_ir import (
    Check,
    ColumnGuard,
    ElementGuard,
    ModelCheck,
)
from overture.schema.codegen.pyspark.constraint_dispatch import RequireAnyOf
from overture.schema.codegen.pyspark.test_data.base_row import (
    generate_arm_rows,
    generate_base_row,
)
from overture.schema.codegen.pyspark.test_data.scaffold import (
    generate_model_scaffold,
    generate_scaffold,
    leaf_list_depth,
)
from overture.schema.system.field_path import ArraySegment, Iterated, parse
from pydantic import TypeAdapter

_path = parse


def _deep_merge(base: dict, scaffold: dict) -> dict:
    """Merge `scaffold` onto a deep copy of `base` (harness `deep_merge` semantics).

    Dicts merge recursively; every other value (including lists) replaces the
    base value. Mirrors `overture.schema.pyspark`'s conformance harness so the
    validated row matches what the generated suite builds.
    """
    result = copy.deepcopy(base)
    for key, value in scaffold.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _check_belongs_to_arm(check: Check, arm: str) -> bool:
    """Whether a field check applies to a union arm (every `ColumnGuard` admits it)."""
    return all(arm in g.values for g in check.guards if isinstance(g, ColumnGuard))


@pytest.fixture(scope="module")
def connector_spec() -> ModelSpec:
    return discover_feature("Connector")


@pytest.fixture(scope="module")
def division_area_spec() -> ModelSpec:
    return discover_feature("DivisionArea")


@pytest.fixture(scope="module")
def segment_spec() -> ModelSpec:
    return discover_feature("Segment")


class TestLeafListDepth:
    def test_leaf_list_depth(self) -> None:
        """leaf_list_depth returns unaccounted-for list depth."""
        spec = spec_for_model(FeatureWithRequiredUrl)
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
        spec = spec_for_model(FeatureWithRequiredUrl)
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
        self, connector_spec: ModelSpec
    ) -> None:
        """Required top-level fields exist in base row; scaffold adds nothing."""
        field_nodes, _ = build_checks(connector_spec)
        id_node = next(n for n in field_nodes if n.target == _path("id"))
        scaffold = generate_scaffold(id_node, connector_spec)
        assert scaffold == {}

    def test_optional_top_level_field_produces_scaffold(
        self, connector_spec: ModelSpec
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

    def test_array_nested_field_builds_path(self, connector_spec: ModelSpec) -> None:
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

    def test_scaffold_is_dict(self, connector_spec: ModelSpec) -> None:
        field_nodes, _ = build_checks(connector_spec)
        for node in field_nodes:
            scaffold = generate_scaffold(node, connector_spec)
            assert isinstance(scaffold, dict)


class TestGenerateScaffoldSegment:
    """Scaffold for Segment — deeply nested arrays and discriminators."""

    def test_suffixed_nested_leaf_uses_actual_field_name(
        self, segment_spec: ModelSpec
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

    def test_deeply_nested_array_path(self, segment_spec: ModelSpec) -> None:
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

    def test_element_guard_discriminator_set(self, segment_spec: ModelSpec) -> None:
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
        self, segment_spec: ModelSpec
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

    def test_multiple_element_guards_raises(self, segment_spec: ModelSpec) -> None:
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


# Models whose scaffolds must merge onto a base row to form a valid instance.
# Spans a union with a union-in-array (`Segment`'s `when.vehicle[]`), record
# specs with `require_any_of` and optional nested-model arrays, a map field
# (`Infrastructure.source_tags`), and `list[list[...]]` arrays
# (`Division.hierarchies[][]`, whose inner `[]` is an anonymous array segment --
# the nested list, carrying no field name of its own -- so anonymous-segment
# wrapping is covered). The
# conformance suite only asserts each scenario's own expected violation is
# absent from its valid row -- whole-row validity of a scaffold is checked here,
# so a model-specific scaffold defect can't hide behind it.
_VALID_ROW_MODELS = [
    "Segment",
    "Connector",
    "Division",
    "DivisionArea",
    "DivisionBoundary",
    "Place",
    "Building",
    "BuildingPart",
    "Address",
    "Infrastructure",
    "Land",
    "LandCover",
    "LandUse",
    "Water",
    "Bathymetry",
]


def _base_rows_and_adapter(spec: ModelSpec) -> tuple[dict[str, dict[str, Any]], Any]:
    """Return per-arm base rows and a Pydantic adapter for a spec.

    A `UnionSpec` yields one base row per discriminator arm, validated against
    the union annotation. A record spec yields a single row keyed by `""` (a
    sentinel arm carrying no `ColumnGuard`, so `_check_belongs_to_arm` admits
    every record-spec check) and validates against the source class.
    """
    if isinstance(spec, UnionSpec):
        return generate_arm_rows(spec), TypeAdapter(spec.source_annotation)
    assert spec.source_type is not None
    return {"": generate_base_row(spec)}, TypeAdapter(spec.source_type)


class TestScaffoldsProduceValidRows:
    """Ground truth for finding #1: a scaffold merged onto the base row is valid.

    The conformance harness builds the `::valid` row as
    `deep_merge(base_row, scaffold)` with no mutation, then asserts the check
    does not fire. That assertion is only meaningful when the merged row is a
    genuinely valid instance -- otherwise unrelated `required` /
    `require_any_of` violations (or a vacuous, target-absent row) let a check
    that wrongly rejects a valid value ship green. These tests validate the
    merged row against the Pydantic schema directly: the scaffold must reach
    the target while keeping every model on the path valid.
    """

    @pytest.fixture(scope="module", params=_VALID_ROW_MODELS)
    def model_case(
        self, request: pytest.FixtureRequest
    ) -> tuple[ModelSpec, dict[str, dict[str, Any]], Any]:
        spec = discover_feature(request.param)
        arm_rows, adapter = _base_rows_and_adapter(spec)
        return spec, arm_rows, adapter

    def test_field_scaffolds_validate(
        self, model_case: tuple[ModelSpec, dict[str, dict[str, Any]], Any]
    ) -> None:
        spec, arm_rows, adapter = model_case
        field_checks, _ = build_checks(spec)
        for check in field_checks:
            scaffold = generate_scaffold(check, spec)
            for arm, base in arm_rows.items():
                if not _check_belongs_to_arm(check, arm):
                    continue
                adapter.validate_python(_deep_merge(base, scaffold))

    def test_model_scaffolds_validate(
        self, model_case: tuple[ModelSpec, dict[str, dict[str, Any]], Any]
    ) -> None:
        spec, arm_rows, adapter = model_case
        _, model_checks = build_checks(spec)
        for check in model_checks:
            scaffold = generate_model_scaffold(check, spec)
            for arm, base in arm_rows.items():
                if not (check.arm is None or check.arm == arm):
                    continue
                adapter.validate_python(_deep_merge(base, scaffold))


class TestGenerateModelScaffold:
    def test_top_level_model_constraint_produces_empty_scaffold(
        self, division_area_spec: ModelSpec
    ) -> None:
        """Model constraints at the top level need no nesting."""
        _, model_nodes = build_checks(division_area_spec)
        assert model_nodes, "DivisionArea should have model constraints"
        node = model_nodes[0]
        scaffold = generate_model_scaffold(node, division_area_spec)
        assert isinstance(scaffold, dict)

    def test_map_value_model_constraint_produces_empty_scaffold(
        self, connector_spec: ModelSpec
    ) -> None:
        """A `dict[K, Model]` value-model constraint needs no scaffold.

        The mutation (`map_path=`) owns map navigation -- it corrupts the
        base row's single map entry in place, or stubs one when the map is
        absent. A dict scaffold can't replace a base-row map entry under
        deep_merge's recursive dict merge, so {} is correct, not the
        row-root-mutation bug.
        """
        mc = ModelCheck(
            descriptor=RequireAnyOf(field_names=("foo", "bar")),
            target=_path("subs{value}"),
        )
        assert generate_model_scaffold(mc, connector_spec) == {}

    def test_array_nested_model_constraint_builds_path(
        self, segment_spec: ModelSpec
    ) -> None:
        """Model constraints inside arrays build the array path."""
        _, model_checks = build_checks(segment_spec)
        if not model_checks:
            pytest.skip("Segment has no model constraints")
        # Find one with an array target (array-first `Iterated`).
        nested = [
            c
            for c in model_checks
            if isinstance(c.target, Iterated)
            and isinstance(c.target.iter_frames[0][1], ArraySegment)
        ]
        if not nested:
            pytest.skip("No nested model constraints found")
        check = nested[0]
        scaffold = generate_model_scaffold(check, segment_spec)
        assert isinstance(scaffold, dict)
        # The scaffold should contain the column root (top-level column name).
        assert isinstance(check.target, Iterated)
        assert check.target.iter_frames[0][1].name in scaffold
