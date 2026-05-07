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
    TripleNestedArrayModel,
    feature_spec_for_model,
)
from overture.schema.codegen.pyspark._render_common import jinja_env
from overture.schema.codegen.pyspark.check_builder import build_checks
from overture.schema.codegen.pyspark.check_ir import (
    Check,
    ColumnGuard,
    ElementGuard,
    ModelCheck,
)
from overture.schema.codegen.pyspark.constraint_dispatch import (
    ExpressionDescriptor,
    RequireAnyOf,
)
from overture.schema.codegen.pyspark.renderer import (
    _render_check_function_context,
    _render_model_constraint_function_context,
    render_feature_module,
)
from overture.schema.codegen.pyspark.schema_builder import build_schema
from overture.schema.system.field_path import (
    parse,
)
from overture.schema.system.model_constraint import (
    FieldEqCondition,
    Not,
    forbid_if,
    require_any_of,
    require_if,
)
from overture.schema.system.primitive import (
    Geometry,
    GeometryType,
    GeometryTypeConstraint,
)
from overture.schema.system.string import CountryCodeAlpha2
from pydantic import BaseModel
from pydantic.fields import FieldInfo

_path = parse


class BoundsModel(BaseModel):
    score: Annotated[float, Ge(0.0)]


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


def _render(model_cls: type[BaseModel], name: str = "simple") -> str:
    spec = feature_spec_for_model(model_cls)
    field_checks, model_checks = build_checks(spec)
    schema_fields = build_schema(spec)
    return render_feature_module(name, field_checks, model_checks, schema_fields)


def _render_check_function_string(ctx: dict[str, object]) -> str:
    """Render a single check function context to source via the Jinja macro."""
    template = jinja_env().get_template("_check_function.py.jinja2")
    return str(template.module.check_function(c=ctx))  # type: ignore[attr-defined]


def _render_check_function(
    check: Check, func_name: str, descriptor_idx: int = 0
) -> str:
    """Render a per-field check function source from a Check."""
    ctx = _render_check_function_context(check, func_name, descriptor_idx)
    return _render_check_function_string(ctx)


def _render_node(check: Check) -> str:
    """Render a single Check to its function source."""
    return _render_check_function(check, "_test_check", descriptor_idx=0)


def _render_model_node(check: ModelCheck) -> str:
    """Render a single ModelCheck to its function source."""
    ctx = _render_model_constraint_function_context(check, 0, "")
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


class TestBuilderFunction:
    def test_contains_builder_function(self, literal_subtype_source: str) -> None:
        assert "def simple_checks()" in literal_subtype_source

    def test_builder_returns_list_check(self, literal_subtype_source: str) -> None:
        assert "list[Check]" in literal_subtype_source

    def test_builder_name_uses_feature_name(self) -> None:
        source = _render(LiteralSubtypeModel, "my_feature")
        assert "def my_feature_checks()" in source


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
        from overture.schema.codegen.pyspark.schema_builder import SchemaField

        schema_fields = [SchemaField(name="bbox", type_expr="BBOX_STRUCT")]
        source = render_feature_module("simple", [], [], schema_fields)
        assert 'StructField("bbox", BBOX_STRUCT, True)' in source


