"""Tests for pyspark constraint dispatch."""

import re

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
    forbid_if_field_shapes,
    model_constraint_function,
    normalize_anchor,
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
from pydantic import Field, Strict


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
        assert desc.constraint_type is StrippedConstraint

    def test_json_pointer(self) -> None:
        desc = dispatch_constraint(JsonPointerConstraint())
        assert desc is not None
        assert desc.function == "check_json_pointer"
        assert desc.constraint_type is JsonPointerConstraint

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


class TestRawPydanticPatternDispatch:
    """Raw pydantic `Field(pattern=)` metadata (`_PydanticGeneralMetadata`).

    Distinguished from the schema's `PatternConstraint` by being a
    `PydanticMetadata` marker. Carries the pattern as a `str`
    (`Field(pattern="...")`) or a compiled `re.Pattern`
    (`Field(pattern=re.compile(...))` -- the only flagged-pattern carrier).
    Reaches dispatch via map keys today (e.g. `Sources.license_priority`).
    """

    def test_pydantic_pattern_metadata_dispatches_as_pattern(self) -> None:
        (meta,) = Field(pattern=r"^[a-z]+$").metadata
        desc = dispatch_constraint(meta)
        assert desc is not None
        assert desc.function == "check_pattern"
        assert desc.args == (r"^[a-z]+\z",)  # anchor-normalized

    def test_compiled_pattern_metadata_dispatches_as_pattern(self) -> None:
        # A compiled re.Pattern is the only carrier for a flagged pattern, so
        # `Field(pattern=re.compile(...))` must dispatch like a bare string.
        (meta,) = Field(pattern=re.compile(r"^[a-z]+$")).metadata
        desc = dispatch_constraint(meta)
        assert desc is not None
        assert desc.function == "check_pattern"
        assert desc.args == (r"^[a-z]+\z",)  # anchor-normalized

    def test_compiled_pattern_ignorecase_prepends_inline_flag(self) -> None:
        # re.IGNORECASE has no string-pattern carrier; it maps to Spark's
        # inline (?i) flag (the same idiom check_url_format uses).
        (meta,) = Field(pattern=re.compile(r"^[a-z]+$", re.I)).metadata
        desc = dispatch_constraint(meta)
        assert desc is not None
        assert desc.function == "check_pattern"
        assert desc.args == (r"(?i)^[a-z]+\z",)

    def test_compiled_pattern_unsupported_flag_raises_named(self) -> None:
        # An untranslatable flag must raise a clean, flag-naming error rather
        # than the opaque "Unhandled constraint type" TypeError.
        (meta,) = Field(pattern=re.compile(r"^[a-z]+$", re.M)).metadata
        with pytest.raises(NotImplementedError, match="MULTILINE"):
            dispatch_constraint(meta)

    def test_plain_object_with_str_pattern_still_raises(self) -> None:
        # A non-PydanticMetadata object that merely exposes a string
        # `.pattern` must not be mistaken for raw pattern metadata: the
        # fallback contract stays "raise on unhandled", so an unrelated
        # future constraint can't be silently turned into a check_pattern.
        class _Imposter:
            pattern = r"^[a-z]+$"

        with pytest.raises(TypeError, match="Unhandled constraint type"):
            dispatch_constraint(_Imposter())

    def test_non_pattern_object_still_raises(self) -> None:
        class _Unknown:
            pass

        with pytest.raises(TypeError, match="Unhandled constraint type"):
            dispatch_constraint(_Unknown())


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

    def test_ignorecase_flag_prepends_inline_flag(self) -> None:
        """A case-insensitive PatternConstraint maps re.I to Spark's (?i)."""
        c = PatternConstraint(r"^[a-z]+$", "error: {value}", flags=re.I)
        desc = dispatch_constraint(c)
        assert desc is not None
        assert desc.args == (r"(?i)^[a-z]+\z",)

    def test_unsupported_flag_raises_named(self) -> None:
        """An untranslatable flag raises a clean, flag-naming error."""
        c = PatternConstraint(r"^[a-z]+$", "error: {value}", flags=re.M)
        with pytest.raises(NotImplementedError, match="MULTILINE"):
            dispatch_constraint(c)


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


class TestPatternLabelAcronymHandling:
    def test_acronym_run_in_name_splits_correctly(self) -> None:
        """PatternConstraint subclass with an acronym run labels with spaces."""

        class JSONPathConstraint(PatternConstraint):
            def __init__(self) -> None:
                super().__init__(r"^\$", "Invalid JSON path: {value}")

        desc = dispatch_constraint(JSONPathConstraint())
        assert desc is not None
        assert desc.label == "json path"


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


class TestForbidIfFieldShapes:
    """Non-string scalar shapes must appear in field_shapes."""

    @pytest.mark.parametrize(
        ("base_type", "field_name"),
        [
            ("int32", "count"),
            ("bool", "flag"),
            ("float64", "score"),
        ],
    )
    def test_non_string_scalar_included_in_field_shapes(
        self, base_type: str, field_name: str
    ) -> None:
        shape = Primitive(base_type=base_type)
        result = forbid_if_field_shapes((field_name,), {field_name: shape})
        assert len(result) == 1
        assert result[0][0] == field_name

    def test_string_scalar_excluded_from_field_shapes(self) -> None:
        """String scalars remain excluded; renderer defaults to '' fill."""
        shape = Primitive(base_type="str")
        result = forbid_if_field_shapes(("label",), {"label": shape})
        assert result == ()

    def test_dispatch_model_constraint_forbid_if_int_has_field_shapes(self) -> None:
        condition = FieldEqCondition(field_name="subtype", value="road")
        c = ForbidIfConstraint(field_names=("version",), condition=condition)
        fields = [
            FieldSpec(name="version", shape=Primitive(base_type="int32")),
        ]
        (desc,) = dispatch_model_constraint(c, fields)
        assert isinstance(desc, ForbidIf)
        assert len(desc.field_shapes) == 1
        assert desc.field_shapes[0][0] == "version"


class TestNormalizeAnchorParity:
    """normalize_anchor uses backslash-parity to distinguish anchor from escaped $."""

    def test_bare_dollar_converted(self) -> None:
        assert normalize_anchor(r"foo$") == r"foo\z"

    def test_escaped_dollar_left_unchanged(self) -> None:
        """Single backslash before $ -- literal dollar, must not convert."""
        assert normalize_anchor(r"foo\$") == r"foo\$"

    def test_escaped_backslash_then_anchor_converted(self) -> None:
        """Two backslashes before $ -- even parity, $ is a real anchor, must convert."""
        # "foo\\\\$" is the 6-char string: f o o \ \ $
        # Even number of backslashes (2) before $: the $ is an unescaped anchor.
        result = normalize_anchor("foo\\\\$")
        assert result.endswith(r"\z"), f"Expected \\\\z suffix, got {result!r}"
        assert not result.endswith("$")

    def test_triple_backslash_dollar_left_unchanged(self) -> None:
        r"""Three backslashes before $ -- odd parity, $ is a literal dollar."""
        # "foo\\\\\\$" -- three backslashes + $, odd count: escaped literal $
        result = normalize_anchor("foo\\\\\\$")
        assert result.endswith("$"), f"Expected trailing $, got {result!r}"
