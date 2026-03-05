"""Tests for the validation rule IR models."""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from overture.schema.validation import (
    CheckType,
    Condition,
    DatasetSpec,
    Rule,
    RuleResult,
    Severity,
    ValidationReport,
    ValidationSpec,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BUILDING_YAML = """\
version: "1"

datasets:
  - name: Building
    source_model: overture.schema.buildings.building.Building
    id_column: id
    rules:
      - name: building.id.not_null
        column: id
        check: not_null
        severity: error
        description: "Feature ID is required"

      - name: building.id.min_length
        column: id
        check: min_length
        value: 1
        severity: error
        description: "Feature ID must be at least 1 character"

      - name: building.id.pattern
        column: id
        check: pattern
        value: '^\\S+$'
        severity: error
        description: "Feature ID must not contain whitespace"

      - name: building.id.unique
        column: id
        check: unique
        severity: error
        description: "Feature IDs must be unique across dataset"

      - name: building.version.not_null
        column: version
        check: not_null
        severity: error
        description: "Version is required"

      - name: building.version.gte
        column: version
        check: gte
        value: 0
        severity: error
        description: "Version must be >= 0"

      - name: building.geometry.not_null
        column: geometry
        check: not_null
        severity: error
        description: "Geometry is required"

      - name: building.geometry.type
        column: geometry
        check: geometry_type
        value: [Polygon, MultiPolygon]
        severity: error
        description: "Building geometry must be Polygon or MultiPolygon"

      - name: building.names.primary.min_length
        column: names.primary
        check: min_length
        value: 1
        severity: error
        description: "Primary name must be at least 1 character"
        when:
          column: names
          check: not_null

      - name: building.names.primary.pattern
        column: names.primary
        check: pattern
        value: '^(\\S.*)?\\S$'
        severity: error
        description: "Primary name must not have leading/trailing whitespace"
        when:
          column: names
          check: not_null

      - name: building.cartography.prominence.range
        column: cartography.prominence
        check: between
        value: [1, 100]
        severity: error
        description: "Prominence must be between 1 and 100"

      - name: building.cartography.min_zoom.range
        column: cartography.min_zoom
        check: between
        value: [0, 23]
        severity: error
        description: "Min zoom must be between 0 and 23"

      - name: building.cartography.max_zoom.range
        column: cartography.max_zoom
        check: between
        value: [0, 23]
        severity: error
        description: "Max zoom must be between 0 and 23"

      - name: building.height.positive
        column: height
        check: gt
        value: 0
        severity: error
        description: "Height must be > 0"

      - name: building.num_floors.positive
        column: num_floors
        check: gt
        value: 0
        severity: error
        description: "Number of floors must be > 0"

      - name: building.roof_direction.lower
        column: roof_direction
        check: gte
        value: 0
        severity: error
        description: "Roof direction must be >= 0"

      - name: building.roof_direction.upper
        column: roof_direction
        check: lt
        value: 360
        severity: error
        description: "Roof direction must be < 360"

      - name: building.facade_color.pattern
        column: facade_color
        check: pattern
        value: '^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$'
        severity: error
        description: "Facade color must be a valid hex color code"

      - name: building.roof_shape.valid
        column: roof_shape
        check: in
        value: [dome, flat, gambrel, gabled, half_hipped, hipped, mansard, onion, pyramidal, round, saltbox, sawtooth, skillion, windmill]
        severity: error
        description: "Roof shape must be a valid RoofShape"

      - name: building.is_underground.type
        column: is_underground
        check: is_type
        value: boolean
        severity: error
        description: "is_underground must be a strict boolean"

      - name: building.subtype.valid
        column: subtype
        check: in
        value: [agricultural, civic, commercial, education, entertainment, industrial, medical, military, outbuilding, religious, residential, service, transportation]
        severity: error
        description: "Subtype must be a valid BuildingSubtype"

      - name: building.has_parts.type
        column: has_parts
        check: is_type
        value: boolean
        severity: error
        description: "has_parts must be a strict boolean"
"""


def _make_rule(**kwargs: Any) -> dict[str, Any]:
    """Build a minimal valid rule dict, overriding with kwargs."""
    defaults: dict[str, Any] = {
        "name": "test.rule",
        "column": "col",
        "check": "not_null",
        "severity": "error",
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Round-trip YAML
# ---------------------------------------------------------------------------


def test_yaml_empty_spec_round_trip() -> None:
    spec = ValidationSpec(version="1", datasets=[])
    dumped = yaml.dump(
        spec.model_dump(mode="json"), default_flow_style=False
    )
    loaded = yaml.safe_load(dumped)
    spec2 = ValidationSpec(**loaded)
    assert spec == spec2


def test_yaml_single_rule_round_trip() -> None:
    rule = Rule(
        name="test.not_null",
        column="id",
        check=CheckType.NOT_NULL,
        severity=Severity.ERROR,
        description="ID required",
    )
    spec = ValidationSpec(
        version="1",
        datasets=[
            DatasetSpec(name="Test", id_column="id", rules=[rule])
        ],
    )
    dumped = yaml.dump(
        spec.model_dump(mode="json"), default_flow_style=False
    )
    loaded = yaml.safe_load(dumped)
    spec2 = ValidationSpec(**loaded)
    assert spec2.version == "1"
    assert len(spec2.datasets) == 1
    assert len(spec2.datasets[0].rules) == 1
    assert spec2.datasets[0].rules[0].name == "test.not_null"
    assert spec2.datasets[0].rules[0].check == CheckType.NOT_NULL


def test_yaml_conditional_rule_round_trip() -> None:
    rule = Rule(
        name="test.conditional",
        column="parent_id",
        check=CheckType.NOT_NULL,
        severity=Severity.ERROR,
        when=Condition(column="subtype", check=CheckType.NEQ, value="country"),
    )
    spec = ValidationSpec(
        version="1",
        datasets=[DatasetSpec(name="Test", rules=[rule])],
    )
    dumped = yaml.dump(
        spec.model_dump(mode="json"), default_flow_style=False
    )
    loaded = yaml.safe_load(dumped)
    spec2 = ValidationSpec(**loaded)
    w = spec2.datasets[0].rules[0].when
    assert w is not None
    assert w.column == "subtype"
    assert w.check == CheckType.NEQ
    assert w.value == "country"


# ---------------------------------------------------------------------------
# Building example
# ---------------------------------------------------------------------------


def test_parse_building_yaml() -> None:
    data = yaml.safe_load(BUILDING_YAML)
    spec = ValidationSpec(**data)
    assert spec.version == "1"
    assert len(spec.datasets) == 1

    ds = spec.datasets[0]
    assert ds.name == "Building"
    assert ds.source_model == "overture.schema.buildings.building.Building"
    assert ds.id_column == "id"
    assert len(ds.rules) == 22


def test_building_rules_have_names() -> None:
    data = yaml.safe_load(BUILDING_YAML)
    spec = ValidationSpec(**data)
    names = [r.name for r in spec.datasets[0].rules]
    assert len(names) == len(set(names)), "Rule names must be unique"
    assert all(n.startswith("building.") for n in names)


def test_building_conditional_rules() -> None:
    data = yaml.safe_load(BUILDING_YAML)
    spec = ValidationSpec(**data)
    conditional = [r for r in spec.datasets[0].rules if r.when is not None]
    assert len(conditional) == 2
    for r in conditional:
        assert r.when is not None
        assert r.when.column == "names"
        assert r.when.check == CheckType.NOT_NULL


def test_building_check_types_used() -> None:
    data = yaml.safe_load(BUILDING_YAML)
    spec = ValidationSpec(**data)
    checks_used = {r.check for r in spec.datasets[0].rules}
    expected = {
        CheckType.NOT_NULL,
        CheckType.MIN_LENGTH,
        CheckType.PATTERN,
        CheckType.UNIQUE,
        CheckType.GTE,
        CheckType.GEOMETRY_TYPE,
        CheckType.BETWEEN,
        CheckType.GT,
        CheckType.LT,
        CheckType.IN,
        CheckType.IS_TYPE,
    }
    assert checks_used == expected


# ---------------------------------------------------------------------------
# Structural validation — invalid combinations
# ---------------------------------------------------------------------------


def test_column_and_columns_both_set() -> None:
    """column + columns both set should fail."""
    with pytest.raises(ValidationError):
        Rule(
            name="bad",
            column="a",
            columns=["a", "b"],
            check=CheckType.NOT_NULL,
            severity=Severity.ERROR,
        )


def test_exactly_one_of_with_column_instead_of_columns() -> None:
    with pytest.raises(ValidationError, match="uses 'columns'"):
        Rule(
            name="bad",
            column="a",
            check=CheckType.EXACTLY_ONE_OF,
            severity=Severity.ERROR,
        )


def test_exactly_one_of_with_fewer_than_two_columns() -> None:
    with pytest.raises(ValidationError, match=">= 2 entries"):
        Rule(
            name="bad",
            columns=["a"],
            check=CheckType.EXACTLY_ONE_OF,
            severity=Severity.ERROR,
        )


def test_list_columns_with_min_length() -> None:
    r = Rule(
        name="ok",
        column="col",
        check=CheckType.MIN_LENGTH,
        value=1,
        list_columns=["parent"],
        severity=Severity.ERROR,
    )
    assert r.list_columns == ["parent"]


def test_list_columns_with_max_length() -> None:
    r = Rule(
        name="ok",
        column="col",
        check=CheckType.MAX_LENGTH,
        value=5,
        list_columns=["parent"],
        severity=Severity.ERROR,
    )
    assert r.list_columns == ["parent"]


def test_column_lt_without_other_column() -> None:
    with pytest.raises(ValidationError, match="other_column"):
        Rule(
            name="bad",
            column="a",
            check=CheckType.COLUMN_LT,
            severity=Severity.ERROR,
        )


def test_other_column_on_non_column_check() -> None:
    with pytest.raises(ValidationError, match="other_column"):
        Rule(
            name="bad",
            column="a",
            check=CheckType.GT,
            value=0,
            other_column="b",
            severity=Severity.ERROR,
        )


def test_gt_without_value() -> None:
    with pytest.raises(ValidationError, match="requires a value"):
        Rule(
            name="bad",
            column="a",
            check=CheckType.GT,
            severity=Severity.ERROR,
        )


def test_not_null_with_value() -> None:
    with pytest.raises(ValidationError, match="must not have a value"):
        Rule(
            name="bad",
            column="a",
            check=CheckType.NOT_NULL,
            value=42,
            severity=Severity.ERROR,
        )


def test_no_column_no_columns() -> None:
    with pytest.raises(ValidationError, match="requires 'column'"):
        Rule(
            name="bad",
            check=CheckType.GT,
            value=0,
            severity=Severity.ERROR,
        )


def test_list_columns_on_multi_field_rejected() -> None:
    with pytest.raises(ValidationError, match="list_columns"):
        Rule(
            name="bad",
            columns=["a", "b"],
            check=CheckType.EXACTLY_ONE_OF,
            list_columns=["parent"],
            severity=Severity.ERROR,
        )


def test_list_columns_on_any_of_rejected() -> None:
    with pytest.raises(ValidationError, match="list_columns"):
        Rule(
            name="bad",
            columns=["a", "b"],
            check=CheckType.ANY_OF,
            list_columns=["parent"],
            severity=Severity.ERROR,
        )


# ---------------------------------------------------------------------------
# Valid rule constructions
# ---------------------------------------------------------------------------


def test_not_null_rule() -> None:
    r = Rule(**_make_rule(check="not_null"))
    assert r.check == CheckType.NOT_NULL
    assert r.value is None


def test_gt_rule() -> None:
    r = Rule(**_make_rule(check="gt", value=0))
    assert r.check == CheckType.GT
    assert r.value == 0


def test_between_rule() -> None:
    r = Rule(**_make_rule(check="between", value=[0, 100]))
    assert r.check == CheckType.BETWEEN
    assert r.value == [0, 100]


def test_in_rule() -> None:
    r = Rule(**_make_rule(check="in", value=["a", "b", "c"]))
    assert r.check == CheckType.IN


def test_in_list_columns_rule() -> None:
    r = Rule(**_make_rule(check="in", value=["a", "b"], list_columns=["col"]))
    assert r.list_columns == ["col"]


def test_pattern_list_columns_rule() -> None:
    r = Rule(
        **_make_rule(check="pattern", value="^[A-Z]{2}$", list_columns=["col"])
    )
    assert r.list_columns == ["col"]


def test_column_lt_rule() -> None:
    r = Rule(
        **_make_rule(
            check="column_lt", other_column="b", value=None
        )
    )
    assert r.check == CheckType.COLUMN_LT
    assert r.other_column == "b"


def test_column_lte_rule() -> None:
    r = Rule(
        **_make_rule(check="column_lte", other_column="b", value=None)
    )
    assert r.check == CheckType.COLUMN_LTE


def test_column_eq_rule() -> None:
    r = Rule(
        **_make_rule(check="column_eq", other_column="b", value=None)
    )
    assert r.check == CheckType.COLUMN_EQ


def test_geometry_type_rule() -> None:
    r = Rule(
        **_make_rule(check="geometry_type", value=["Point", "MultiPoint"])
    )
    assert r.check == CheckType.GEOMETRY_TYPE


def test_exactly_one_of_rule() -> None:
    r = Rule(
        name="test.radio",
        columns=["a", "b", "c"],
        check=CheckType.EXACTLY_ONE_OF,
        severity=Severity.ERROR,
    )
    assert r.columns == ["a", "b", "c"]
    assert r.column is None


def test_any_of_rule() -> None:
    r = Rule(
        name="test.any",
        columns=["x", "y"],
        check=CheckType.ANY_OF,
        severity=Severity.ERROR,
    )
    assert r.columns == ["x", "y"]


def test_unique_rule() -> None:
    r = Rule(**_make_rule(check="unique"))
    assert r.check == CheckType.UNIQUE


def test_min_length_rule() -> None:
    r = Rule(**_make_rule(check="min_length", value=1))
    assert r.check == CheckType.MIN_LENGTH


def test_max_length_rule() -> None:
    r = Rule(**_make_rule(check="max_length", value=10))
    assert r.check == CheckType.MAX_LENGTH


def test_is_type_rule() -> None:
    r = Rule(**_make_rule(check="is_type", value="boolean"))
    assert r.check == CheckType.IS_TYPE


def test_rule_with_when() -> None:
    r = Rule(
        **_make_rule(
            check="not_null",
            when={"column": "status", "check": "eq", "value": "active"},
        )
    )
    assert r.when is not None
    assert r.when.check == CheckType.EQ


def test_nested_column_dot_notation() -> None:
    r = Rule(**_make_rule(column="cartography.min_zoom", check="gte", value=0))
    assert r.column == "cartography.min_zoom"


# ---------------------------------------------------------------------------
# Condition validation
# ---------------------------------------------------------------------------


def test_condition_rejects_unique() -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        Condition(column="id", check=CheckType.UNIQUE)


def test_condition_rejects_exactly_one_of() -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        Condition(column="id", check=CheckType.EXACTLY_ONE_OF)


def test_condition_rejects_any_of() -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        Condition(column="id", check=CheckType.ANY_OF)


def test_condition_rejects_column_lt() -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        Condition(column="a", check=CheckType.COLUMN_LT)


def test_condition_rejects_column_lte() -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        Condition(column="a", check=CheckType.COLUMN_LTE)


def test_condition_rejects_column_eq() -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        Condition(column="a", check=CheckType.COLUMN_EQ)


def test_condition_rejects_geometry_type() -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        Condition(column="geom", check=CheckType.GEOMETRY_TYPE)


def test_condition_requires_value_for_eq() -> None:
    with pytest.raises(ValidationError, match="requires a value"):
        Condition(column="a", check=CheckType.EQ)


def test_condition_not_null_no_value() -> None:
    c = Condition(column="a", check=CheckType.NOT_NULL)
    assert c.value is None


def test_condition_in_with_value() -> None:
    c = Condition(column="status", check=CheckType.IN, value=["a", "b"])
    assert c.check == CheckType.IN
    assert c.value == ["a", "b"]


# ---------------------------------------------------------------------------
# Report models
# ---------------------------------------------------------------------------


def test_rule_result() -> None:
    r = RuleResult(
        name="test.check",
        violating_id="id1",
        severity=Severity.ERROR,
    )
    assert r.name == "test.check"
    assert r.violating_id == "id1"


def test_validation_report() -> None:
    report = ValidationReport(
        dataset="Test",
        results=[
            RuleResult(
                name="test.check",
                violating_id="id1",
                severity=Severity.WARNING,
            )
        ],
    )
    assert len(report.results) == 1
    assert report.results[0].severity == Severity.WARNING


def test_report_yaml_round_trip() -> None:
    report = ValidationReport(
        dataset="Building",
        results=[
            RuleResult(
                name="building.id.not_null",
                violating_id="abc",
                severity=Severity.ERROR,
            ),
            RuleResult(
                name="building.id.not_null",
                violating_id="def",
                severity=Severity.ERROR,
            ),
        ],
    )
    dumped = yaml.dump(
        report.model_dump(mode="json"), default_flow_style=False
    )
    loaded = yaml.safe_load(dumped)
    report2 = ValidationReport(**loaded)
    assert report2.dataset == "Building"
    assert len(report2.results) == 2
    assert report2.results[0].name == "building.id.not_null"


# ---------------------------------------------------------------------------
# CheckType and Severity enums
# ---------------------------------------------------------------------------


def test_check_type_count() -> None:
    assert len(CheckType) == 22


def test_severity_values() -> None:
    assert Severity.ERROR.value == "error"
    assert Severity.WARNING.value == "warning"


def test_check_type_string_coercion() -> None:
    r = Rule(**_make_rule(check="gt", value=0))
    assert r.check == CheckType.GT
    assert r.check.value == "gt"
