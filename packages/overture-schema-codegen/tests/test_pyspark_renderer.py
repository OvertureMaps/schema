"""Tests for pyspark feature module renderer."""

import ast
import re
from enum import Enum
from typing import Annotated, Literal, Union

import pytest
from annotated_types import Ge, MinLen
from codegen_test_support import (
    LiteralSubtypeModel,
    RadioModel,
    RequireAnyModel,
    RequireAnyTrueModel,
    TripleNestedArrayModel,
    discover_feature,
    flat_specs_from_discovery,
    spec_for_model,
)
from overture.schema.codegen.extraction.specs import ModelSpec
from overture.schema.codegen.pyspark._render_common import (
    field_check_rows,
    jinja_env,
    model_check_rows,
    schema_const_name,
)
from overture.schema.codegen.pyspark.check_builder import build_checks
from overture.schema.codegen.pyspark.check_ir import (
    Check,
    ColumnGuard,
    ElementGuard,
    ModelCheck,
)
from overture.schema.codegen.pyspark.constraint_dispatch import (
    ExpressionDescriptor,
    FieldEq,
    ForbidIf,
    MinFieldsSet,
    RadioGroup,
    RequireAnyOf,
    RequireIf,
    require_field_eq,
)
from overture.schema.codegen.pyspark.renderer import (
    _render_check_function_context,
    _render_model_constraint_function_context,
    render_model_module,
)
from overture.schema.codegen.pyspark.schema_builder import SchemaField, build_schema
from overture.schema.system.field_path import (
    Direct,
    parse,
)
from overture.schema.system.geometric import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.model_constraint import (
    FieldEqCondition,
    Not,
    forbid_if,
    require_any_of,
    require_if,
)
from overture.schema.system.numeric import int32
from overture.schema.system.string import CountryCodeAlpha2
from pydantic import BaseModel, Field, HttpUrl
from pydantic.fields import FieldInfo

_path = parse


class TestCheckIRReadColumns:
    """IR-derived `read_columns` on `Check` and `ModelCheck`.

    Each variant enumerates top-level row columns from the IR structure
    directly -- no regex over rendered source. `ColumnGuard` discriminators
    are included (they produce `F.col(...)` at the row level); `ElementGuard`
    discriminators are not (they reference `el[...]`, an element-relative
    accessor).
    """

    def test_scalar_field_read_columns(self) -> None:
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("speed"),
        )
        assert check.read_columns == frozenset({"speed"})

    def test_struct_dotted_scalar_strips_to_top_level(self) -> None:
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_bounds"),),
            target=_path("bbox.xmin"),
        )
        assert check.read_columns == frozenset({"bbox"})

    def test_array_field_read_columns(self) -> None:
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("sources[]"),
        )
        assert check.read_columns == frozenset({"sources"})

    def test_dotted_array_strips_to_top_level(self) -> None:
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("names.rules[]"),
        )
        assert check.read_columns == frozenset({"names"})

    def test_map_field_read_columns(self) -> None:
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_stripped"),),
            target=_path("names.common{value}"),
        )
        assert check.read_columns == frozenset({"names"})

    def test_column_guard_discriminator_included(self) -> None:
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("class"),
            guards=(ColumnGuard(discriminator="subtype", values=("road",)),),
        )
        assert check.read_columns == frozenset({"class", "subtype"})

    def test_element_guard_discriminator_excluded(self) -> None:
        # ElementGuard discriminators reference `el["subtype"]`, not F.col --
        # they are element-relative and do not constitute a top-level row read.
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("items[].value"),
            guards=(ElementGuard(discriminator="subtype", values=("road",)),),
        )
        assert check.read_columns == frozenset({"items"})

    def test_model_check_require_any_of_reads_all_field_names(self) -> None:
        check = ModelCheck(
            descriptor=RequireAnyOf(field_names=("x", "y", "z")),
        )
        assert check.read_columns == frozenset({"x", "y", "z"})

    def test_model_check_require_if_includes_condition_field(self) -> None:
        check = ModelCheck(
            descriptor=RequireIf(
                field_names=("admin_level",),
                condition=FieldEqCondition("subtype", "county"),
            ),
        )
        assert check.read_columns == frozenset({"admin_level", "subtype"})

    def test_model_check_negated_condition_field_included(self) -> None:
        check = ModelCheck(
            descriptor=RequireIf(
                field_names=("admin_level",),
                condition=Not(FieldEqCondition("subtype", "county")),
            ),
        )
        assert check.read_columns == frozenset({"admin_level", "subtype"})

    def test_model_check_array_target_reads_only_container_column(self) -> None:
        # When the constrained model is inside an array, field references use
        # element-relative el["x"] accessors (not F.col("x")), so only the outer
        # array column is a top-level row read.
        check = ModelCheck(
            descriptor=RequireAnyOf(field_names=("x", "y")),
            target=_path("items[]"),
        )
        assert check.read_columns == frozenset({"items"})

    def test_scalar_target_gate_column_included(self) -> None:
        # A descriptor gate on a scalar target renders as F.col("{gate}").isNotNull(),
        # a row-level read; the gate's top-level column must appear in read_columns.
        check = Check(
            descriptors=(
                ExpressionDescriptor(function="check_required", gate=_path("parent")),
            ),
            target=_path("parent.value"),
        )
        assert check.read_columns == frozenset({"parent"})

    def test_array_target_gate_column_excluded(self) -> None:
        # A descriptor gate on an array target is applied element-relatively via
        # element_relative_gate (el[...]), not as F.col -- excluded from read_columns.
        check = Check(
            descriptors=(
                ExpressionDescriptor(function="check_required", gate=_path("items[]")),
            ),
            target=_path("items[].value"),
        )
        assert check.read_columns == frozenset({"items"})

    def test_model_check_require_if_array_target_excludes_condition_field(self) -> None:
        # On an array target, the condition is el["cond"] (element-relative), not
        # F.col("cond"); only the outer array column is a row-level read.
        check = ModelCheck(
            descriptor=RequireIf(
                field_names=("x",),
                condition=FieldEqCondition("cond", "v"),
            ),
            target=_path("items[]"),
        )
        assert check.read_columns == frozenset({"items"})

    def test_model_check_forbid_if_array_target_excludes_condition_field(self) -> None:
        check = ModelCheck(
            descriptor=ForbidIf(
                field_names=("x",),
                condition=FieldEqCondition("cond", "v"),
                field_shapes=(),
            ),
            target=_path("items[]"),
        )
        assert check.read_columns == frozenset({"items"})

    # RadioGroup and MinFieldsSet share the RequireAnyOf match arm, so all
    # three variants derive read_columns identically.
    @pytest.mark.parametrize(
        "descriptor",
        [
            RequireAnyOf(field_names=("a", "b")),
            RadioGroup(field_names=("a", "b")),
            MinFieldsSet(field_names=("a", "b"), count=1),
        ],
    )
    def test_model_check_row_root_field_names_in_read_columns(
        self, descriptor: RequireAnyOf | RadioGroup | MinFieldsSet
    ) -> None:
        # All three variants carry field_names rendered as F.col(...) at the row root.
        check = ModelCheck(descriptor=descriptor)
        assert check.read_columns == frozenset({"a", "b"})

    def test_model_check_map_target_reads_only_outer_column(self) -> None:
        # A dict[K, Model] value-model constraint targets a map-projection
        # `Iterated`; field references use the projected element variable
        # (v["field"]), not F.col. Only the map column itself is a row-level read.
        check = ModelCheck(
            descriptor=RequireAnyOf(field_names=("label", "value")),
            target=_path("names.common{value}"),
        )
        assert check.read_columns == frozenset({"names"})


# Resurrected as a TEST ORACLE: the regex `read_columns` derivation deleted from
# renderer.py in this refactor. It recognized every top-level column form the
# renderer emits -- `F.col`, the outer `array_check`/`nested_array_check`, and
# `map_keys_check`/`map_values_check` -- by reading the rendered source directly.
_RENDERED_COLUMN_READ = re.compile(
    r'(?:F\.col|(?:nested_)?array_check|map_(?:keys|values)_check)\("([^"]+)"'
)


def _columns_in_rendered_expr(expr: str) -> frozenset[str]:
    """Top-level columns a rendered check expression dereferences (regex oracle)."""
    return frozenset(
        m.group(1).split(".", 1)[0] for m in _RENDERED_COLUMN_READ.finditer(expr)
    )


