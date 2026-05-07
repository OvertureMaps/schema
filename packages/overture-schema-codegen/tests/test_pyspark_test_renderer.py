"""Tests for the generated conformance test module renderer."""

import ast
import re
from enum import Enum

import pytest
from overture.schema.codegen.extraction.field import ArrayOf, Primitive
from overture.schema.codegen.pyspark.check_ir import (
    Check,
    ColumnGuard,
    ElementGuard,
    ModelCheck,
)
from overture.schema.codegen.pyspark.constraint_dispatch import (
    ExpressionDescriptor,
    ForbidIf,
    MinFieldsSet,
    RadioGroup,
    RequireAnyOf,
    RequireIf,
)
from overture.schema.codegen.pyspark.test_renderer import (
    render_test_module as _real_render_test_module,
)
from overture.schema.system.field_constraint.string import (
    CountryCodeAlpha2Constraint,
    NoWhitespaceConstraint,
)
from overture.schema.system.field_path import ArrayPath, ScalarPath, parse
from overture.schema.system.model_constraint import FieldEqCondition, Not
from overture.schema.system.primitive.geom import GeometryType

_path = parse

# Placeholder expression import path -- tests parse the rendered source
# rather than executing it, so the import target need not be real.
_TEST_EXPRESSION_IMPORT = "_placeholder.expression_module"


def render_test_module(*args: object, **kwargs: object) -> str:
    """Invoke the renderer with placeholder `expression_import`/`support_prefix`.

    Tests parse the rendered source rather than executing it, so neither
    the expression import target nor the relative `_support` package depth
    needs to match a real layout. Defining this as a free function (rather
    than a fixture) keeps test bodies terse.
    """
    kwargs.setdefault("expression_import", _TEST_EXPRESSION_IMPORT)
    kwargs.setdefault("support_prefix", "..")
    return _real_render_test_module(*args, **kwargs)  # type: ignore[arg-type]


def make_check(
    function: str,
    target: object,
    *,
    args: tuple[object, ...] = (),
    kwargs: tuple[tuple[str, object], ...] = (),
    constraint_type: object = None,
    label: str | None = None,
    check_name: str | None = None,
    guards: tuple[object, ...] = (),
) -> Check:
    """Build a single-descriptor Check; defaults match Check/ExpressionDescriptor."""
    descriptor_kwargs: dict[str, object] = {"function": function}
    if args:
        descriptor_kwargs["args"] = args
    if kwargs:
        descriptor_kwargs["kwargs"] = kwargs
    if constraint_type is not None:
        descriptor_kwargs["constraint_type"] = constraint_type
    if label is not None:
        descriptor_kwargs["label"] = label
    if check_name is not None:
        descriptor_kwargs["check_name"] = check_name
    return Check(
        descriptors=(ExpressionDescriptor(**descriptor_kwargs),),  # type: ignore[arg-type]
        target=target,  # type: ignore[arg-type]
        guards=guards,  # type: ignore[arg-type]
    )


def _array(
    column: str,
    inner_struct_paths: tuple[tuple[str, ...], ...] = (),
    leaf_path: tuple[str, ...] = (),
) -> ArrayPath:
    """Build an ArrayPath from a column name, inner struct paths, and a leaf path.

    Each entry in `inner_struct_paths` is `(prefix_structs..., inner_array_name)`:
    the prefix names become struct segments and the last name becomes an
    inner ArraySegment.
    """
    column_path = _path(column)
    if isinstance(column_path, ScalarPath):
        prefix_structs = column_path.segments[:-1]
        outer_name = column_path.segments[-1].name
        prefix = ScalarPath(segments=prefix_structs)
        path = prefix.append_array(outer_name, iter_count=1)
    else:
        path = column_path
    for sp in inner_struct_paths:
        for n in sp[:-1]:
            path = path.append_struct(n)
        path = path.append_array(sp[-1], iter_count=1)
    for n in leaf_path:
        path = path.append_struct(n)
    return path


class TestRenderTestModuleParseable:
    def test_renders_valid_python_with_nodes(self) -> None:
        nodes = [make_check("check_required", _path("country"))]
        source = render_test_module("division_area", nodes, [])
        ast.parse(source)

    def test_empty_nodes_renders_valid_python(self) -> None:
        source = render_test_module("empty", [], [])
        ast.parse(source)


