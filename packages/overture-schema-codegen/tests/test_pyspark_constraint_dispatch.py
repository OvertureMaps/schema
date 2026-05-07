"""Tests for pyspark constraint dispatch."""

import pytest
from annotated_types import Ge, Gt, Interval, Le, Lt
from overture.schema.codegen.extraction.field import Primitive
from overture.schema.codegen.extraction.length_constraints import (
    ArrayMaxLen,
    ArrayMinLen,
    ScalarMaxLen,
    ScalarMinLen,
)
from overture.schema.codegen.extraction.specs import FieldSpec
from overture.schema.codegen.pyspark.constraint_dispatch import (
    ExpressionDescriptor,
    ForbidIf,
    MinFieldsSet,
    RadioGroup,
    RequireAnyOf,
    RequireIf,
    dispatch_base_type,
    dispatch_constraint,
    dispatch_model_constraint,
    dispatch_newtype,
    model_constraint_function,
)
from overture.schema.system.field_constraint.collection import UniqueItemsConstraint
from overture.schema.system.field_constraint.string import (
    CountryCodeAlpha2Constraint,
    JsonPointerConstraint,
    PatternConstraint,
    SnakeCaseConstraint,
    StrippedConstraint,
)
from overture.schema.system.model_constraint import (
    FieldEqCondition,
    ForbidIfConstraint,
    MinFieldsSetConstraint,
    NoExtraFieldsConstraint,
    Not,
    RadioGroupConstraint,
    RequireAnyOfConstraint,
    RequireIfConstraint,
)
from overture.schema.system.primitive import GeometryType, GeometryTypeConstraint
from overture.schema.system.ref import Identified, Reference, Relationship
from pydantic import Strict


class _Stub(Identified):
    pass


class TestBoundsDispatch:
    @pytest.mark.parametrize(
        ("constraint", "expected_kwargs"),
        [
            (Ge(ge=0), (("ge", 0),)),
            (Gt(gt=0), (("gt", 0),)),
            (Le(le=100), (("le", 100),)),
            (Lt(lt=100), (("lt", 100),)),
            (Interval(ge=0, le=1), (("ge", 0), ("le", 1))),
            (Interval(ge=0), (("ge", 0),)),
        ],
    )
    def test_bound_dispatches_to_check_bounds(
        self, constraint: object, expected_kwargs: tuple[tuple[str, object], ...]
    ) -> None:
        desc = dispatch_constraint(constraint)
        assert desc is not None
        assert desc.function == "check_bounds"
        assert desc.kwargs == expected_kwargs

    def test_int_bounds_coerced_to_float_for_float_type(self) -> None:
        """Integer bound values become float when the field is a float type."""
        desc = dispatch_constraint(Ge(ge=0), base_type="float64")
        assert desc is not None
        assert desc.kwargs == (("ge", 0.0),)
        assert isinstance(dict(desc.kwargs)["ge"], float)

    def test_int_bounds_preserved_for_int_type(self) -> None:
        desc = dispatch_constraint(Ge(ge=0), base_type="int32")
        assert desc is not None
        assert desc.kwargs == (("ge", 0),)
        assert isinstance(dict(desc.kwargs)["ge"], int)

    def test_float_bounds_unchanged_for_float_type(self) -> None:
        desc = dispatch_constraint(Ge(ge=0.0), base_type="float64")
        assert desc is not None
        assert desc.kwargs == (("ge", 0.0),)
        assert isinstance(dict(desc.kwargs)["ge"], float)


class TestLengthDispatch:
    def test_min_len_on_array(self) -> None:
        desc = dispatch_constraint(ArrayMinLen(min_length=2))
        assert desc == ExpressionDescriptor(
            function="check_array_min_length", args=(2,)
        )

    def test_min_len_on_scalar(self) -> None:
        desc = dispatch_constraint(ScalarMinLen(min_length=1))
        assert desc == ExpressionDescriptor(
            function="check_string_min_length", args=(1,)
        )

    def test_max_len_on_array(self) -> None:
        desc = dispatch_constraint(ArrayMaxLen(max_length=10))
        assert desc == ExpressionDescriptor(
            function="check_array_max_length", args=(10,)
        )

    def test_max_len_on_scalar(self) -> None:
        desc = dispatch_constraint(ScalarMaxLen(max_length=10))
        assert desc == ExpressionDescriptor(
            function="check_string_max_length", args=(10,)
        )