def _read_columns_mismatches(spec: ModelSpec) -> list[str]:
    """Mismatches between IR `read_columns` and the rendered source, for one spec."""
    field_checks, model_checks = build_checks(spec)
    mismatches: list[str] = []
    for check in field_checks:
        for row in field_check_rows([check]):
            expr = str(_render_check_function_context(row)["expr"])
            rendered = _columns_in_rendered_expr(expr)
            expected = row.check.read_columns
            if rendered != expected:
                mismatches.append(
                    f"{spec.name}.{row.label}: rendered={sorted(rendered)} "
                    f"read_columns={sorted(expected)} expr={expr}"
                )
    for model_row in model_check_rows(model_checks):
        expr = str(_render_model_constraint_function_context(model_row)["expr"])
        rendered = _columns_in_rendered_expr(expr)
        expected = model_row.check.read_columns
        if rendered != expected:
            mismatches.append(
                f"{spec.name}.{model_row.label} (model): rendered={sorted(rendered)} "
                f"read_columns={sorted(expected)} expr={expr}"
            )
    return mismatches


class TestReadColumnsMatchRenderedSource:
    """IR-derived `read_columns` equals what the rendered expression dereferences.

    `read_columns` moved from a regex over rendered source to an IR-structural
    derivation, so the two are now independent code paths that must agree:
    `validate_model` drops a check only when none of its `read_columns` are
    present in the input, so a column the rendered `F.col(...)` reads but
    `read_columns` omits would reach Spark unresolved when that column is absent.
    Neither the unit tests nor the regeneration diff catch such a desync (both
    sides derive from the same code). This oracle re-derives the columns from
    rendered source -- ground truth -- and asserts equality across every check
    the real schemas produce, so a future renderer change that emits a new
    column form without updating `read_columns` fails here.
    """

    def test_real_models_read_columns_match_rendered_source(self) -> None:
        specs: list[ModelSpec] = list(flat_specs_from_discovery())
        specs.append(discover_feature("Segment"))
        mismatches: list[str] = []
        for spec in specs:
            mismatches.extend(_read_columns_mismatches(spec))
        assert not mismatches, "read_columns desync:\n" + "\n".join(mismatches)


class TestRequireFieldEq:
    """`require_field_eq` is the strict, raising companion to `parse_field_eq`."""

    def test_unwraps_field_eq(self) -> None:
        assert require_field_eq(FieldEqCondition("subtype", "county")) == FieldEq(
            "subtype", "county", False
        )

    def test_unwraps_negated_field_eq(self) -> None:
        condition = Not(FieldEqCondition("subtype", "county"))
        assert require_field_eq(condition) == FieldEq("subtype", "county", True)

    def test_raises_on_other_condition(self) -> None:
        # A condition `parse_field_eq` cannot unwrap (nested negation) names its
        # type in the error so a new Condition subtype fails loudly in one place.
        condition = Not(Not(FieldEqCondition("subtype", "county")))
        with pytest.raises(TypeError, match="Unhandled condition type: Not"):
            require_field_eq(condition)


class TestSchemaConstName:
    def test_uppercases_model_name(self) -> None:
        assert schema_const_name("address") == "ADDRESS_SCHEMA"

    def test_already_uppercase(self) -> None:
        assert schema_const_name("BUILDING") == "BUILDING_SCHEMA"

    def test_mixed_case(self) -> None:
        assert schema_const_name("myFeature") == "MYFEATURE_SCHEMA"


class BoundsModel(BaseModel):
    score: Annotated[float, Ge(0.0)]


# int32 is a non-float primitive; bounds on it must not emit the NaN guard.
class IntBoundsModel(BaseModel):
    count: Annotated[int32, Ge(0)]


class ArrayModel(BaseModel):
    tags: Annotated[list[str], MinLen(1)]


class InnerModel(BaseModel):
    value: str


class NestedArrayModel(BaseModel):
    items: list[InnerModel] | None = None


# list[Annotated[float, Ge(0.0)]] produces ARRAY-shape nodes because
# check_bounds is an element-level function (not in _COLUMN_LEVEL_FUNCTIONS).
class FloatListModel(BaseModel):
    scores: list[Annotated[float, Ge(0.0)]] | None = None


class MapValueLeaf(BaseModel):
    label: Annotated[str, MinLen(1)]


# dict[K, Model] value model with a constrained field -- the field check
# renders inside a map_values_check lambda navigating into the value struct.
class MapValueFieldModel(BaseModel):
    items: dict[str, MapValueLeaf]


@require_any_of("foo", "bar")
class MapValueAnyOf(BaseModel):
    foo: int | None = None
    bar: str | None = None


# dict[K, Model] value model with a model-level constraint -- the model check
# renders inside a map_values_check lambda.
class MapValueConstraintModel(BaseModel):
    subs: dict[str, MapValueAnyOf]


@require_if(["admin_level"], FieldEqCondition("subtype", "country"))
class LeafRequireIf(BaseModel):
    subtype: str
    admin_level: int | None = None


# The require_if model sits one struct level below the container element, so
# both container types reach it at a non-empty leaf (`...inner`). The target
# AND condition field refs must both navigate that leaf.
class LeafRequireIfOuter(BaseModel):
    inner: LeafRequireIf


class MapValueRequireIfModel(BaseModel):
    subs: dict[str, LeafRequireIfOuter]


class ArrayValueRequireIfModel(BaseModel):
    rows: list[LeafRequireIfOuter]


@forbid_if(["extra"], FieldEqCondition("kind", "basic"))
class MapValueForbidIf(BaseModel):
    kind: str
    extra: str | None = None


class MapValueForbidIfModel(BaseModel):
    subs: dict[str, MapValueForbidIf]


def _render(model_cls: type[BaseModel], name: str = "simple") -> str:
    spec = spec_for_model(model_cls)
    field_checks, model_checks = build_checks(spec)
    schema_fields = build_schema(spec)
    return render_model_module(name, field_checks, model_checks, schema_fields)


def _render_check_function_string(ctx: dict[str, object]) -> str:
    """Render a single check function context to source via the Jinja macro."""
    template = jinja_env().get_template("_check_function.py.jinja2")
    return str(template.module.check_function(c=ctx))  # type: ignore[attr-defined]


def _render_check_function(check: Check, descriptor_idx: int = 0) -> str:
    """Render a per-field check function source from a Check."""
    row = field_check_rows([check])[descriptor_idx]
    ctx = _render_check_function_context(row)
    return _render_check_function_string(ctx)


def _render_node(check: Check) -> str:
    """Render a single Check to its function source."""
    return _render_check_function(check, descriptor_idx=0)


def _render_model_node(check: ModelCheck) -> str:
    """Render a single ModelCheck to its function source."""
    ctx = _render_model_constraint_function_context(model_check_rows([check])[0])
    return _render_check_function_string(ctx)


@pytest.fixture(scope="module")
def literal_subtype_source() -> str:
    """Rendered `LiteralSubtypeModel` source (default `simple` feature name).

    Module-scoped so the extraction+render cost is paid once for all
    consumers in this file.
    """
    return _render(LiteralSubtypeModel)


class TestParseable:
    def test_renders_parseable_python(self, literal_subtype_source: str) -> None:
        ast.parse(literal_subtype_source)

    def test_bounds_model_parseable(self) -> None:
        source = _render(BoundsModel)
        ast.parse(source)

    def test_array_model_parseable(self) -> None:
        source = _render(ArrayModel)
        ast.parse(source)

    def test_nested_array_model_parseable(self) -> None:
        source = _render(NestedArrayModel)
        ast.parse(source)

    def test_radio_model_parseable(self) -> None:
        source = _render(RadioModel, "radio")
        ast.parse(source)

    def test_require_any_model_parseable(self) -> None:
        source = _render(RequireAnyModel, "require_any")
        ast.parse(source)

    def test_depth_3_renders_valid_python(self) -> None:
        source = _render(TripleNestedArrayModel, "triple")
        ast.parse(source)
        assert "nested_array_check(" in source


class TestBoundsNanGuardRendering:
    """The NaN guard flag is emitted only for non-float bound columns."""

    def test_float_bound_omits_check_nan(self) -> None:
        """Float-typed bounds produce a check_bounds call without check_nan."""
        source = _render(BoundsModel)
        start = source.index("check_bounds(")
        call = source[start : source.index(")", start) + 1]
        assert "check_nan" not in call

    def test_integer_bound_emits_check_nan_false(self) -> None:
        """Integer-typed bounds include check_nan=False to skip the dead guard."""
        source = _render(IntBoundsModel)
        assert "check_nan=False" in source


