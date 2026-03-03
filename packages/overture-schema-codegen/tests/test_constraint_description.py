"""Tests for constraint description (model-level and field-level)."""

from annotated_types import Ge, Gt, Interval, Le, Lt, MaxLen, MinLen
from overture.schema.codegen.field_constraint_description import (
    constraint_display_text,
    describe_field_constraint,
)
from overture.schema.codegen.model_constraint_description import (
    analyze_model_constraints,
)
from overture.schema.codegen.specs import TypeIdentity
from overture.schema.codegen.type_analyzer import ConstraintSource
from overture.schema.system.model_constraint import (
    FieldEqCondition,
    ForbidIfConstraint,
    MinFieldsSetConstraint,
    ModelConstraint,
    NoExtraFieldsConstraint,
    Not,
    RadioGroupConstraint,
    RequireAnyOfConstraint,
    RequireIfConstraint,
)
from overture.schema.system.primitive import GeometryType, GeometryTypeConstraint
from overture.schema.system.ref import Reference, Relationship
from overture.schema.system.ref.id import Identified


def describe_model_constraints(
    constraints: tuple[ModelConstraint, ...],
) -> list[str]:
    descriptions, _ = analyze_model_constraints(constraints)
    return descriptions


def field_constraint_notes(
    constraints: tuple[ModelConstraint, ...],
) -> dict[str, list[str]]:
    _, field_notes = analyze_model_constraints(constraints)
    return field_notes


class TestDescribeSingleConstraint:
    """Each constraint type produces readable prose."""

    def test_require_any_of(self) -> None:
        constraint = RequireAnyOfConstraint._create_internal(
            "@require_any_of", "name", "description"
        )
        result = describe_model_constraints((constraint,))

        assert result == ["At least one of `name`, `description` must be set"]

    def test_radio_group(self) -> None:
        constraint = RadioGroupConstraint._create_internal(
            "@radio_group", "is_land", "is_territorial"
        )
        result = describe_model_constraints((constraint,))

        assert result == ["Exactly one of `is_land`, `is_territorial` must be `true`"]

    def test_min_fields_set(self) -> None:
        constraint = MinFieldsSetConstraint._create_internal("@min_fields_set", 3)
        result = describe_model_constraints((constraint,))

        assert result == ["At least 3 fields must be set"]

    def test_require_if_field_eq(self) -> None:
        constraint = RequireIfConstraint._create_internal(
            "@require_if", ["admin_level"], FieldEqCondition("subtype", "country")
        )
        result = describe_model_constraints((constraint,))

        assert result == ["`admin_level` is required when `subtype` = `country`"]

    def test_require_if_negated_condition(self) -> None:
        """Not(FieldEqCondition) uses not-equal sign."""
        constraint = RequireIfConstraint._create_internal(
            "@require_if",
            ["parent_division_id"],
            Not(FieldEqCondition("subtype", "country")),
        )
        result = describe_model_constraints((constraint,))

        assert result == ["`parent_division_id` is required when `subtype` ≠ `country`"]

    def test_forbid_if_field_eq(self) -> None:
        constraint = ForbidIfConstraint._create_internal(
            "@forbid_if",
            ["parent_division_id"],
            FieldEqCondition("subtype", "country"),
        )
        result = describe_model_constraints((constraint,))

        assert result == [
            "`parent_division_id` is forbidden when `subtype` = `country`"
        ]

    def test_multi_field_uses_plural_verb(self) -> None:
        """Multiple field names produce 'are required', not 'is required'."""
        constraint = RequireIfConstraint._create_internal(
            "@require_if",
            ["foo", "bar"],
            FieldEqCondition("flag", "on"),
        )
        result = describe_model_constraints((constraint,))

        assert result == ["`foo`, `bar` are required when `flag` = `on`"]