class TestStringConstraintDispatch:
    def test_stripped(self) -> None:
        desc = dispatch_constraint(StrippedConstraint())
        assert desc is not None
        assert desc.function == "check_stripped"

    def test_json_pointer(self) -> None:
        desc = dispatch_constraint(JsonPointerConstraint())
        assert desc is not None
        assert desc.function == "check_json_pointer"

    def test_pattern_constraint_base(self) -> None:
        c = PatternConstraint(r"^[A-Z]{2}$", "test error")
        desc = dispatch_constraint(c)
        assert desc is not None
        assert desc.function == "check_pattern"
        assert desc.args == (r"^[A-Z]{2}\z",)  # anchor normalized

    def test_country_code_dispatches_as_pattern(self) -> None:
        c = CountryCodeAlpha2Constraint()
        desc = dispatch_constraint(c)
        assert desc is not None
        assert desc.function == "check_pattern"
        assert desc.args == (r"^[A-Z]{2}\z",)  # anchor normalized
        assert desc.label == "ISO 3166-1 alpha-2 country code"
        assert desc.check_name == "country_code_alpha2"

    def test_snake_case_dispatches_as_pattern(self) -> None:
        c = SnakeCaseConstraint()
        desc = dispatch_constraint(c)
        assert desc is not None
        assert desc.function == "check_pattern"
        assert desc.args == (r"^[a-z0-9]+(_[a-z0-9]+)*\z",)  # anchor normalized
        assert desc.label == "Category in snake_case format"
        assert desc.check_name == "snake_case"


class TestPatternConstraintDispatch:
    def test_pattern_constraint_label_fallback_to_docstring(self) -> None:
        """PatternConstraint with no description falls back to docstring, period stripped."""
        c = PatternConstraint(r"^test$", "error: {value}")
        desc = dispatch_constraint(c)
        assert desc is not None
        # Base PatternConstraint has docstring "Generic pattern-based string constraint."
        assert desc.label == "Generic pattern-based string constraint"

    def test_pattern_constraint_check_name_base_class(self) -> None:
        c = PatternConstraint(r"^test$", "error: {value}")
        desc = dispatch_constraint(c)
        assert desc is not None
        assert desc.check_name == "pattern"

    def test_anchor_normalized_dollar_to_backslash_z(self) -> None:
        c = CountryCodeAlpha2Constraint()  # pattern ends with $
        desc = dispatch_constraint(c)
        assert desc is not None
        pattern = str(desc.args[0])
        assert pattern.endswith(r"\z")
        assert not pattern.endswith("$")

    def test_anchor_normalization_replaces_only_trailing_dollar(self) -> None:
        """Dollar signs inside character classes are not end-anchors."""
        c = PatternConstraint(r"^[\$]+$", "error: {value}")
        desc = dispatch_constraint(c)
        assert desc is not None
        pattern = str(desc.args[0])
        # The trailing $ is replaced; the \$ inside the class is preserved
        assert pattern == r"^[\$]+\z"


class TestStructuralConstraintDispatch:
    def test_unique_items(self) -> None:
        desc = dispatch_constraint(UniqueItemsConstraint())
        assert desc is not None
        assert desc.function == "check_struct_unique"

    def test_geometry_type(self) -> None:
        c = GeometryTypeConstraint(GeometryType.POINT)
        desc = dispatch_constraint(c)
        assert desc is not None
        assert desc.function == "check_geometry_type"
        assert GeometryType.POINT in desc.args


class TestSkippedConstraints:
    def test_reference_returns_none(self) -> None:
        r = Reference(Relationship.AGGREGATION, _Stub)
        desc = dispatch_constraint(r)
        assert desc is None

    def test_strict_returns_none(self) -> None:
        desc = dispatch_constraint(Strict())
        assert desc is None


class TestBaseTypeDispatch:
    def test_http_url_dispatches_to_check_url_format_and_length(self) -> None:
        descs = dispatch_base_type("HttpUrl")
        assert descs is not None
        assert len(descs) == 2
        assert descs[0].function == "check_url_format"
        assert descs[1].function == "check_url_length"

    def test_email_str_dispatches_to_check_email(self) -> None:
        descs = dispatch_base_type("EmailStr")
        assert descs is not None
        assert len(descs) == 1
        assert descs[0].function == "check_email"

    def test_bbox_dispatches_to_three_checks(self) -> None:
        descs = dispatch_base_type("BBox")
        assert descs is not None
        assert len(descs) == 3
        assert descs[0].function == "check_bbox_completeness"
        assert descs[1].function == "check_bbox_lat_ordering"
        assert descs[2].function == "check_bbox_lat_range"

    def test_unknown_base_type_returns_none(self) -> None:
        descs = dispatch_base_type("str")
        assert descs is None


class TestNewtypeDispatch:
    def test_linear_range(self) -> None:
        descs = dispatch_newtype("LinearlyReferencedRange")
        assert descs is not None
        assert len(descs) == 3
        assert descs[0].function == "check_linear_range_length"
        assert descs[1].function == "check_linear_range_bounds"
        assert descs[2].function == "check_linear_range_order"

    def test_country_code_alpha2_returns_none(self) -> None:
        descs = dispatch_newtype("CountryCodeAlpha2")
        assert descs is None

    def test_region_code_returns_none(self) -> None:
        descs = dispatch_newtype("RegionCode")
        assert descs is None

    def test_unknown_newtype_returns_none(self) -> None:
        desc = dispatch_newtype("FeatureVersion")
        assert desc is None