class TestBuilderFunction:
    def test_contains_builder_function(self, literal_subtype_source: str) -> None:
        assert "def simple_checks()" in literal_subtype_source

    def test_builder_returns_list_check(self, literal_subtype_source: str) -> None:
        assert "list[Check]" in literal_subtype_source

    def test_builder_name_uses_model_name(self) -> None:
        source = _render(LiteralSubtypeModel, "my_model")
        assert "def my_model_checks()" in source


class TestSchemaConstant:
    def test_contains_schema_constant(self, literal_subtype_source: str) -> None:
        assert "SIMPLE_SCHEMA" in literal_subtype_source

    def test_schema_constant_name_uppercased(self) -> None:
        source = _render(LiteralSubtypeModel, "my_feature")
        assert "MY_FEATURE_SCHEMA" in source

    def test_contains_struct_type(self, literal_subtype_source: str) -> None:
        assert "StructType" in literal_subtype_source

    def test_contains_struct_field(self, literal_subtype_source: str) -> None:
        assert "StructField" in literal_subtype_source

    def test_shared_struct_ref_emits_struct_field(self) -> None:
        """Shared struct refs (BBOX_STRUCT) render as the type of a StructField."""
        schema_fields = [SchemaField(name="bbox", type_expr="BBOX_STRUCT")]
        source = render_model_module("simple", [], [], schema_fields)
        assert 'StructField("bbox", BBOX_STRUCT, True)' in source


class TestGeometryTypes:
    """`GEOMETRY_TYPES` constant emission for runtime discovery."""

    def test_omitted_when_empty(self, literal_subtype_source: str) -> None:
        assert "GEOMETRY_TYPES" not in literal_subtype_source

    def test_emitted_when_provided(self) -> None:
        spec = spec_for_model(LiteralSubtypeModel)
        field_nodes, model_nodes = build_checks(spec)
        schema_fields = build_schema(spec)
        source = render_model_module(
            "simple",
            field_nodes,
            model_nodes,
            schema_fields,
            geometry_types=(GeometryType.POINT,),
        )
        assert (
            "GEOMETRY_TYPES: tuple[GeometryType, ...] = (GeometryType.POINT,)" in source
        )

    def test_geometry_type_imported_when_only_constant_needs_it(self) -> None:
        # LiteralSubtypeModel has no check_geometry_type constraint, so the
        # import is only required because GEOMETRY_TYPES references it.
        spec = spec_for_model(LiteralSubtypeModel)
        field_nodes, model_nodes = build_checks(spec)
        schema_fields = build_schema(spec)
        source = render_model_module(
            "simple",
            field_nodes,
            model_nodes,
            schema_fields,
            geometry_types=(GeometryType.POINT,),
        )
        assert "from overture.schema.system.geometric import GeometryType" in source


class TestImports:
    def test_imports_pyspark_functions(self, literal_subtype_source: str) -> None:
        assert "from pyspark.sql import functions as F" in literal_subtype_source

    def test_imports_check_classes(self, literal_subtype_source: str) -> None:
        assert (
            "from overture.schema.pyspark.check import Check, CheckShape"
            in literal_subtype_source
        )

    def test_imports_constraint_expressions(self, literal_subtype_source: str) -> None:
        assert (
            "from overture.schema.pyspark.expressions.constraint_expressions import"
            in literal_subtype_source
        )

    def test_imports_schema_types(self, literal_subtype_source: str) -> None:
        # StructType and StructField must appear in the import section (before first def)
        first_def = literal_subtype_source.index("\ndef ")
        import_section = literal_subtype_source[:first_def]
        assert "pyspark.sql.types" in import_section
        assert "StructType" in import_section
        assert "StructField" in import_section

    def test_imports_array_check_when_needed(self) -> None:
        source = _render(FloatListModel, "float_list")
        assert "array_check" in source

    def test_no_unused_column_patterns_import_for_simple(
        self, literal_subtype_source: str
    ) -> None:
        # LiteralSubtypeModel has no array fields -- column_patterns import not needed
        assert "column_patterns" not in literal_subtype_source


class TestPerFieldFunctions:
    def test_per_field_function_exists(self, literal_subtype_source: str) -> None:
        # With split checks, compound fields produce suffixed names
        assert (
            "_subtype_required_check" in literal_subtype_source
            or "_subtype_enum_check" in literal_subtype_source
        )

    def test_check_has_name_field(self, literal_subtype_source: str) -> None:
        """Rendered Check includes name= derived from constraint function."""
        assert "name='required'" in literal_subtype_source
        assert "name='enum'" in literal_subtype_source

    def test_no_field_in_check_calls(self, literal_subtype_source: str) -> None:
        """check_* calls should not include field string as second arg."""
        # Match pattern: check_xxx(F.col("yyy"), "yyy", ...) — field as 2nd arg
        field_arg_pattern = re.compile(r'check_\w+\(F\.col\("[^"]+"\),\s*"[^"]+"')
        assert not field_arg_pattern.search(literal_subtype_source)

    def test_scalar_single_descriptor_no_coalesce(self) -> None:
        class OptionalBounds(BaseModel):
            value: Annotated[float, Ge(0.0)] | None = None

        source = _render(OptionalBounds, "opt")
        assert "check_bounds" in source
        assert "F.coalesce" not in source

    def test_scalar_multi_descriptor_produces_separate_checks(
        self, literal_subtype_source: str
    ) -> None:
        """SimpleModel.subtype has check_required + check_enum -> two separate functions."""
        assert "F.coalesce" not in literal_subtype_source
        assert "name='required'" in literal_subtype_source
        assert "name='enum'" in literal_subtype_source

    def test_compound_checks_split(self, literal_subtype_source: str) -> None:
        """A field with required + enum produces two Check functions, not one coalesced."""
        assert "F.coalesce" not in literal_subtype_source

    def test_array_shape_uses_array_check(self) -> None:
        source = _render(FloatListModel, "float_list")
        assert "array_check" in source

    def test_field_function_name_sanitized(self) -> None:
        # nested field like "items[].value" -> _items_value_check
        source = _render(NestedArrayModel)
        assert "_items_value_check" in source

    def test_builder_collects_all_checks(self, literal_subtype_source: str) -> None:
        # With split checks, both descriptors appear in the builder
        assert "_subtype_required_check()" in literal_subtype_source
        assert "_subtype_enum_check()" in literal_subtype_source


class TestModelConstraintFunctions:
    def test_radio_group_check_rendered(self) -> None:
        source = _render(RadioModel, "radio")
        assert "check_radio_group" in source

    def test_require_any_of_rendered(self) -> None:
        source = _render(RequireAnyModel, "require_any")
        assert "check_require_any_of" in source

    def test_require_any_true_rendered(self) -> None:
        source = _render(RequireAnyTrueModel, "require_any_true")
        assert "check_require_any_true" in source

    def test_require_any_true_lowers_conditions_to_value_equality(self) -> None:
        """Each FieldEqCondition(field, True) lowers to a boolean Column.

        The bool value renders as `F.lit(True)` (not the `True` keyword),
        so ruff's E712 does not rewrite the comparison away.
        """
        source = _render(RequireAnyTrueModel, "require_any_true")
        assert 'F.col("is_land") == F.lit(True)' in source
        assert 'F.col("is_territorial") == F.lit(True)' in source

    def test_require_any_true_reads_condition_columns(self) -> None:
        source = _render(RequireAnyTrueModel, "require_any_true")
        assert "read_columns=frozenset({'is_land', 'is_territorial'})" in source

    def test_radio_group_no_context_arg(self) -> None:
        """check_radio_group must not receive a context string argument."""
        source = _render(RadioModel, "radio")
        # Context arg was the model name, e.g. "RadioModel" — must not appear
        assert "'RadioModel'" not in source

    def test_require_any_of_no_context_arg(self) -> None:
        """check_require_any_of must not receive a context string argument."""
        source = _render(RequireAnyModel, "require_any")
        assert "'RequireAnyModel'" not in source

    def test_require_any_of_emits_read_columns(self) -> None:
        # A model check reads several columns directly; the runtime drops the
        # check when any of them is skipped or structurally absent.
        source = _render(RequireAnyModel, "require_any")
        assert "read_columns=frozenset({'x', 'y'})" in source

    def test_field_check_emits_read_columns(self) -> None:
        # Every check declares the columns it reads, field checks included --
        # there is no separate root_field/referenced_fields split.
        source = _render(BoundsModel)
        assert "read_columns=frozenset({'score'})" in source
        assert "root_field" not in source
        assert "referenced_fields" not in source

    def test_require_if_read_columns_include_condition(self) -> None:
        # require_if reads its target column and the column its condition
        # branches on; both must be carried so skipping either drops the check.
        source = _render(RequireIfEnumModel, "require_if_enum")
        assert "read_columns=frozenset({'admin_level', 'subtype'})" in source

    def test_model_constraint_imports_function(self) -> None:
        source = _render(RadioModel, "radio")
        assert "check_radio_group" in source
        # imported from constraint_expressions
        assert (
            "from overture.schema.pyspark.expressions.constraint_expressions import"
            in source
        )

    def test_model_constraint_included_in_builder(self) -> None:
        source = _render(RadioModel, "radio")
        # some check function for radio_group should appear in builder return
        lines = source.splitlines()
        builder_lines = []
        in_builder = False
        for line in lines:
            if "def radio_checks()" in line:
                in_builder = True
            if in_builder:
                builder_lines.append(line)
        builder_src = "\n".join(builder_lines)
        assert "check" in builder_src.lower()