class TestDescribeFiltering:
    """Filtering and fallback behavior."""

    def test_no_extra_fields_filtered_out(self) -> None:
        """@no_extra_fields produces no output."""
        constraint = NoExtraFieldsConstraint._create_internal("@no_extra_fields")
        result = describe_model_constraints((constraint,))

        assert result == []

    def test_unknown_constraint_uses_name_fallback(self) -> None:
        """Unrecognized constraint type falls back to constraint.name."""

        class FutureConstraint(ModelConstraint):
            pass

        constraint = FutureConstraint("@future_thing")
        result = describe_model_constraints((constraint,))

        assert result == ["`@future_thing`"]


class TestConsolidation:
    """Consolidation of same-field conditional constraints."""

    def test_consolidate_require_if_same_field(self) -> None:
        """Multiple @require_if with same fields, different FieldEqCondition values, merge."""
        constraints = tuple(
            RequireIfConstraint._create_internal(
                "@require_if",
                ["admin_level"],
                FieldEqCondition("subtype", val),
            )
            for val in ("country", "dependency", "macroregion")
        )
        result = describe_model_constraints(constraints)

        assert result == [
            "`admin_level` is required when `subtype` is one of: "
            "`country`, `dependency`, `macroregion`"
        ]

    def test_no_consolidation_for_different_fields(self) -> None:
        """@require_if with different field_names are not consolidated."""
        c1 = RequireIfConstraint._create_internal(
            "@require_if", ["foo"], FieldEqCondition("flag", "a")
        )
        c2 = RequireIfConstraint._create_internal(
            "@require_if", ["bar"], FieldEqCondition("flag", "b")
        )
        result = describe_model_constraints((c1, c2))

        assert len(result) == 2

    def test_no_consolidation_for_negated_conditions(self) -> None:
        """Negated conditions are not consolidated."""
        c1 = RequireIfConstraint._create_internal(
            "@require_if", ["foo"], Not(FieldEqCondition("flag", "a"))
        )
        c2 = RequireIfConstraint._create_internal(
            "@require_if", ["foo"], Not(FieldEqCondition("flag", "b"))
        )
        result = describe_model_constraints((c1, c2))

        assert len(result) == 2

    def test_consolidate_forbid_if_same_field(self) -> None:
        """Multiple @forbid_if with same fields also consolidate."""
        constraints = tuple(
            ForbidIfConstraint._create_internal(
                "@forbid_if",
                ["secret"],
                FieldEqCondition("role", val),
            )
            for val in ("guest", "anonymous")
        )
        result = describe_model_constraints(constraints)

        assert result == [
            "`secret` is forbidden when `role` is one of: `guest`, `anonymous`"
        ]


class TestMixedConstraints:
    """End-to-end with mixed constraint types."""

    def test_division_like_model(self) -> None:
        """Mixed constraints render in declaration order with consolidation."""
        constraints = (
            RequireAnyOfConstraint._create_internal("@require_any_of", "foo", "bar"),
            ForbidIfConstraint._create_internal(
                "@forbid_if",
                ["parent_id"],
                FieldEqCondition("subtype", "country"),
            ),
            RequireIfConstraint._create_internal(
                "@require_if",
                ["parent_id"],
                Not(FieldEqCondition("subtype", "country")),
            ),
            RequireIfConstraint._create_internal(
                "@require_if",
                ["level"],
                FieldEqCondition("subtype", "country"),
            ),
            RequireIfConstraint._create_internal(
                "@require_if",
                ["level"],
                FieldEqCondition("subtype", "region"),
            ),
            RadioGroupConstraint._create_internal("@radio_group", "is_land", "is_sea"),
        )
        result = describe_model_constraints(constraints)

        assert result == [
            "At least one of `foo`, `bar` must be set",
            "`parent_id` is forbidden when `subtype` = `country`",
            "`parent_id` is required when `subtype` ≠ `country`",
            "`level` is required when `subtype` is one of: `country`, `region`",
            "Exactly one of `is_land`, `is_sea` must be `true`",
        ]