class TestUnknownConstraintFails:
    def test_unknown_constraint_raises(self) -> None:
        with pytest.raises(TypeError, match="Unhandled constraint"):
            dispatch_constraint(object())


class TestModelConstraintDispatch:
    def test_require_any_of(self) -> None:
        c = RequireAnyOfConstraint("a", "b")
        (desc,) = dispatch_model_constraint(c, [])
        assert isinstance(desc, RequireAnyOf)
        assert model_constraint_function(desc) == "check_require_any_of"
        assert desc.field_names == ("a", "b")

    def test_radio_group(self) -> None:
        c = RadioGroupConstraint("is_land", "is_territorial")
        (desc,) = dispatch_model_constraint(c, [])
        assert isinstance(desc, RadioGroup)
        assert model_constraint_function(desc) == "check_radio_group"
        assert desc.field_names == ("is_land", "is_territorial")

    def test_require_if(self) -> None:
        c = RequireIfConstraint(
            field_names=("class",),
            condition=FieldEqCondition(field_name="subtype", value="road"),
        )
        (desc,) = dispatch_model_constraint(c, [])
        assert isinstance(desc, RequireIf)
        assert model_constraint_function(desc) == "check_require_if"
        assert desc.field_names == ("class",)
        assert desc.condition is c.condition

    def test_require_if_multi_field_splits(self) -> None:
        """Multi-field `@require_if(["a", "b"], cond)` splits into one descriptor per field.

        Each runtime `check_require_if` call takes a single target
        column, so the descriptor mirrors that: one per field, sharing
        the same condition.
        """
        condition = FieldEqCondition(field_name="subtype", value="road")
        c = RequireIfConstraint(field_names=("a", "b"), condition=condition)
        descs = dispatch_model_constraint(c, [])
        assert len(descs) == 2
        assert all(isinstance(d, RequireIf) for d in descs)
        assert [d.field_names for d in descs] == [("a",), ("b",)]
        assert all(d.condition is condition for d in descs)  # type: ignore[union-attr]

    def test_forbid_if(self) -> None:
        c = ForbidIfConstraint(
            field_names=("class",),
            condition=FieldEqCondition(field_name="subtype", value="water"),
        )
        (desc,) = dispatch_model_constraint(c, [])
        assert isinstance(desc, ForbidIf)
        assert model_constraint_function(desc) == "check_forbid_if"
        assert desc.field_names == ("class",)
        assert desc.field_shapes == ()

    def test_forbid_if_negated(self) -> None:
        c = ForbidIfConstraint(
            field_names=("parent_division_id",),
            condition=Not(FieldEqCondition(field_name="subtype", value="country")),
        )
        (desc,) = dispatch_model_constraint(c, [])
        assert isinstance(desc, ForbidIf)
        assert model_constraint_function(desc) == "check_forbid_if"
        assert desc.condition is c.condition

    def test_forbid_if_multi_field_splits(self) -> None:
        """Multi-field `@forbid_if` splits into one descriptor per field, each with its own shape."""
        condition = FieldEqCondition(field_name="subtype", value="road")
        c = ForbidIfConstraint(field_names=("a", "b"), condition=condition)
        descs = dispatch_model_constraint(c, [])
        assert len(descs) == 2
        assert all(isinstance(d, ForbidIf) for d in descs)
        assert [d.field_names for d in descs] == [("a",), ("b",)]

    def test_min_fields_set(self) -> None:
        c = MinFieldsSetConstraint(count=1)
        (desc,) = dispatch_model_constraint(c, [])
        assert isinstance(desc, MinFieldsSet)
        assert model_constraint_function(desc) == "check_min_fields_set"
        assert desc.count == 1
        assert desc.field_names == ()

    def test_min_fields_set_enumerates_all_fields(self) -> None:
        """`field_names` holds every field -- required and optional alike.

        Matches Pydantic's `model_fields_set` semantics, where required
        fields are always set by the constructor and contribute to the
        count alongside any explicitly-set optional fields.
        """
        fields = [
            FieldSpec(name="required_a", shape=Primitive(base_type="str")),
            FieldSpec(
                name="optional_b",
                shape=Primitive(base_type="str"),
                is_required=False,
            ),
            FieldSpec(name="required_c", shape=Primitive(base_type="str")),
            FieldSpec(
                name="optional_d",
                shape=Primitive(base_type="str"),
                is_required=False,
            ),
        ]
        c = MinFieldsSetConstraint(count=1)
        (desc,) = dispatch_model_constraint(c, fields)
        assert isinstance(desc, MinFieldsSet)
        assert desc.field_names == (
            "required_a",
            "optional_b",
            "required_c",
            "optional_d",
        )

    def test_no_extra_fields_skipped(self) -> None:
        c = NoExtraFieldsConstraint()
        assert dispatch_model_constraint(c, []) == ()

    def test_unknown_model_constraint_raises(self) -> None:
        with pytest.raises(TypeError, match="Unhandled model constraint"):
            dispatch_model_constraint(object(), [])