class TestEnumConstants:
    def test_enum_values_appear_as_list(self, literal_subtype_source: str) -> None:
        for value in ("a", "b", "c"):
            assert f"'{value}'" in literal_subtype_source

    def test_check_enum_called_with_values(self, literal_subtype_source: str) -> None:
        assert "check_enum" in literal_subtype_source


class GeomModel(BaseModel):
    geometry: Annotated[
        Geometry,
        GeometryTypeConstraint(GeometryType.POLYGON, GeometryType.MULTI_POLYGON),
    ]


class TestGeometryTypeRendering:
    def test_geometry_type_renders_valid_python(self) -> None:
        source = _render(GeomModel, "geom")
        ast.parse(source)

    def test_geometry_type_uses_qualified_name(self) -> None:
        source = _render(GeomModel, "geom")
        assert "GeometryType.POLYGON" in source
        assert "GeometryType.MULTI_POLYGON" in source

    def test_geometry_type_import_present(self) -> None:
        source = _render(GeomModel, "geom")
        assert "from overture.schema.system.geometric import GeometryType" in source

    def test_no_geometry_type_import_without_geometry_field(
        self, literal_subtype_source: str
    ) -> None:
        assert "GeometryType" not in literal_subtype_source


class _DeepInner(BaseModel):
    field: str


class _ArrayElementWithNestedStruct(BaseModel):
    nested: _DeepInner


class DeepNestedArrayModel(BaseModel):
    items: list[_ArrayElementWithNestedStruct]


class _ArrayElementWithList(BaseModel):
    countries: list[CountryCodeAlpha2]


class ListInArrayModel(BaseModel):
    items: list[_ArrayElementWithList]


class _ArrayElementWithNewtype(BaseModel):
    country: Annotated[str, Ge(0)]  # stand-in for a constrained field


class TestArrayElementSubfieldRendering:
    """Scalar sub-fields of array elements render as array_check with el[...] accessors."""

    def test_scalar_subfield_uses_array_check(self) -> None:
        source = _render(NestedArrayModel, "nested")
        assert "array_check(" in source

    def test_scalar_subfield_uses_element_accessor(self) -> None:
        source = _render(NestedArrayModel, "nested")
        assert 'el["value"]' in source

    def test_scalar_subfield_no_f_col_with_brackets(self) -> None:
        source = _render(NestedArrayModel, "nested")
        assert 'F.col("items[].value")' not in source

    def test_nested_struct_subfield_chained_brackets(self) -> None:
        source = _render(DeepNestedArrayModel, "deep")
        assert 'el["nested"]["field"]' in source

    def test_nested_struct_subfield_no_dot_in_brackets(self) -> None:
        source = _render(DeepNestedArrayModel, "deep")
        assert 'el["nested.field"]' not in source

    def test_list_subfield_uses_nested_array_check(self) -> None:
        source = _render(ListInArrayModel, "list_in_array")
        assert "nested_array_check(" in source

    def test_list_subfield_has_inner_array_check(self) -> None:
        source = _render(ListInArrayModel, "list_in_array")
        # nested_array_check outer + array_check inner
        assert "nested_array_check(" in source
        assert "array_check(" in source

    def test_list_subfield_parseable(self) -> None:
        source = _render(ListInArrayModel, "list_in_array")
        ast.parse(source)

    def test_deep_nested_parseable(self) -> None:
        source = _render(DeepNestedArrayModel, "deep")
        ast.parse(source)


class TestNoFunctionNameCollisions:
    def test_list_field_produces_unique_function_names(self) -> None:
        source = _render(ArrayModel, "arr")
        # Each "def _" function name should appear exactly once
        func_defs = re.findall(r"^def (_\w+_check)\(", source, re.MULTILINE)
        assert len(func_defs) == len(set(func_defs)), (
            f"Duplicate function names: {func_defs}"
        )

    def test_list_field_renders_parseable(self) -> None:
        source = _render(ArrayModel, "arr")
        ast.parse(source)


class PlaceSubtype(str):
    COUNTRY = "country"
    REGION = "region"

    def __new__(cls, value: str) -> "PlaceSubtype":
        return str.__new__(cls, value)


class _SubtypeEnum(str, Enum):
    COUNTRY = "country"
    REGION = "region"


@require_if(["admin_level"], FieldEqCondition("subtype", _SubtypeEnum.COUNTRY))
class RequireIfEnumModel(BaseModel):
    subtype: str
    admin_level: int | None = None


class TestModelConstraintNoRedundantArgs:
    """Model constraints must not embed context or target_name strings."""

    def test_require_if_no_target_name_arg(self) -> None:
        """check_require_if must not pass the field name as a string arg."""
        source = _render(RequireIfEnumModel, "require_if_enum")
        # Was: check_require_if(F.col("admin_level"), "admin_level", condition, desc)
        # Now:  check_require_if(F.col("admin_level"), condition, desc)
        # Pattern: check_require_if(col_expr, "field_name", ...
        pattern = re.compile(r'check_require_if\([^,]+,\s*"[^"]+",\s*F\.')
        assert not pattern.search(source), (
            "check_require_if still passes field name as string arg"
        )

    def test_forbid_if_no_target_name_arg(self) -> None:
        """check_forbid_if must not pass the field name as a string arg."""
        source = _render(RequireForbidModel, "rf")
        pattern = re.compile(r'check_forbid_if\([^,]+,\s*"[^"]+",\s*F\.')
        assert not pattern.search(source), (
            "check_forbid_if still passes field name as string arg"
        )


class TestEnumValueInCondition:
    def test_renders_valid_python(self) -> None:
        source = _render(RequireIfEnumModel, "require_if_enum")
        ast.parse(source)

    def test_enum_value_rendered_as_string_literal_in_column_expr(self) -> None:
        source = _render(RequireIfEnumModel, "require_if_enum")
        # The column expression (F.col == ...) must use the plain string value,
        # not the non-parseable enum repr <_SubtypeEnum.COUNTRY: 'country'>.
        # The condition description string may still contain the enum repr since
        # it's only displayed in error messages (inside a quoted string literal).
        assert "'country'" in source


class TestConditionDescriptionRendering:
    """Model constraint condition descriptions are human-readable, not Python repr."""

    def test_condition_desc_no_enum_repr(self) -> None:
        source = _render(RequireIfEnumModel, "require_if_enum")
        # The condition_desc string (4th arg to check_require_if) must not contain
        # the non-parseable enum repr like <_SubtypeEnum.COUNTRY: 'country'>
        assert "<_SubtypeEnum" not in source

    def test_condition_desc_uses_field_eq_format(self) -> None:
        source = _render(RequireIfEnumModel, "require_if_enum")
        # Should render as "subtype = 'country'" style (value quoted)
        assert "subtype = 'country'" in source

    def test_condition_desc_with_double_quote_in_value_parseable(self) -> None:
        """Condition values containing double-quotes must produce parseable output."""

        @require_if(["admin_level"], FieldEqCondition("subtype", 'say "hi"'))
        class DoubleQuoteCondModel(BaseModel):
            subtype: str
            admin_level: int | None = None

        source = _render(DoubleQuoteCondModel, "dq_cond")
        ast.parse(source)