class TestFieldConstraintNotes:
    """field_constraint_notes maps field names to their constraint descriptions."""

    def test_require_any_of_maps_all_fields(self) -> None:
        """RequireAnyOfConstraint maps each field name to the description."""
        constraint = RequireAnyOfConstraint._create_internal(
            "@require_any_of", "name", "description"
        )
        result = field_constraint_notes((constraint,))

        expected = "At least one of `name`, `description` must be set"
        assert result == {"name": [expected], "description": [expected]}

    def test_require_if_includes_condition_field(self) -> None:
        """RequireIfConstraint includes both constrained and condition fields."""
        constraint = RequireIfConstraint._create_internal(
            "@require_if", ["admin_level"], FieldEqCondition("subtype", "country")
        )
        result = field_constraint_notes((constraint,))

        expected = "`admin_level` is required when `subtype` = `country`"
        assert result["admin_level"] == [expected]
        assert result["subtype"] == [expected]

    def test_forbid_if_with_negated_condition_includes_condition_field(self) -> None:
        """ForbidIfConstraint with Not(FieldEqCondition) includes condition field."""
        constraint = ForbidIfConstraint._create_internal(
            "@forbid_if",
            ["parent_id"],
            Not(FieldEqCondition("subtype", "country")),
        )
        result = field_constraint_notes((constraint,))

        expected = "`parent_id` is forbidden when `subtype` ≠ `country`"
        assert result["parent_id"] == [expected]
        assert result["subtype"] == [expected]

    def test_consolidated_constraints_map_all_fields(self) -> None:
        """Consolidated constraints map to all participating fields."""
        constraints = tuple(
            RequireIfConstraint._create_internal(
                "@require_if",
                ["admin_level"],
                FieldEqCondition("subtype", val),
            )
            for val in ("country", "dependency")
        )
        result = field_constraint_notes(constraints)

        expected = (
            "`admin_level` is required when `subtype` is one of: "
            "`country`, `dependency`"
        )
        assert result["admin_level"] == [expected]
        assert result["subtype"] == [expected]

    def test_no_extra_fields_produces_no_annotations(self) -> None:
        """NoExtraFieldsConstraint produces no field annotations."""
        constraint = NoExtraFieldsConstraint._create_internal("@no_extra_fields")
        result = field_constraint_notes((constraint,))

        assert result == {}

    def test_min_fields_set_produces_no_annotations(self) -> None:
        """MinFieldsSetConstraint produces no field annotations."""
        constraint = MinFieldsSetConstraint._create_internal("@min_fields_set", 3)
        result = field_constraint_notes((constraint,))

        assert result == {}

    def test_radio_group_maps_all_fields(self) -> None:
        """RadioGroupConstraint maps each field name to the description."""
        constraint = RadioGroupConstraint._create_internal(
            "@radio_group", "is_land", "is_sea"
        )
        result = field_constraint_notes((constraint,))

        expected = "Exactly one of `is_land`, `is_sea` must be `true`"
        assert result == {"is_land": [expected], "is_sea": [expected]}

    def test_multiple_constraints_on_one_field(self) -> None:
        """Field appearing in multiple constraints gets all descriptions."""
        c1 = RequireAnyOfConstraint._create_internal(
            "@require_any_of", "name", "description"
        )
        c2 = RequireIfConstraint._create_internal(
            "@require_if", ["name"], FieldEqCondition("subtype", "venue")
        )
        result = field_constraint_notes((c1, c2))

        assert len(result["name"]) == 2