class TestGeometryTypes:
    """`GEOMETRY_TYPES` constant emission for runtime discovery."""

    def test_omitted_when_empty(self, literal_subtype_source: str) -> None:
        assert "GEOMETRY_TYPES" not in literal_subtype_source

    def test_emitted_when_provided(self) -> None:
        spec = feature_spec_for_model(LiteralSubtypeModel)
        field_nodes, model_nodes = build_checks(spec)
        schema_fields = build_schema(spec)
        source = render_feature_module(
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
        spec = feature_spec_for_model(LiteralSubtypeModel)
        field_nodes, model_nodes = build_checks(spec)
        schema_fields = build_schema(spec)
        source = render_feature_module(
            "simple",
            field_nodes,
            model_nodes,
            schema_fields,
            geometry_types=(GeometryType.POINT,),
        )
        assert "from overture.schema.system.primitive import GeometryType" in source


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
        assert 'name="required"' in literal_subtype_source
        assert 'name="enum"' in literal_subtype_source

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
        assert 'name="required"' in literal_subtype_source
        assert 'name="enum"' in literal_subtype_source

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

    def test_radio_group_no_context_arg(self) -> None:
        """check_radio_group must not receive a context string argument."""
        source = _render(RadioModel, "radio")
        # Context arg was the model name, e.g. "RadioModel" — must not appear
        assert "'RadioModel'" not in source

    def test_require_any_of_no_context_arg(self) -> None:
        """check_require_any_of must not receive a context string argument."""
        source = _render(RequireAnyModel, "require_any")
        assert "'RequireAnyModel'" not in source

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
        assert "from overture.schema.system.primitive import GeometryType" in source

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
        assert 'field="admin_level_required"' in source

    def test_forbid_if_single_constraint_no_suffix(self) -> None:
        source = _render(RequireForbidModel, "rf")
        assert 'field="admin_level_forbidden"' in source

    def test_require_and_forbid_have_distinct_labels(self) -> None:
        source = _render(RequireForbidModel, "rf")
        assert 'field="admin_level_required"' in source
        assert 'field="admin_level_forbidden"' in source

    def test_multiple_require_if_same_target_disambiguated(self) -> None:
        """Multiple require_if on the same target get per-field numeric suffixes."""

        @require_if(["level"], FieldEqCondition("kind", "a"))
        @require_if(["level"], FieldEqCondition("kind", "b"))
        class MultiRequireModel(BaseModel):
            kind: str
            level: int | None = None

        source = _render(MultiRequireModel, "multi_req")
        labels = re.findall(r'field="(level_required[^"]*)"', source)
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
        source = render_feature_module("dup", [col_check, elem_check], [], [])
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
        source = render_feature_module("dup", [road_check, rail_check], [], [])
        ast.parse(source)
        func_defs = re.findall(r"^def (_\w+_check\w*)\(", source, re.MULTILINE)
        assert len(func_defs) == len(set(func_defs)), (
            f"Duplicate function names: {func_defs}"
        )


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
        assert 'field="items[]' in source

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
        source = render_feature_module("test_variant", [check], [], [])
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
    def rendered_source(self) -> str:
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
    def surface_check(self) -> Check:
        """ARRAY check with top-level discriminator -- surface only exists for subtype='a'."""
        return Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("surface[]"),
            guards=(ColumnGuard(discriminator="subtype", values=("a",)),),
        )

    @pytest.fixture(scope="class")
    def surface_value_check(self) -> Check:
        """ARRAY check with leaf path and top-level discriminator."""
        return Check(
            descriptors=(ExpressionDescriptor(function="check_required"),),
            target=_path("surface[].value"),
            guards=(ColumnGuard(discriminator="subtype", values=("a",)),),
        )

    def test_parseable(self, surface_check: Check) -> None:
        source = render_feature_module("test", [surface_check], [], [])
        ast.parse(source)

    def test_discriminator_uses_f_col(self, surface_check: Check) -> None:
        """Top-level discriminator must reference F.col, not el[...]."""
        source = render_feature_module("test", [surface_check], [], [])
        assert 'F.col("subtype")' in source, (
            "Top-level discriminator must use F.col, not el[...]"
        )
        assert 'el["subtype"]' not in source, (
            'el["subtype"] found -- discriminator placed inside lambda'
        )

    def test_f_when_wraps_array_check(self, surface_check: Check) -> None:
        """F.when must wrap the array_check call, not the lambda body."""
        source = _render_check_function(surface_check, "_surface_check")
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
        source = render_feature_module("test", [surface_value_check], [], [])
        assert 'el["subtype"]' not in source, (
            'el["subtype"] found -- top-level discriminator must not appear inside lambda'
        )

    def test_leaf_path_check_parseable(self, surface_value_check: Check) -> None:
        source = render_feature_module("test", [surface_value_check], [], [])
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
        source = _render_check_function(check, "_test_check")
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
        source = _render_check_function(check, "_test_check")
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
        source = _render_check_function(check, "_test_check")
        assert "nested_array_check" in source
        assert 'F.col("kind")' not in source
        assert 'inner["kind"]' in source


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
        """A column-level gate on an ArrayPath target is not produced by check_builder."""
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