@forbid_if(["admin_level"], FieldEqCondition("subtype", "country"))
@require_if(["admin_level"], Not(FieldEqCondition("subtype", "country")))
class RequireForbidModel(BaseModel):
    subtype: str
    admin_level: int | None = None


class TestModelConstraintFieldLabels:
    """require_if/forbid_if field labels: no suffix when unique, per-field counter on collision."""

    def test_require_if_single_constraint_no_suffix(self) -> None:
        source = _render(RequireIfEnumModel, "require_if_enum")
        assert "field='admin_level_required'" in source

    def test_forbid_if_single_constraint_no_suffix(self) -> None:
        source = _render(RequireForbidModel, "rf")
        assert "field='admin_level_forbidden'" in source

    def test_require_and_forbid_have_distinct_labels(self) -> None:
        source = _render(RequireForbidModel, "rf")
        assert "field='admin_level_required'" in source
        assert "field='admin_level_forbidden'" in source

    def test_multiple_require_if_same_target_disambiguated(self) -> None:
        """Multiple require_if on the same target get per-field numeric suffixes."""

        @require_if(["level"], FieldEqCondition("kind", "a"))
        @require_if(["level"], FieldEqCondition("kind", "b"))
        class MultiRequireModel(BaseModel):
            kind: str
            level: int | None = None

        source = _render(MultiRequireModel, "multi_req")
        labels = re.findall(r"field='(level_required[^']*)'", source)
        assert len(labels) >= 2, f"Expected >=2 unique labels, got {labels}"
        assert len(labels) == len(set(labels)), f"Duplicate labels: {labels}"
        assert all(re.search(r"_\d+$", lbl) for lbl in labels), (
            f"Expected numeric suffixes on collision labels: {labels}"
        )


class TestDuplicateFunctionNames:
    def test_column_and_element_level_get_unique_names(self) -> None:
        """division_ids and division_ids[] should produce distinct function names."""
        col_check = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("items"),
        )
        elem_check = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("items[]"),
        )
        source = render_model_module("dup", [col_check, elem_check], [], [])
        ast.parse(source)
        func_defs = re.findall(r"^def (_\w+_check\w*)\(", source, re.MULTILINE)
        assert len(func_defs) == len(set(func_defs)), (
            f"Duplicate function names: {func_defs}"
        )

    def test_same_field_different_variants_get_unique_names(self) -> None:
        """class for road and class for rail should produce distinct function names."""
        road_check = Check(
            descriptors=(
                ExpressionDescriptor(function="check_enum", args=(["a", "b"],)),
            ),
            target=_path("class"),
            guards=(ColumnGuard(discriminator="subtype", values=("road",)),),
        )
        rail_check = Check(
            descriptors=(
                ExpressionDescriptor(function="check_enum", args=(["x", "y"],)),
            ),
            target=_path("class"),
            guards=(ColumnGuard(discriminator="subtype", values=("rail",)),),
        )
        source = render_model_module("dup", [road_check, rail_check], [], [])
        ast.parse(source)
        func_defs = re.findall(r"^def (_\w+_check\w*)\(", source, re.MULTILINE)
        assert len(func_defs) == len(set(func_defs)), (
            f"Duplicate function names: {func_defs}"
        )


class TestFieldCheckLabelCollision:
    """Field checks sharing a `(field, name)` identity get distinct labels.

    The discriminated vehicle-dimension union in `segment` emits two
    field checks with the identical identity
    `("...vehicle[].value", "required")` -- one per arm of the inner
    union. Without a collision suffix the emitted `Check.field` is
    ambiguous (it keys `suppress` matching, `explain_errors` metadata,
    and the conformance test's `expected_field`). Mirror the model-check
    `_N` convention: every member of a colliding group gets a suffix.
    """

    def test_colliding_required_checks_get_distinct_labels(self) -> None:
        first = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("value"),
            guards=(ElementGuard(discriminator="dimension", values=("axle_count",)),),
        )
        second = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("value"),
            guards=(
                ElementGuard(discriminator="dimension", values=("height", "width")),
            ),
        )
        source = render_model_module("collide", [first, second], [], [])
        ast.parse(source)
        labels = re.findall(r"field='(value[^']*)'", source)
        assert labels == ["value_0", "value_1"], labels

    def test_noncolliding_field_check_stays_bare(self) -> None:
        required = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("value"),
        )
        bounds = Check(
            descriptors=(
                ExpressionDescriptor(function="check_bounds", kwargs=(("ge", 0),)),
            ),
            target=_path("value"),
        )
        source = render_model_module("solo", [required, bounds], [], [])
        ast.parse(source)
        labels = re.findall(r"field='(value[^']*)'", source)
        assert labels == ["value", "value"], labels

    def test_multi_descriptor_collision_only_on_shared_name(self) -> None:
        """A multi-descriptor check collides per emitted `(field, name)` row."""
        single = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("value"),
        )
        multi = Check(
            descriptors=(
                ExpressionDescriptor(function="check_required"),
                ExpressionDescriptor(function="check_bounds", kwargs=(("ge", 0),)),
            ),
            target=_path("value"),
        )
        source = render_model_module("multi", [single, multi], [], [])
        ast.parse(source)
        # The two `required` rows collide (-> value_0/value_1); the lone
        # `bounds` row stays bare.
        required_fields = re.findall(
            r"field='(value[^']*)',\n\s+name='required'", source
        )
        bounds_fields = re.findall(r"field='(value[^']*)',\n\s+name='bounds'", source)
        assert required_fields == ["value_0", "value_1"], required_fields
        assert bounds_fields == ["value"], bounds_fields

    def test_labels_are_positional_not_identity_keyed(self) -> None:
        """Row labels align to flattened `(check, desc_idx)` order.

        Collision suffixes depend only on the iteration order both
        renderers share -- never on the identity of the `Check` objects.
        Two value-equal but distinct checks (the cross-arm collision case)
        must still each receive their own collision index.
        """
        first = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("value"),
        )
        second = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("value"),
        )
        # A distinct copy of `first`, equal by value -- under identity
        # keying this would alias `first`; positional keying keeps it
        # separate.
        first_copy = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("value"),
        )
        labels = [row.label for row in field_check_rows([first, second, first_copy])]
        assert labels == ["value_0", "value_1", "value_2"], labels

    def test_arm_unique_check_shares_arm_suffix(self) -> None:
        """A check present in only one arm takes that arm's suffix, not the bare label.

        The axle arm carries an `integer` check the dimension arms lack.
        Keyed on `(field, name)` the lone `integer` row is unique, so it
        would escape suffixing and report the bare `value` beside its
        `value_0` siblings. Grouping by arm keeps the whole axle arm on
        `value_0`.
        """
        axle = (ElementGuard(discriminator="dimension", values=("axle_count",)),)
        dimension = (
            ElementGuard(discriminator="dimension", values=("height", "width")),
        )
        axle_required = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("value"),
            guards=axle,
        )
        axle_multiple_of = Check(
            descriptors=(
                ExpressionDescriptor(function="check_multiple_of", args=(1,)),
            ),
            target=_path("value"),
            guards=axle,
        )
        dimension_required = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("value"),
            guards=dimension,
        )
        rows = field_check_rows([axle_required, axle_multiple_of, dimension_required])
        labeled = {(row.name, row.label) for row in rows}
        assert labeled == {
            ("required", "value_0"),
            ("multiple_of", "value_0"),
            ("required", "value_1"),
        }, labeled


class TestMapProjectionRendering:
    """Map-projection targets render to map_keys_check / map_values_check."""

    def test_map_key_renders_map_keys_check(self) -> None:
        check = Check(
            descriptors=(
                ExpressionDescriptor(
                    function="check_pattern",
                    args=(r"^[a-z]+$",),
                    label="language tag",
                ),
            ),
            target=_path("names{key}"),
        )
        source = render_model_module("dictfeat", [check], [], [])
        ast.parse(source)
        assert 'map_keys_check("names", lambda k: check_pattern(k,' in source

    def test_map_value_renders_map_values_check(self) -> None:
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_stripped"),),
            target=_path("names.common{value}"),
        )
        source = render_model_module("dictfeat", [check], [], [])
        ast.parse(source)
        assert 'map_values_check("names.common", lambda v: check_stripped(v))' in source

    def test_map_check_imports_helper_from_column_patterns(self) -> None:
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_stripped"),),
            target=_path("names{value}"),
        )
        source = render_model_module("dictfeat", [check], [], [])
        assert re.search(
            r"from [.\w]*column_patterns import[\s\S]*?map_values_check", source
        )

    def test_map_check_read_columns_is_top_level_column(self) -> None:
        # The map check dereferences its top-level map column (`names`), not the
        # dotted struct path or the `{value}` step marker; `read_columns` is the
        # granularity at which validate drops the check when the column is absent.
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_stripped"),),
            target=_path("names.common{value}"),
        )
        source = render_model_module("dictfeat", [check], [], [])
        # Renderer emits repr() (single quotes); ruff later normalizes.
        assert "read_columns=frozenset({'names'})" in source