class TestDescribeFieldConstraint:
    """Tests for describe_field_constraint readable output."""

    def test_ge(self) -> None:
        assert describe_field_constraint(Ge(ge=0)) == "`≥ 0`"

    def test_le(self) -> None:
        assert describe_field_constraint(Le(le=100)) == "`≤ 100`"

    def test_gt(self) -> None:
        assert describe_field_constraint(Gt(gt=0)) == "`> 0`"

    def test_lt(self) -> None:
        assert describe_field_constraint(Lt(lt=100)) == "`< 100`"

    def test_min_len(self) -> None:
        assert describe_field_constraint(MinLen(min_length=1)) == "`minimum length: 1`"

    def test_max_len(self) -> None:
        assert (
            describe_field_constraint(MaxLen(max_length=10)) == "`maximum length: 10`"
        )

    def test_interval_closed(self) -> None:
        assert describe_field_constraint(Interval(ge=0, le=100)) == "`0 ≤ x ≤ 100`"

    def test_interval_open(self) -> None:
        assert describe_field_constraint(Interval(gt=0, lt=100)) == "`0 < x < 100`"

    def test_interval_half_open(self) -> None:
        assert describe_field_constraint(Interval(ge=0, lt=100)) == "`0 ≤ x < 100`"

    def test_interval_lower_only(self) -> None:
        assert describe_field_constraint(Interval(ge=0)) == "`≥ 0`"

    def test_interval_upper_only(self) -> None:
        assert describe_field_constraint(Interval(le=100)) == "`≤ 100`"

    def test_geometry_type_single(self) -> None:
        constraint = GeometryTypeConstraint(GeometryType.POINT)
        assert describe_field_constraint(constraint) == "Allowed geometry types: Point"

    def test_geometry_type_multiple(self) -> None:
        constraint = GeometryTypeConstraint(GeometryType.POINT, GeometryType.POLYGON)
        assert (
            describe_field_constraint(constraint)
            == "Allowed geometry types: Point, Polygon"
        )

    def test_geometry_type_all_types(self) -> None:
        constraint = GeometryTypeConstraint(
            GeometryType.POINT,
            GeometryType.LINE_STRING,
            GeometryType.POLYGON,
        )
        assert (
            describe_field_constraint(constraint)
            == "Allowed geometry types: LineString, Point, Polygon"
        )

    def test_reference_belongs_to(self) -> None:
        class Target(Identified):
            pass

        constraint = Reference(Relationship.BELONGS_TO, Target)
        assert (
            describe_field_constraint(constraint) == "References `Target` (belongs to)"
        )

    def test_reference_connects_to(self) -> None:
        class Other(Identified):
            pass

        constraint = Reference(Relationship.CONNECTS_TO, Other)
        assert (
            describe_field_constraint(constraint) == "References `Other` (connects to)"
        )

    def test_reference_link_fn_receives_type_identity(self) -> None:
        """link_fn callback receives TypeIdentity wrapping the relatee class."""

        class Target(Identified):
            pass

        received: list[TypeIdentity] = []

        def link_fn(tid: TypeIdentity) -> str:
            received.append(tid)
            return f"[`{tid.name}`](link)"

        constraint = Reference(Relationship.BELONGS_TO, Target)
        result = describe_field_constraint(constraint, link_fn=link_fn)

        assert len(received) == 1
        assert received[0].obj is Target
        assert received[0].name == "Target"
        assert result == "References [`Target`](link) (belongs to)"

    def test_reference_link_fn_used_in_output(self) -> None:
        """link_fn return value appears verbatim in the description."""

        class Target(Identified):
            pass

        constraint = Reference(Relationship.CONNECTS_TO, Target)
        result = describe_field_constraint(
            constraint, link_fn=lambda tid: f"[`{tid.name}`](path/to/target)"
        )
        assert result == "References [`Target`](path/to/target) (connects to)"


class TestConstraintDisplayText:
    """constraint_display_text forwards link_fn to describe_field_constraint."""

    def test_link_fn_forwarded_to_reference_constraint(self) -> None:
        """link_fn is forwarded when constraint is a Reference."""

        class Target(Identified):
            pass

        constraint = Reference(Relationship.BELONGS_TO, Target)
        cs = ConstraintSource(source_ref=None, source_name=None, constraint=constraint)

        received: list[TypeIdentity] = []

        def link_fn(tid: TypeIdentity) -> str:
            received.append(tid)
            return f"[`{tid.name}`](link)"

        result = constraint_display_text(cs, link_fn=link_fn)

        assert len(received) == 1
        assert received[0].obj is Target
        assert result == "References [`Target`](link) (belongs to)"