class TestBaseRow:
    def test_default_base_rows_are_empty(self) -> None:
        source = render_test_module("test", [], [])
        assert "BASE_ROW_SPARSE: dict = {}" in source
        assert "BASE_ROW_POPULATED: dict = {}" in source

    def test_provided_sparse_row_rendered(self) -> None:
        source = render_test_module("test", [], [], base_row_sparse={"id": "abc"})
        assert "BASE_ROW_SPARSE: dict = " in source
        assert "'id': 'abc'" in source

    def test_provided_populated_row_rendered(self) -> None:
        source = render_test_module(
            "test",
            [],
            [],
            base_row_sparse={"id": "abc"},
            base_row_populated={"id": "abc", "names": {"primary": ""}},
        )
        assert "BASE_ROW_POPULATED: dict = " in source
        assert "'names'" in source


class TestFieldScenarios:
    def test_required_produces_none_value(self) -> None:
        nodes = [make_check("check_required", _path("country"))]
        source = render_test_module("test", nodes, [])
        assert "Scenario(" in source
        assert "set_at_path('country', None)" in source
        assert "'country'" in source
        assert "'required'" in source

    def test_enum_produces_invalid_string(self) -> None:
        nodes = [
            make_check("check_enum", _path("subtype"), args=(["a", "b", "c"],)),
        ]
        source = render_test_module("test", nodes, [])
        assert "__INVALID__" in source
        assert "'enum'" in source

    def test_bounds_produces_out_of_range(self) -> None:
        nodes = [
            make_check("check_bounds", _path("score"), kwargs=(("ge", 0.0),)),
        ]
        source = render_test_module("test", nodes, [])
        assert "-1" in source or "-1.0" in source
        assert "'bounds'" in source

    def test_bounds_preserves_int_type(self) -> None:
        """Integer bound kwargs emit integer literals for IntegerType fields."""
        nodes = [
            make_check("check_bounds", _path("version"), kwargs=(("ge", 0),)),
        ]
        source = render_test_module("test", nodes, [])
        assert "set_at_path('version', -1)" in source

    def test_bounds_preserves_float_type(self) -> None:
        """Float bound kwargs emit float literals for DoubleType fields."""
        nodes = [
            make_check("check_bounds", _path("height"), kwargs=(("ge", 0.0),)),
        ]
        source = render_test_module("test", nodes, [])
        assert "-1.0" in source

    def test_unknown_constraint_raises(self) -> None:
        nodes = [make_check("check_something_unknown", _path("geom"))]
        with pytest.raises(ValueError, match="Cannot render mutate expression"):
            render_test_module("test", nodes, [])

    def test_pattern_produces_invalid_string(self) -> None:
        nodes = [
            make_check("check_pattern", _path("wikidata.value"), args=(r"^Q\d+$",)),
        ]
        source = render_test_module("test", nodes, [])
        assert "'pattern'" in source

    def test_no_whitespace_pattern_mutation_contains_whitespace(self) -> None:
        """Mutation for NoWhitespaceConstraint must contain whitespace to violate ^\\S+$."""
        nodes = [
            make_check(
                "check_pattern",
                _path("id"),
                args=(r"^\S+$",),
                constraint_type=NoWhitespaceConstraint,
            ),
        ]
        source = render_test_module("test", nodes, [])
        match = re.search(
            r"set_at_path\('id',\s*(.+?)\)",
            source,
            re.DOTALL,
        )
        assert match, f"no id:pattern set_at_path found in:\n{source}"
        mutation_value = match.group(1).strip()
        assert re.search(r"\\s|\s", mutation_value.strip("'")), (
            f"mutation {mutation_value} does not contain whitespace"
        )

    def test_country_code_uses_invalid_value(self) -> None:
        nodes = [
            make_check(
                "check_pattern",
                _path("country.value"),
                constraint_type=CountryCodeAlpha2Constraint,
                label="ISO 3166-1 alpha-2 country code",
                check_name="country_code_alpha2",
            ),
        ]
        source = render_test_module("test", nodes, [])
        assert "'99'" in source

    def test_multiple_descriptors_produce_multiple_entries(self) -> None:
        """A field with required + enum produces two scenario entries."""
        nodes = [
            Check(
                descriptors=(
                    ExpressionDescriptor(function="check_required"),
                    ExpressionDescriptor(function="check_enum", args=(["a"],)),
                ),
                target=_path("subtype"),
            ),
        ]
        source = render_test_module("test", nodes, [])
        assert "'required'" in source
        assert "'enum'" in source

    def test_min_length_produces_empty_list(self) -> None:
        nodes = [
            make_check("check_array_min_length", _path("sources"), args=(1,)),
        ]
        source = render_test_module("test", nodes, [])
        assert "set_at_path('sources', [])" in source
        assert "expected_field='sources_min_length'" in source

    def test_max_length_produces_oversized_list(self) -> None:
        nodes = [
            make_check("check_array_max_length", _path("connectors"), args=(3,)),
        ]
        source = render_test_module("test", nodes, [])
        assert "[{}, {}, {}, {}]" in source or "[{}] * 4" in source
        assert "expected_field='connectors_max_length'" in source

    def test_scenario_id_includes_feature_name(self) -> None:
        nodes = [make_check("check_required", _path("country"))]
        source = render_test_module("division_area", nodes, [])
        assert "division_area::country:required" in source

    def test_scenario_has_scaffold(self) -> None:
        """Scenario includes a scaffold dict (empty when spec is None)."""
        nodes = [make_check("check_required", _path("country"))]
        source = render_test_module("test", nodes, [])
        assert "scaffold={}" in source