@require_any_of("x", "y")
class _ArrayElementConstrained(BaseModel):
    x: str | None = None
    y: str | None = None


class ArrayOfConstrained(BaseModel):
    items: list[_ArrayElementConstrained]


class TestArrayModelConstraintRendering:
    """Model constraints on array elements render inside array_check."""

    def test_renders_parseable_python(self) -> None:
        source = _render(ArrayOfConstrained, "arr_constrained")
        ast.parse(source)

    def test_renders_array_check(self) -> None:
        source = _render(ArrayOfConstrained, "arr_constrained")
        assert "array_check(" in source

    def test_renders_el_field_refs(self) -> None:
        source = _render(ArrayOfConstrained, "arr_constrained")
        assert 'el["x"]' in source
        assert 'el["y"]' in source

    def test_no_f_col_for_array_element_constraint(self) -> None:
        source = _render(ArrayOfConstrained, "arr_constrained")
        # The array-element model constraint should not use F.col for its field refs
        assert 'F.col("x")' not in source
        assert 'F.col("y")' not in source

    def test_shape_is_array(self) -> None:
        source = _render(ArrayOfConstrained, "arr_constrained")
        assert "CheckShape.ARRAY" in source

    def test_field_label_uses_prefix(self) -> None:
        source = _render(ArrayOfConstrained, "arr_constrained")
        assert "field='items[]" in source

    def test_imports_array_check(self) -> None:
        source = _render(ArrayOfConstrained, "arr_constrained")
        assert "array_check" in source


class TestVariantDiscriminatorField:
    def test_variant_uses_check_discriminator_field(self) -> None:
        """Variant gating should use the Guard's discriminator field, not hardcoded 'subtype'."""
        check = Check(
            descriptors=(
                ExpressionDescriptor(function="check_enum", args=(["x", "y"],)),
            ),
            target=_path("a_field"),
            guards=(ColumnGuard(discriminator="kind", values=("a",)),),
        )
        source = render_model_module("test_variant", [check], [], [])
        ast.parse(source)
        assert 'F.col("kind")' in source
        assert 'F.col("subtype")' not in source


@require_any_of("a", "b")
class _NestedConstrainedStruct(BaseModel):
    a: str | None = None
    b: str | None = None


class _ArrayElementWithNestedConstraint(BaseModel):
    nested: _NestedConstrainedStruct


class ArrayOfNestedConstrained(BaseModel):
    items: list[_ArrayElementWithNestedConstraint]


class TestVariantGatedArrayLambdaScope:
    """Variant gating for ARRAY-shaped nodes must be inside the lambda, not wrapping it."""

    @pytest.fixture(scope="class")
    @classmethod
    def rendered_source(cls) -> str:
        class _Base(BaseModel):
            kind: str

        class _TypeA(_Base):
            kind: Literal["a"] = "a"
            a_field: str

        class _TypeB(_Base):
            kind: Literal["b"] = "b"

        _Union = Annotated[
            Union[_TypeA, _TypeB],  # noqa: UP007
            FieldInfo(discriminator="kind"),
        ]

        class _Wrapper(BaseModel):
            items: list[_Union]

        return _render(_Wrapper, "wrapper")

    def test_parseable(self, rendered_source: str) -> None:
        ast.parse(rendered_source)

    def test_variant_gating_inside_lambda(self, rendered_source: str) -> None:
        """el['kind'] must appear inside the lambda body, not outside array_check."""
        lines = rendered_source.splitlines()
        for i, line in enumerate(lines):
            if "array_check(" in line and i > 0:
                preceding = lines[i - 1].strip()
                assert not preceding.startswith("F.when("), (
                    f"array_check wrapped by F.when at line {i}: {lines[i - 1]!r}"
                )

        lambda_found = False
        el_kind_inside_lambda = False
        for line in lines:
            if "lambda el:" in line:
                lambda_found = True
            if lambda_found and 'el["kind"]' in line:
                el_kind_inside_lambda = True
                break

        assert lambda_found, "No lambda el: found in generated source"
        assert el_kind_inside_lambda, (
            'el["kind"] never appears after lambda el: — variant gating is outside lambda scope'
        )


class TestTopLevelVariantGatedArray:
    """When the array column itself is variant-conditional, discriminator wraps array_check."""

    @pytest.fixture(scope="class")
    @classmethod
    def surface_check(cls) -> Check:
        """ARRAY check with top-level discriminator -- surface only exists for subtype='a'."""
        return Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("surface[]"),
            guards=(ColumnGuard(discriminator="subtype", values=("a",)),),
        )

    @pytest.fixture(scope="class")
    @classmethod
    def surface_value_check(cls) -> Check:
        """ARRAY check with leaf path and top-level discriminator."""
        return Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("surface[].value"),
            guards=(ColumnGuard(discriminator="subtype", values=("a",)),),
        )

    def test_parseable(self, surface_check: Check) -> None:
        source = render_model_module("test", [surface_check], [], [])
        ast.parse(source)

    def test_discriminator_uses_f_col(self, surface_check: Check) -> None:
        """Top-level discriminator must reference F.col, not el[...]."""
        source = render_model_module("test", [surface_check], [], [])
        assert 'F.col("subtype")' in source, (
            "Top-level discriminator must use F.col, not el[...]"
        )
        assert 'el["subtype"]' not in source, (
            'el["subtype"] found -- discriminator placed inside lambda'
        )

    def test_f_when_wraps_array_check(self, surface_check: Check) -> None:
        """F.when must wrap the array_check call, not the lambda body."""
        source = _render_check_function(surface_check)
        # F.when must appear before array_check in the expression.
        f_when_pos = source.find("F.when(")
        array_check_pos = source.find("array_check(")
        assert f_when_pos != -1, "F.when not found in output"
        assert array_check_pos != -1, "array_check not found in output"
        assert f_when_pos < array_check_pos, (
            f"F.when (pos {f_when_pos}) must appear before array_check (pos {array_check_pos})"
        )

    def test_no_el_discriminator_in_lambda(self, surface_value_check: Check) -> None:
        """el['subtype'] must not appear even with leaf path -- subtype is top-level."""
        source = render_model_module("test", [surface_value_check], [], [])
        assert 'el["subtype"]' not in source, (
            'el["subtype"] found -- top-level discriminator must not appear inside lambda'
        )

    def test_leaf_path_check_parseable(self, surface_value_check: Check) -> None:
        source = render_model_module("test", [surface_value_check], [], [])
        ast.parse(source)


class TestNestedStructModelConstraintRendering:
    """Nested struct model constraints inside array elements use chained el accessors."""

    def test_renders_parseable_python(self) -> None:
        source = _render(ArrayOfNestedConstrained, "nested_constrained")
        ast.parse(source)

    def test_chained_struct_accessor(self) -> None:
        source = _render(ArrayOfNestedConstrained, "nested_constrained")
        assert 'el["nested"]["a"]' in source
        assert 'el["nested"]["b"]' in source

    def test_no_direct_el_access(self) -> None:
        """Should NOT produce el["a"] — must go through nested struct."""
        source = _render(ArrayOfNestedConstrained, "nested_constrained")
        # el["a"] without ["nested"] prefix should not appear
        lines = source.split("\n")
        for line in lines:
            if 'el["a"]' in line and '["nested"]' not in line:
                pytest.fail(f'Found bare el["a"] without struct prefix: {line}')


class TestRenderNestedArrayCheckStructure:
    """_render_check_function emits correct nested_array_check / lambda structure."""

    def test_render_nested_array_check(self) -> None:
        check = Check(
            descriptors=(
                ExpressionDescriptor(function="check_bounds", kwargs=(("ge", 0),)),
            ),
            target=_path("items[].things[].value"),
        )
        source = _render_check_function(check)
        assert "nested_array_check" in source
        assert "lambda el" in source
        assert "lambda inner" in source
        assert 'el["things"]' in source
        assert 'check_bounds(inner["value"],' in source

    def test_render_variant_expr_in_nested_array_top_level_disc(self) -> None:
        """Top-level discriminator wraps nested_array_check in F.when(F.col(...))."""
        check = Check(
            descriptors=(
                ExpressionDescriptor(function="check_enum", args=(["m", "km"],)),
            ),
            target=_path("items[].things[].unit"),
            guards=(ColumnGuard(discriminator="kind", values=("a", "b")),),
        )
        source = _render_check_function(check)
        assert "nested_array_check" in source
        assert 'F.col("kind").isin(' in source

    def test_render_variant_expr_in_nested_array_element_disc(self) -> None:
        """Element-level discriminator gates inside the inner lambda."""
        check = Check(
            descriptors=(
                ExpressionDescriptor(function="check_enum", args=(["m", "km"],)),
            ),
            target=_path("items[].things[].unit"),
            guards=(ElementGuard(discriminator="kind", values=("a", "b")),),
        )
        source = _render_check_function(check)
        assert "nested_array_check" in source
        assert 'F.col("kind")' not in source
        assert 'inner["kind"]' in source


class _TagItem(BaseModel):
    tags: dict[str, Annotated[str, Field(min_length=3)]]


class _TagItemList(BaseModel):
    items: list[_TagItem]


class _NestedIntMap(BaseModel):
    subs: dict[str, dict[str, Annotated[int, Field(ge=0)]]]


class TestMapValueUnderContainerRendering:
    """A map value checked under a further container folds a flattening helper
    around `map_values_check`.

    The two mixed nestings -- a map value inside an array element and inside
    another map value -- are the pairings no other renderer test pins;
    `test_column_patterns` runs the same pairings in Spark.
    """

    def test_map_value_inside_array_element(self) -> None:
        field_checks, _ = build_checks(spec_for_model(_TagItemList))
        assert any(str(c.target) == "items[].tags{value}" for c in field_checks)
        source = _render(_TagItemList, "item_list")
        assert "nested_array_check(" in source
        assert "map_values_check(" in source
        assert 'el["tags"]' in source
        assert "check_string_min_length" in source

    def test_map_value_inside_map_value(self) -> None:
        field_checks, _ = build_checks(spec_for_model(_NestedIntMap))
        assert any(str(c.target) == "subs{value}{value}" for c in field_checks)
        source = _render(_NestedIntMap, "map_of_map")
        assert "nested_map_values_check(" in source
        assert "map_values_check(" in source
        assert "check_bounds(" in source


@require_any_of("a", "b")
class _DoubleNestedConstrainedElement(BaseModel):
    a: str | None = None
    b: str | None = None


class _OuterArrayElement(BaseModel):
    things: list[_DoubleNestedConstrainedElement]


class _DoubleNestedModel(BaseModel):
    items: list[_OuterArrayElement]


class TestDoubleNestedArrayModelConstraintRendering:
    """Model constraints on list[] inside another array render nested_array_check."""

    def test_renders_parseable_python(self) -> None:
        source = _render(_DoubleNestedModel, "double_nested")
        ast.parse(source)

    def test_uses_nested_array_check(self) -> None:
        source = _render(_DoubleNestedModel, "double_nested")
        assert "nested_array_check" in source

    def test_inner_lambda_uses_inner_variable(self) -> None:
        source = _render(_DoubleNestedModel, "double_nested")
        assert 'inner["a"]' in source
        assert 'inner["b"]' in source

    def test_outer_lambda_navigates_to_inner_array(self) -> None:
        source = _render(_DoubleNestedModel, "double_nested")
        assert 'el["things"]' in source


class TestMultiLevelNestedArrayRendering:
    """Rendering of deeply nested array checks (2+ inner levels)."""

    def test_two_inner_levels_produces_double_nesting(self) -> None:
        """list[list[list[Struct]]].field -> nested(nested(array_check))."""
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("items[][][].value"),
        )
        source = _render_node(check)
        # Three IterateArrays -> 1 outer nested_array_check + 1 intermediate
        # nested_array_check + 1 innermost array_check = 2 nested_array_check calls.
        assert source.count("nested_array_check(") == 2
        assert "lambda el:" in source
        assert "lambda el2:" in source  # intermediate level
        assert "lambda inner:" in source  # innermost
        assert 'check_required(inner["value"])' in source

    def test_two_inner_levels_with_struct_path(self) -> None:
        """Intermediate level with struct navigation."""
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("outer[].mid[][].leaf"),
        )
        source = _render_node(check)
        assert 'el["mid"]' in source
        assert source.count("nested_array_check(") == 2

    def test_model_constraint_with_two_inner_levels(self) -> None:
        """Model constraint at depth 3 uses double-nested wrapping."""
        check = ModelCheck(
            descriptor=RequireAnyOf(field_names=("a", "b")),
            target=_path("items[][][]"),
        )
        source = _render_model_node(check)
        assert source.count("nested_array_check(") == 2
        assert "lambda el:" in source
        assert "lambda el2:" in source
        assert "array_check(" in source

    def test_variant_gating_only_at_innermost_level(self) -> None:
        """Variant values on a multi-level check with element guard apply at innermost."""
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("items[][][].value"),
            guards=(ElementGuard(discriminator="kind", values=("type_a",)),),
        )
        source = _render_node(check)
        # Variant gating appears at the innermost level.
        assert 'inner["kind"]' in source


class TestGatedScalarRendering:
    """Gated check_required wraps expression in F.when(gate.isNotNull(), ...)."""

    @pytest.fixture
    def gated_check(self) -> Check:
        return Check(
            descriptors=(
                ExpressionDescriptor(function="check_required", gate=_path("inner")),
            ),
            target=_path("inner.value"),
        )

    def test_gated_scalar_has_when_wrapping(self, gated_check: Check) -> None:
        source = _render_node(gated_check)
        assert 'F.col("inner").isNotNull()' in source
        assert "check_required" in source
        assert "F.when(" in source

    def test_gated_scalar_is_parseable(self, gated_check: Check) -> None:
        source = _render_node(gated_check)
        ast.parse(source)

    def test_ungated_scalar_unchanged(self) -> None:
        check = Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("value"),
        )
        source = _render_node(check)
        assert "isNotNull" not in source
        assert "check_required" in source


class _NullableNestedElement(BaseModel):
    value: str


class _ElementWithNullableStruct(BaseModel):
    nested: _NullableNestedElement | None = None


class _ArrayWithNullableStruct(BaseModel):
    items: list[_ElementWithNullableStruct]


class TestGatedFullModelRendering:
    def test_gated_array_descriptor_is_parseable(self) -> None:
        source = _render(_ArrayWithNullableStruct, "arr")
        ast.parse(source)

    def test_gated_array_descriptor_has_element_gate(self) -> None:
        source = _render(_ArrayWithNullableStruct, "arr")
        assert 'el["nested"].isNotNull()' in source
        assert "check_required" in source

    def test_model_with_nullable_parent_is_parseable(self) -> None:
        class Inner(BaseModel):
            value: str

        class Outer(BaseModel):
            inner: Inner | None = None

        source = _render(Outer, "outer")
        ast.parse(source)
        assert "isNotNull" in source
        assert "check_required" in source


class TestGatedArrayRendering:
    """Gated check_required in array context uses element accessor for gate."""

    @pytest.fixture
    def element_gated_check(self) -> Check:
        return Check(
            descriptors=(
                ExpressionDescriptor(
                    function="check_required", gate=_path("items[].nested")
                ),
            ),
            target=_path("items[].nested.mode"),
        )

    def test_gated_array_has_element_gate(self, element_gated_check: Check) -> None:
        source = _render_node(element_gated_check)
        assert 'el["nested"].isNotNull()' in source
        assert "check_required" in source
        assert "F.when(" in source

    def test_gated_array_is_parseable(self, element_gated_check: Check) -> None:
        source = _render_node(element_gated_check)
        ast.parse(source)

    def test_column_level_gate_on_array_target_raises(self) -> None:
        """A column-level gate on an Iterated target is not produced by check_builder."""
        check = Check(
            descriptors=(
                ExpressionDescriptor(
                    function="check_required", gate=_path("perspectives")
                ),
            ),
            target=_path("perspectives.countries[]"),
        )
        with pytest.raises(AssertionError, match="column-level gate"):
            _render_node(check)

    def test_nested_array_gate_applied_at_outermost_lambda(self) -> None:
        """Gate on a nested_array_check wraps the el lambda body, not inner."""
        check = Check(
            descriptors=(
                ExpressionDescriptor(
                    function="check_required", gate=_path("rules[].perspectives")
                ),
            ),
            target=_path("rules[].perspectives.countries[]"),
        )
        source = _render_node(check)
        ast.parse(source)
        assert "nested_array_check(" in source
        # Gate must be on el (the rule struct), not inner (the country string).
        assert 'el["perspectives"].isNotNull()' in source
        assert "inner[" not in source