class TestModelScenarios:
    def test_radio_group_imports_mutation(self) -> None:
        model_nodes = [
            ModelCheck(
                descriptor=RadioGroup(field_names=("is_land", "is_territorial")),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        assert "mutate_radio_group" in source
        assert "radio_group" in source

    def test_require_any_of_imports_mutation(self) -> None:
        model_nodes = [
            ModelCheck(
                descriptor=RequireAnyOf(field_names=("x", "y")),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        assert "mutate_require_any_of" in source

    def test_require_if_includes_condition(self) -> None:
        model_nodes = [
            ModelCheck(
                descriptor=RequireIf(
                    field_names=("admin_level",),
                    condition=FieldEqCondition("subtype", "country"),
                ),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        assert "mutate_require_if" in source
        assert "'country'" in source

    def test_model_scenario_uses_contains_assertion(self) -> None:
        """Model-level tests use 'in' not '==' to check violation membership."""
        model_nodes = [
            ModelCheck(
                descriptor=RadioGroup(field_names=("a", "b")),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        assert "assert expected in invalid_violations" in source

    def test_renders_valid_python(self) -> None:
        model_nodes = [
            ModelCheck(
                descriptor=RequireIf(
                    field_names=("admin_level",),
                    condition=FieldEqCondition("subtype", "country"),
                ),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        ast.parse(source)

    def test_enum_condition_value_renders_valid_python(self) -> None:
        """Enum condition values must render as their string payload, not repr."""

        class PlaceType(str, Enum):
            COUNTY = "county"

        model_nodes = [
            ModelCheck(
                descriptor=RequireIf(
                    field_names=("admin_level",),
                    condition=FieldEqCondition("subtype", PlaceType.COUNTY),
                ),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        ast.parse(source)
        assert "'county'" in source

    def test_forbid_if_array_field_generates_fill_values(self) -> None:
        """forbid_if targeting an array field emits fill_values with [{}]."""
        model_nodes = [
            ModelCheck(
                descriptor=ForbidIf(
                    field_names=("destinations",),
                    condition=FieldEqCondition("subtype", "road"),
                    field_shapes=(
                        (
                            "destinations",
                            ArrayOf(element=Primitive(base_type="Destination")),
                        ),
                    ),
                ),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        ast.parse(source)
        assert "fill_values" in source
        assert "[{}]" in source

    def test_forbid_if_struct_field_generates_fill_values(self) -> None:
        """forbid_if targeting a struct field emits fill_values with {}."""
        model_nodes = [
            ModelCheck(
                descriptor=ForbidIf(
                    field_names=("road_surface",),
                    condition=FieldEqCondition("subtype", "road"),
                    field_shapes=(
                        ("road_surface", Primitive(base_type="RoadSurface")),
                    ),
                ),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        ast.parse(source)
        assert "fill_values" in source
        assert "'road_surface': {}" in source

    def test_forbid_if_string_field_no_fill_values(self) -> None:
        """forbid_if targeting a string field does not emit fill_values."""
        model_nodes = [
            ModelCheck(
                descriptor=ForbidIf(
                    field_names=("class",),
                    condition=FieldEqCondition("subtype", "water"),
                    field_shapes=(),
                ),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        ast.parse(source)
        assert "fill_values" not in source

    def test_forbid_if_not_condition_uses_negate(self) -> None:
        """forbid_if with Not(FieldEqCondition) passes negate=True to mutation."""
        model_nodes = [
            ModelCheck(
                descriptor=ForbidIf(
                    field_names=("destinations",),
                    condition=Not(FieldEqCondition("subtype", "road")),
                    field_shapes=(),
                ),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        ast.parse(source)
        assert "negate=True" in source
        assert "'road'" in source

    def test_require_any_of_nested_uses_array_path(self) -> None:
        """require_any_of in an array element passes array_path to mutation."""
        model_nodes = [
            ModelCheck(
                descriptor=RequireAnyOf(field_names=("labels", "symbols")),
                target=_array("destinations"),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        ast.parse(source)
        assert 'array_path="destinations"' in source

    def test_require_any_of_nested_with_leaf_path(self) -> None:
        """require_any_of nested in struct within array passes struct_path."""
        model_nodes = [
            ModelCheck(
                descriptor=RequireAnyOf(field_names=("heading", "during")),
                target=_array("access_restrictions", leaf_path=("when",)),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        ast.parse(source)
        assert 'array_path="access_restrictions"' in source
        assert 'struct_path="when"' in source

    def test_require_any_of_top_level_no_array_path(self) -> None:
        """Top-level require_any_of does not emit array_path."""
        model_nodes = [
            ModelCheck(
                descriptor=RequireAnyOf(field_names=("a", "b")),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        assert "array_path" not in source

    def test_require_if_not_condition_uses_negate(self) -> None:
        """require_if with Not(FieldEqCondition) passes negate=True to mutation."""
        model_nodes = [
            ModelCheck(
                descriptor=RequireIf(
                    field_names=("class",),
                    condition=Not(FieldEqCondition("subtype", "road")),
                ),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        ast.parse(source)
        assert "negate=True" in source

    def test_model_scenario_uses_inline_lambda(self) -> None:
        """Model scenarios emit mutate=lambda row: ... directly."""
        model_nodes = [
            ModelCheck(
                descriptor=RadioGroup(field_names=("a", "b")),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        assert "mutate=lambda row:" in source
        assert "mutate_radio_group(" in source

    def test_model_scenario_has_scaffold(self) -> None:
        """Scenario includes a scaffold dict (empty when spec is None)."""
        model_nodes = [
            ModelCheck(
                descriptor=RadioGroup(field_names=("a", "b")),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        assert "Scenario(" in source
        assert "scaffold={}" in source

    def test_min_fields_set_renders_mutation_call(self) -> None:
        """MinFieldsSet dispatches to `mutate_min_fields_set`."""
        model_nodes = [
            ModelCheck(
                descriptor=MinFieldsSet(field_names=("x", "y"), count=1),
            ),
        ]
        source = render_test_module("test", [], model_nodes)
        assert "mutate_min_fields_set(row, ['x', 'y'])" in source
        import_match = re.search(
            r"from \.\._support\.mutations\s+import\s+(.+?)(?:\n\n|\Z)",
            source,
            re.DOTALL,
        )
        assert import_match is not None
        assert "mutate_min_fields_set" in import_match.group(1)

    def test_require_any_of_with_inner_levels_raises(self) -> None:
        """require_any_of does not accept inner_array_path."""
        model_nodes = [
            ModelCheck(
                descriptor=RequireAnyOf(field_names=("a", "b")),
                target=_array("outer", inner_struct_paths=(("inner",),)),
            ),
        ]
        with pytest.raises(ValueError, match="inner_array_path"):
            render_test_module("test", [], model_nodes)

    def test_radio_group_with_array_path_raises(self) -> None:
        """radio_group takes no array kwargs; nodes with column_path raise."""
        model_nodes = [
            ModelCheck(
                descriptor=RadioGroup(field_names=("a", "b")),
                target=_array("outer"),
            ),
        ]
        with pytest.raises(ValueError, match="array_path"):
            render_test_module("test", [], model_nodes)

    def test_require_if_with_leaf_path_raises(self) -> None:
        """require_if does not accept struct_path; nodes with leaf_path raise."""
        model_nodes = [
            ModelCheck(
                descriptor=RequireIf(
                    field_names=("admin_level",),
                    condition=FieldEqCondition("subtype", "country"),
                ),
                target=_array("outer", leaf_path=("when",)),
            ),
        ]
        with pytest.raises(ValueError, match="struct_path"):
            render_test_module("test", [], model_nodes)

    def test_require_if_with_multi_inner_levels_raises(self) -> None:
        """require_if only consumes one inner iteration; multi-level is rejected."""
        model_nodes = [
            ModelCheck(
                descriptor=RequireIf(
                    field_names=("admin_level",),
                    condition=FieldEqCondition("subtype", "country"),
                ),
                target=_array("outer", inner_struct_paths=(("middle",), ("inner",))),
            ),
        ]
        with pytest.raises(ValueError, match="multi-level inner struct paths"):
            render_test_module("test", [], model_nodes)


class TestTestLayer:
    @pytest.fixture(scope="class")
    def empty_source(self) -> str:
        return render_test_module("test", [], [])

    def test_test_scenario_sparse_present(self, empty_source: str) -> None:
        assert "def test_scenario_sparse(" in empty_source

    def test_test_scenario_populated_present(self, empty_source: str) -> None:
        assert "def test_scenario_populated(" in empty_source

    def test_test_baseline_sparse_present(self, empty_source: str) -> None:
        assert "def test_baseline_sparse(" in empty_source

    def test_test_baseline_populated_present(self, empty_source: str) -> None:
        assert "def test_baseline_populated(" in empty_source

    def test_sparse_results_fixture_present(self, empty_source: str) -> None:
        assert "def sparse_results(" in empty_source

    def test_populated_results_fixture_present(self, empty_source: str) -> None:
        assert "def populated_results(" in empty_source

    def test_assert_scenario_helper_present(self, empty_source: str) -> None:
        assert "def _assert_scenario(" in empty_source

    def test_imports_scenario(self, empty_source: str) -> None:
        assert "Scenario" in empty_source

    def test_uses_harness_imports(self, empty_source: str) -> None:
        assert "from .._support.harness import" in empty_source

    def test_imports_set_at_path_only_when_field_scenarios_present(self) -> None:
        # No field checks -> no set_at_path scenarios -> no import
        empty = render_test_module("test", [], [])
        assert "from .._support.helpers import set_at_path" not in empty

        # Field check -> set_at_path used -> import emitted
        with_field = render_test_module(
            "test",
            [make_check("check_required", _path("country"))],
            [],
        )
        assert "from .._support.helpers import set_at_path" in with_field

    def test_scenario_checks_valid_and_invalid(self, empty_source: str) -> None:
        assert "::valid" in empty_source
        assert "::invalid" in empty_source

    def test_scenarios_list_type_annotation(self, empty_source: str) -> None:
        assert "list[Scenario]" in empty_source

    def test_populated_tests_not_marked_skip(self, empty_source: str) -> None:
        assert "pytest.mark.skip" not in empty_source


class TestStructUniqueCheckScenarios:
    @pytest.fixture()
    def sources_unique_output(self) -> str:
        nodes = [make_check("check_struct_unique", _path("sources"))]
        return render_test_module("test", nodes, [])

    def test_struct_unique_emits_scenario(self, sources_unique_output: str) -> None:
        """struct_unique_check produces Scenario with scaffold and inline lambda."""
        assert "Scenario(" in sources_unique_output
        assert "expected_field='sources_unique'" in sources_unique_output
        assert "expected_check='struct_unique'" in sources_unique_output

    def test_struct_unique_imports_mutate_unique_items(
        self, sources_unique_output: str
    ) -> None:
        assert (
            "from .._support.mutations import mutate_unique_items"
            in sources_unique_output
        )

    def test_no_struct_unique_does_not_import_mutate_unique_items(self) -> None:
        nodes = [make_check("check_required", _path("country"))]
        source = render_test_module("test", nodes, [])
        assert "mutate_unique_items" not in source

    def test_struct_unique_inline_lambda(self, sources_unique_output: str) -> None:
        """struct_unique_check emits mutate=lambda row: mutate_unique_items(...)."""
        assert "mutate=lambda row: mutate_unique_items(" in sources_unique_output
        assert "'sources'" in sources_unique_output

    def test_struct_unique_nested_path_strips_suffix(self) -> None:
        """Nested bracket path uses the structural field for mutation."""
        nodes = [
            make_check("check_struct_unique", _path("access_restrictions[].when.mode")),
        ]
        source = render_test_module("test", nodes, [])
        # Black may wrap the long lambda — check parts separately
        assert "mutate_unique_items(" in source
        assert "'access_restrictions[].when.mode'" in source
        assert "expected_field='access_restrictions[].when.mode_unique'" in source

    def test_struct_unique_renders_valid_python(
        self, sources_unique_output: str
    ) -> None:
        ast.parse(sources_unique_output)

    def test_struct_unique_mixed_with_field_scenarios(self) -> None:
        """struct_unique_check alongside normal field checks renders valid Python."""
        nodes = [
            make_check("check_required", _path("sources")),
            make_check("check_struct_unique", _path("sources")),
        ]
        source = render_test_module("test", nodes, [])
        ast.parse(source)
        assert source.count("Scenario(") == 2

    def test_struct_unique_has_scaffold(self, sources_unique_output: str) -> None:
        """struct_unique_check Scenario includes scaffold dict."""
        assert "scaffold={}" in sources_unique_output


class TestArmFiltering:
    """Per-arm test generation filters field checks by discriminator value."""

    def _common_node(self) -> Check:
        return make_check("check_required", _path("id"))

    def _road_node(self) -> Check:
        return make_check(
            "check_required",
            _array("road_surface"),
            guards=(ColumnGuard(discriminator="subtype", values=("road",)),),
        )

    def _rail_node(self) -> Check:
        return make_check(
            "check_required",
            _array("rail_flags"),
            guards=(ColumnGuard(discriminator="subtype", values=("rail",)),),
        )

    def _inner_disc_node(self) -> Check:
        """Road-arm check with in-element discriminator (vehicle dimension)."""
        return make_check(
            "check_required",
            _path("speed_limits[].when.vehicle[].value"),
            guards=(
                ColumnGuard(discriminator="subtype", values=("road",)),
                ElementGuard(discriminator="dimension", values=("height", "length")),
            ),
        )

    def test_arm_road_includes_common_and_road_checks(self) -> None:
        nodes = [self._common_node(), self._road_node(), self._rail_node()]
        source = render_test_module("test", nodes, [], arm="road")
        assert "set_at_path('id'" in source
        assert "road_surface" in source
        assert "rail_flags" not in source

    def test_arm_rail_includes_common_and_rail_checks(self) -> None:
        nodes = [self._common_node(), self._road_node(), self._rail_node()]
        source = render_test_module("test", nodes, [], arm="rail")
        assert "set_at_path('id'" in source
        assert "rail_flags" in source
        assert "road_surface" not in source

    def test_arm_includes_inner_disc_by_outer_variant(self) -> None:
        """In-element discriminator checks emit when the outer Guard matches the arm."""
        nodes = [self._inner_disc_node()]
        source = render_test_module("test", nodes, [], arm="road")
        assert "vehicle" in source

    def test_arm_excludes_inner_disc_wrong_outer(self) -> None:
        nodes = [self._inner_disc_node()]
        source = render_test_module("test", nodes, [], arm="rail")
        assert "vehicle" not in source

    def test_no_arm_includes_all_checks(self) -> None:
        """Without arm filtering, all checks are included."""
        nodes = [self._common_node(), self._road_node(), self._rail_node()]
        source = render_test_module("test", nodes, [])
        assert "set_at_path('id'" in source
        assert "road_surface" in source
        assert "rail_flags" in source

    def test_arm_includes_model_checks(self) -> None:
        """Arm-agnostic ModelChecks (arm=None) reach every arm test."""
        model_nodes = [
            ModelCheck(
                descriptor=ForbidIf(
                    field_names=("rail_flags",),
                    condition=Not(FieldEqCondition("subtype", "rail")),
                    field_shapes=(),
                ),
            ),
        ]
        source = render_test_module("test", [], model_nodes, arm="road")
        assert "mutate_forbid_if" in source

    def test_arm_excludes_other_arms_model_checks(self) -> None:
        """A ModelCheck tagged for one arm does not appear in another arm's tests."""
        road_only = ModelCheck(
            descriptor=RadioGroup(field_names=("road_flag_a", "road_flag_b")),
            arm="road",
        )
        road_source = render_test_module("test", [], [road_only], arm="road")
        assert "mutate_radio_group" in road_source
        rail_source = render_test_module("test", [], [road_only], arm="rail")
        assert "mutate_radio_group" not in rail_source

    def test_arm_renders_valid_python(self) -> None:
        nodes = [self._common_node(), self._road_node(), self._rail_node()]
        source = render_test_module("test", nodes, [], arm="road")
        ast.parse(source)

    def test_arm_filtering_ignores_inner_element_discriminator(self) -> None:
        """Element guards on inner-union discriminators don't gate arm filtering.

        The inner `ElementGuard` discriminator (`dimension`) is unrelated
        to the outer union arm (`subtype`). When an `ElementGuard` value
        happens to coincide with an arm name, an `any(...)` filter would
        wrongly include the check in that arm; the correct filter
        consults only `ColumnGuard`s.
        """
        check = make_check(
            "check_required",
            _path("speed_limits[].when.vehicle[].value"),
            guards=(
                ColumnGuard(discriminator="subtype", values=("road",)),
                # ElementGuard values include "rail" by coincidence -- it's
                # a vehicle dimension, not a segment subtype. Filtering by
                # `any(...)` would let arm="rail" include the check.
                ElementGuard(discriminator="dimension", values=("rail",)),
            ),
        )
        rail = render_test_module("test", [check], [], arm="rail")
        assert "speed_limits" not in rail
        road = render_test_module("test", [check], [], arm="road")
        assert "speed_limits" in road


class TestLinearRangeMutations:
    @pytest.mark.parametrize(
        ("function", "expected_value"),
        [
            ("check_linear_range_length", "[0.5]"),
            ("check_linear_range_bounds", "[1.5, 2.0]"),
            ("check_linear_range_order", "[0.8, 0.2]"),
        ],
    )
    def test_mutation_renders(self, function: str, expected_value: str) -> None:
        nodes = [make_check(function, _path("between"))]
        source = render_test_module("test", nodes, [])
        assert expected_value in source


class TestGeometryTypeMutations:
    def test_point_allowed_emits_linestring(self) -> None:
        """When Point is allowed, inject LineString as the wrong type."""
        nodes = [
            make_check(
                "check_geometry_type",
                _path("geometry"),
                args=(GeometryType.POINT,),
            ),
        ]
        source = render_test_module("test", nodes, [])
        assert "LineString" in source or "LINESTRING" in source

    def test_polygon_allowed_emits_point(self) -> None:
        """When Point is not allowed, inject Point as the wrong type."""
        nodes = [
            make_check(
                "check_geometry_type",
                _path("geometry"),
                args=(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
            ),
        ]
        source = render_test_module("test", nodes, [])
        assert "POINT" in source or "Point" in source

    def test_geometry_type_renders_valid_python(self) -> None:
        nodes = [
            make_check(
                "check_geometry_type",
                _path("geometry"),
                args=(GeometryType.POINT,),
            ),
        ]
        source = render_test_module("test", nodes, [])
        ast.parse(source)

    def test_geometry_type_uses_wkt_strings(self) -> None:
        """Geometry scenarios use WKT strings, not shapely constructor calls."""
        nodes = [
            make_check(
                "check_geometry_type",
                _path("geometry"),
                args=(GeometryType.POINT,),
            ),
        ]
        source = render_test_module("test", nodes, [])
        assert "shapely" not in source
        assert "LINESTRING" in source or "LineString" in source

    def test_all_candidates_allowed_raises(self) -> None:
        """When all geometry candidates are allowed, scenario generation raises."""
        nodes = [
            make_check(
                "check_geometry_type",
                _path("geometry"),
                args=(
                    GeometryType.POINT,
                    GeometryType.LINE_STRING,
                    GeometryType.GEOMETRY_COLLECTION,
                ),
            ),
        ]
        with pytest.raises(ValueError, match="Cannot render mutate expression"):
            render_test_module("test", nodes, [])

    def test_no_geometry_type_no_shapely_imports(self) -> None:
        """Shapely imports are absent when no geometry type scenario exists."""
        nodes = [make_check("check_required", _path("country"))]
        source = render_test_module("test", nodes, [])
        assert "shapely" not in source