@require_any_of("a", "b")
class _OptionalSubModel(BaseModel):
    a: str | None = None
    b: str | None = None


class _ElementWithOptional(BaseModel):
    nested: _OptionalSubModel | None = None


class _ArrayWithOptionalSubModel(BaseModel):
    items: list[_ElementWithOptional]


class TestGatedModelConstraintRendering:
    """ModelCheck with gate wraps the constraint in F.when(<accessor>.isNotNull(), ...)."""

    def test_gated_model_check_wraps_in_f_when(self) -> None:
        """A gated ModelCheck on items[].nested emits F.when(el['nested'].isNotNull(), ...)."""
        check = ModelCheck(
            descriptor=RequireAnyOf(field_names=("a", "b")),
            target=_path("items[].nested"),
            gate=_path("items[].nested"),
        )
        source = _render_model_node(check)
        assert 'el["nested"].isNotNull()' in source
        assert "check_require_any_of" in source
        assert "F.when(" in source

    def test_gated_model_check_is_parseable(self) -> None:
        check = ModelCheck(
            descriptor=RequireAnyOf(field_names=("a", "b")),
            target=_path("items[].nested"),
            gate=_path("items[].nested"),
        )
        source = _render_model_node(check)
        ast.parse(source)

    def test_ungated_model_check_no_f_when(self) -> None:
        """A ModelCheck without gate does NOT emit isNotNull wrapping."""
        check = ModelCheck(
            descriptor=RequireAnyOf(field_names=("x", "y")),
            target=_path("items[]"),
            gate=None,
        )
        source = _render_model_node(check)
        assert "isNotNull" not in source
        assert "check_require_any_of" in source

    def test_full_render_optional_sub_model_has_when_guard(self) -> None:
        """End-to-end: rendering _ArrayWithOptionalSubModel emits the isNotNull guard."""
        source = _render(_ArrayWithOptionalSubModel, "arr_optional_sub")
        assert 'el["nested"].isNotNull()' in source

    def test_full_render_optional_sub_model_parseable(self) -> None:
        source = _render(_ArrayWithOptionalSubModel, "arr_optional_sub")
        ast.parse(source)

    def test_gated_model_check_assertion_on_non_array_target(self) -> None:
        """A gate paired with a `Direct` target raises AssertionError."""
        check = ModelCheck(
            descriptor=RequireAnyOf(field_names=("a", "b")),
            target=Direct(),
            gate=_path("items[].nested"),
        )
        with pytest.raises(AssertionError, match="gate.*Direct target"):
            _render_model_node(check)


class TestMapValueModelRendering:
    """Render `dict[K, Model]` value-model checks inside a map lambda.

    The map's values are iterated like an array: a value-model field check
    renders `map_values_check("col", lambda v: check(v["field"]))`, and a
    value-model constraint renders `map_values_check("col", lambda v:
    check_require_any_of([v["a"], v["b"]], ...))`. Both mirror the
    `array_check` rendering of a `list[Model]` element.
    """

    def _field_check(self, model_cls: type[BaseModel], function: str) -> Check:
        field_checks, _ = build_checks(spec_for_model(model_cls))
        for check in field_checks:
            if any(d.function == function for d in check.descriptors):
                return check
        raise AssertionError(f"no field check with {function}")

    def _model_check(self, model_cls: type[BaseModel]) -> ModelCheck:
        _, model_checks = build_checks(spec_for_model(model_cls))
        assert len(model_checks) == 1, model_checks
        return model_checks[0]

    def test_value_field_check_renders_map_values_lambda(self) -> None:
        check = self._field_check(MapValueFieldModel, "check_string_min_length")
        rows = field_check_rows([check])
        sources = [
            _render_check_function_string(_render_check_function_context(row))
            for row in rows
        ]
        assert any(
            'map_values_check("items", lambda v: check_string_min_length(v["label"], 1))'
            in s
            for s in sources
        ), sources

    def test_value_model_constraint_renders_map_values_lambda(self) -> None:
        # Asserts the raw renderer form: field names render via repr (single
        # quotes); ruff normalizes to double quotes downstream.
        check = self._model_check(MapValueConstraintModel)
        source = _render_model_node(check)
        assert (
            'map_values_check("subs", lambda v: '
            "check_require_any_of([v[\"foo\"], v[\"bar\"]], ['foo', 'bar']))"
        ) in source, source

    def test_full_module_parseable_with_map_value_field(self) -> None:
        source = _render(MapValueFieldModel, "map_field")
        ast.parse(source)
        assert "map_values_check(" in source

    def test_full_module_parseable_with_map_value_constraint(self) -> None:
        source = _render(MapValueConstraintModel, "map_con")
        ast.parse(source)
        assert "map_values_check(" in source

    def test_model_constraint_func_name_prefixes_outer_column(self) -> None:
        # Mirrors the array-target naming so distinct map columns yield distinct
        # generated function names rather than colliding on `_<fn>_<idx>`.
        check = self._model_check(MapValueConstraintModel)
        source = _render_model_node(check)
        assert "def _subs_check_require_any_of_0_check()" in source, source

    def test_forbid_if_value_constraint_renders_map_values_lambda(self) -> None:
        check = self._model_check(MapValueForbidIfModel)
        source = _render_model_node(check)
        assert (
            'map_values_check("subs", lambda v: '
            'check_forbid_if(v["extra"], v["kind"] == \'basic\', "kind = \'basic\'"))'
        ) in source, source


class TestLeafQualifiedConditionRef:
    """A require_if/forbid_if condition reached through a non-empty leaf
    keeps the leaf.

    The target field ref and the condition field ref navigate the same
    struct leaf; rendering the condition without the leaf references a
    wrong column (a top-level field of the iterated element instead of the
    nested struct's field). The leaf is non-empty for a constrained model
    reached below an iterated container -- both `list[Model]` and
    `dict[K, Model]`.
    """

    def _require_if_check(self, model_cls: type[BaseModel]) -> ModelCheck:
        _, model_checks = build_checks(spec_for_model(model_cls))
        matches = [c for c in model_checks if isinstance(c.descriptor, RequireIf)]
        assert len(matches) == 1, model_checks
        return matches[0]

    def test_map_value_require_if_condition_keeps_leaf(self) -> None:
        source = _render_model_node(self._require_if_check(MapValueRequireIfModel))
        assert 'v["inner"]["admin_level"]' in source, source
        assert 'v["inner"]["subtype"] ==' in source, source

    def test_array_require_if_condition_keeps_leaf(self) -> None:
        source = _render_model_node(self._require_if_check(ArrayValueRequireIfModel))
        assert 'el["inner"]["admin_level"]' in source, source
        assert 'el["inner"]["subtype"] ==' in source, source


class _UrlOrEmptyRender(BaseModel):
    """Required `HttpUrl | Literal[""]` -- the literal bypasses the URL checks."""

    data_url: HttpUrl | Literal[""]


class TestLiteralAlternativesRendering:
    """A descriptor carrying allow_literals renders an except_literals wrapper."""

    def test_url_checks_wrapped_in_except_literals(self) -> None:
        source = _render(_UrlOrEmptyRender)
        # Both content checks are wrapped; the literal value is threaded in.
        assert 'except_literals(F.col("data_url"), check_url_format(' in source, source
        assert 'except_literals(F.col("data_url"), check_url_length(' in source, source
        # py_literal emits the pre-ruff form (single quotes); ruff normalizes later.
        assert ", ['']" in source, source

    def test_except_literals_imported(self) -> None:
        source = _render(_UrlOrEmptyRender)
        assert "except_literals" in source
        # check_required is not wrapped: it is not threaded with allow_literals.
        assert 'except_literals(F.col("data_url"), check_required(' not in source
