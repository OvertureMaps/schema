"""Tests for the validation rule extractor."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, NewType

import pytest
from pydantic import BaseModel, Field

from overture.schema.validation.extract import (
    _collect_constraints,
    _convert_condition,
    _extract_field_rules,
    _extract_model_constraint_rules,
    _get_dataset_name,
    extract,
    extract_all,
)
from overture.schema.validation.ir import (
    CheckType,
    Condition,
    DatasetSpec,
    Rule,
    Severity,
)


# ---------------------------------------------------------------------------
# Test helpers — inline model definitions for unit tests
# ---------------------------------------------------------------------------


class Color(str, Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class InlineNested(BaseModel):
    value: int = Field(ge=0)
    label: str | None = None


class InlineListItem(BaseModel):
    value: Annotated[str, Field(min_length=1)]
    score: int = Field(ge=0)
    tag: Color | None = None


class InlineModel(BaseModel):
    theme: Literal["test"] = "test"
    type: Literal["inline"]
    name: str
    age: int = Field(ge=0, le=150)
    color: Color | None = None
    tags: list[Color] | None = None
    flag: Annotated[bool | None, Field(strict=True)] = None
    nested: InlineNested | None = None
    optional_str: str | None = None
    items: list[InlineListItem] | None = None


# ---------------------------------------------------------------------------
# Dataset name detection
# ---------------------------------------------------------------------------


def test_get_dataset_name_literal_type_field() -> None:
    assert _get_dataset_name(InlineModel) == "inline"


def test_get_dataset_name_fallback_lowercase() -> None:
    class NoTypeField(BaseModel):
        pass

    assert _get_dataset_name(NoTypeField) == "notypefield"


# ---------------------------------------------------------------------------
# Type unwrapping — _collect_constraints
# ---------------------------------------------------------------------------


def test_collect_constraints_int32_is_storage_primitive() -> None:
    """int32 range constraints should be skipped (storage primitive)."""
    from overture.schema.system.primitive import int32

    _, _, domain_kwargs, _, _ = _collect_constraints(int32)
    # int32 is in _STORAGE_PRIMITIVES, so its kwargs should NOT be selected as domain
    assert domain_kwargs == {}


def test_collect_constraints_feature_version_yields_ge_0() -> None:
    """FeatureVersion layers ge=0 on top of int32 — domain constraints are from FeatureVersion."""
    from overture.schema.core.types import FeatureVersion

    _, _, domain_kwargs, _, _ = _collect_constraints(FeatureVersion)
    assert "ge" in domain_kwargs
    assert domain_kwargs["ge"] == 0


def test_collect_constraints_min_zoom_yields_ge_0_le_23() -> None:
    """MinZoom has ge=0 and le=23 at the domain level."""
    from overture.schema.core.cartography import MinZoom

    _, _, domain_kwargs, _, _ = _collect_constraints(MinZoom)
    assert domain_kwargs.get("ge") == 0
    assert domain_kwargs.get("le") == 23


def test_collect_constraints_hex_color_has_pattern() -> None:
    """HexColor carries a HexColorConstraint in metadata."""
    from overture.schema.system.string import HexColor

    _, metadata, _, _, _ = _collect_constraints(HexColor)
    constraint_names = {type(m).__name__ for m in metadata}
    assert "HexColorConstraint" in constraint_names


def test_collect_constraints_stripped_string_detected() -> None:
    """StrippedString carries a StrippedConstraint."""
    from overture.schema.system.string import StrippedString

    _, metadata, _, _, _ = _collect_constraints(StrippedString)
    constraint_names = {type(m).__name__ for m in metadata}
    assert "StrippedConstraint" in constraint_names


def test_collect_constraints_optional_detection() -> None:
    """X | None should be detected as nullable."""
    _, _, _, is_nullable, _ = _collect_constraints(int | None)
    assert is_nullable is True


def test_collect_constraints_list_detection() -> None:
    """list[X] should be detected as list."""
    _, _, _, _, is_list = _collect_constraints(list[str])
    assert is_list is True


# ---------------------------------------------------------------------------
# Field-level rule extraction
# ---------------------------------------------------------------------------


def test_field_required_not_null() -> None:
    """Required field produces a not_null rule."""
    field_info = InlineModel.model_fields["name"]
    rules = _extract_field_rules(
        "test", "name", field_info, column_prefix="", parent_is_optional=False
    )
    checks = {r.check for r in rules}
    assert CheckType.NOT_NULL in checks


def test_field_optional_no_not_null() -> None:
    """Optional field does not produce a not_null rule."""
    field_info = InlineModel.model_fields["optional_str"]
    rules = _extract_field_rules(
        "test", "optional_str", field_info, column_prefix="", parent_is_optional=False
    )
    checks = {r.check for r in rules}
    assert CheckType.NOT_NULL not in checks


def test_field_enum_in_rule() -> None:
    """Enum field produces an 'in' rule with sorted values."""
    field_info = InlineModel.model_fields["color"]
    rules = _extract_field_rules(
        "test", "color", field_info, column_prefix="", parent_is_optional=False
    )
    in_rules = [r for r in rules if r.check == CheckType.IN]
    assert len(in_rules) == 1
    assert in_rules[0].value == ["blue", "green", "red"]
    assert in_rules[0].list_columns is None


def test_field_list_enum_list_columns() -> None:
    """list[Enum] produces an 'in' rule with list_columns=["tags"]."""
    field_info = InlineModel.model_fields["tags"]
    rules = _extract_field_rules(
        "test", "tags", field_info, column_prefix="", parent_is_optional=False
    )
    in_rules = [r for r in rules if r.check == CheckType.IN]
    assert len(in_rules) == 1
    assert in_rules[0].list_columns == ["tags"]


def test_field_strict_bool_is_type() -> None:
    """bool with strict=True produces an is_type 'boolean' rule."""
    field_info = InlineModel.model_fields["flag"]
    rules = _extract_field_rules(
        "test", "flag", field_info, column_prefix="", parent_is_optional=False
    )
    type_rules = [r for r in rules if r.check == CheckType.IS_TYPE]
    assert len(type_rules) == 1
    assert type_rules[0].value == "boolean"


def test_field_ge_le_between() -> None:
    """ge + le with no gt/lt produces a single 'between' rule."""
    field_info = InlineModel.model_fields["age"]
    rules = _extract_field_rules(
        "test", "age", field_info, column_prefix="", parent_is_optional=False
    )
    between_rules = [r for r in rules if r.check == CheckType.BETWEEN]
    assert len(between_rules) == 1
    assert between_rules[0].value == [0, 150]


def test_field_gt_lt_separate_rules() -> None:
    """gt + lt produce two separate rules (not between)."""

    class GtLtModel(BaseModel):
        value: Annotated[float | None, Field(gt=0, lt=360)] = None

    field_info = GtLtModel.model_fields["value"]
    rules = _extract_field_rules(
        "test", "value", field_info, column_prefix="", parent_is_optional=False
    )
    between_rules = [r for r in rules if r.check == CheckType.BETWEEN]
    assert len(between_rules) == 0
    gt_rules = [r for r in rules if r.check == CheckType.GT]
    lt_rules = [r for r in rules if r.check == CheckType.LT]
    assert len(gt_rules) == 1
    assert len(lt_rules) == 1


def test_field_nested_model_dot_notation() -> None:
    """Nested BaseModel fields produce dot-notation column names."""
    field_info = InlineModel.model_fields["nested"]
    rules = _extract_field_rules(
        "test", "nested", field_info, column_prefix="", parent_is_optional=False
    )
    columns = {r.column for r in rules}
    assert "nested.value" in columns


def test_field_nested_optional_parent_when_guard() -> None:
    """Required fields in optional nested models get a 'when: not_null' guard."""
    field_info = InlineModel.model_fields["nested"]
    rules = _extract_field_rules(
        "test", "nested", field_info, column_prefix="", parent_is_optional=False
    )
    not_null_rules = [
        r for r in rules if r.check == CheckType.NOT_NULL and r.column == "nested.value"
    ]
    assert len(not_null_rules) == 1
    assert not_null_rules[0].when is not None
    assert not_null_rules[0].when.column == "nested"
    assert not_null_rules[0].when.check == CheckType.NOT_NULL


def test_field_list_of_structs_list_columns_not_null() -> None:
    """Required fields inside list[Struct] get list_columns=["items"]."""
    field_info = InlineModel.model_fields["items"]
    rules = _extract_field_rules(
        "test", "items", field_info, column_prefix="", parent_is_optional=False
    )
    nn_rules = [
        r for r in rules if r.check == CheckType.NOT_NULL and r.column == "items.value"
    ]
    assert len(nn_rules) == 1
    assert nn_rules[0].list_columns == ["items"]


def test_field_list_of_structs_list_columns_min_length() -> None:
    """min_length inside list[Struct] gets list_columns=["items"]."""
    field_info = InlineModel.model_fields["items"]
    rules = _extract_field_rules(
        "test", "items", field_info, column_prefix="", parent_is_optional=False
    )
    ml_rules = [
        r
        for r in rules
        if r.check == CheckType.MIN_LENGTH and r.column == "items.value"
    ]
    assert len(ml_rules) == 1
    assert ml_rules[0].list_columns == ["items"]


def test_field_list_of_structs_list_columns_numeric() -> None:
    """Numeric constraints inside list[Struct] get list_columns=["items"]."""
    field_info = InlineModel.model_fields["items"]
    rules = _extract_field_rules(
        "test", "items", field_info, column_prefix="", parent_is_optional=False
    )
    gte_rules = [
        r for r in rules if r.check == CheckType.GTE and r.column == "items.score"
    ]
    assert len(gte_rules) == 1
    assert gte_rules[0].list_columns == ["items"]


def test_field_list_of_structs_list_columns_enum() -> None:
    """Enum in inside list[Struct] gets list_columns=["items"]."""
    field_info = InlineModel.model_fields["items"]
    rules = _extract_field_rules(
        "test", "items", field_info, column_prefix="", parent_is_optional=False
    )
    in_rules = [r for r in rules if r.check == CheckType.IN and r.column == "items.tag"]
    assert len(in_rules) == 1
    assert in_rules[0].list_columns == ["items"]


def test_field_non_list_struct_no_list_columns() -> None:
    """Scalar nested struct fields do NOT get list_columns."""
    field_info = InlineModel.model_fields["nested"]
    rules = _extract_field_rules(
        "test", "nested", field_info, column_prefix="", parent_is_optional=False
    )
    for r in rules:
        assert r.list_columns is None, f"Rule {r.name} should not have list_columns"


def test_field_geometry_type_constraint() -> None:
    """GeometryTypeConstraint produces a geometry_type rule."""
    from overture.schema.buildings.building import Building

    field_info = Building.model_fields["geometry"]
    rules = _extract_field_rules(
        "building", "geometry", field_info, column_prefix="", parent_is_optional=False
    )
    geo_rules = [r for r in rules if r.check == CheckType.GEOMETRY_TYPE]
    assert len(geo_rules) == 1
    assert "Polygon" in geo_rules[0].value
    assert "MultiPolygon" in geo_rules[0].value


def test_field_unique_items_constraint() -> None:
    """UniqueItemsConstraint produces a unique rule."""
    from overture.schema.divisions.division.models import Division

    field_info = Division.model_fields["hierarchies"]
    rules = _extract_field_rules(
        "division",
        "hierarchies",
        field_info,
        column_prefix="",
        parent_is_optional=False,
    )
    unique_rules = [r for r in rules if r.check == CheckType.UNIQUE]
    assert len(unique_rules) >= 1


def test_field_literal_single_eq() -> None:
    """A Literal['x'] field produces an 'eq' rule."""

    class LitModel(BaseModel):
        kind: Literal["special"]

    field_info = LitModel.model_fields["kind"]
    rules = _extract_field_rules(
        "test", "kind", field_info, column_prefix="", parent_is_optional=False
    )
    eq_rules = [r for r in rules if r.check == CheckType.EQ]
    assert len(eq_rules) == 1
    assert eq_rules[0].value == "special"


def test_field_literal_multi_in() -> None:
    """A Literal['a', 'b'] field produces an 'in' rule."""

    class LitModel(BaseModel):
        mode: Literal["fast", "slow", "auto"]

    field_info = LitModel.model_fields["mode"]
    rules = _extract_field_rules(
        "test", "mode", field_info, column_prefix="", parent_is_optional=False
    )
    in_rules = [r for r in rules if r.check == CheckType.IN]
    assert len(in_rules) == 1
    assert in_rules[0].value == ["auto", "fast", "slow"]


# ---------------------------------------------------------------------------
# Pattern constraints
# ---------------------------------------------------------------------------


def test_hex_color_pattern() -> None:
    """HexColor field produces a pattern rule."""
    from overture.schema.buildings.building import Building

    field_info = Building.model_fields["facade_color"]
    rules = _extract_field_rules(
        "building",
        "facade_color",
        field_info,
        column_prefix="",
        parent_is_optional=False,
    )
    pattern_rules = [r for r in rules if r.check == CheckType.PATTERN]
    assert len(pattern_rules) == 1
    assert "0-9A-Fa-f" in pattern_rules[0].value


# ---------------------------------------------------------------------------
# Model constraint extraction
# ---------------------------------------------------------------------------


def test_division_has_require_if_rules() -> None:
    """Division model produces require_if rules for conditional fields."""
    from overture.schema.divisions.division.models import Division

    rules = _extract_model_constraint_rules(Division, "division")
    required_when = [r for r in rules if r.name.endswith(".required_when")]
    assert len(required_when) > 0
    # parent_division_id should be required when subtype != country
    parent_rules = [r for r in required_when if "parent_division_id" in r.name]
    assert len(parent_rules) >= 1


def test_division_has_forbid_if_rules() -> None:
    """Division model produces forbid_if rules."""
    from overture.schema.divisions.division.models import Division

    rules = _extract_model_constraint_rules(Division, "division")
    forbidden_when = [r for r in rules if r.name.endswith(".forbidden_when")]
    assert len(forbidden_when) > 0
    # parent_division_id should be forbidden when subtype == country
    parent_rules = [r for r in forbidden_when if "parent_division_id" in r.name]
    assert len(parent_rules) == 1


def test_no_extra_fields_skipped() -> None:
    """NoExtraFieldsConstraint should not produce any rules."""
    from overture.schema.divisions.division.models import Norms

    rules = _extract_model_constraint_rules(Norms, "norms")
    assert len(rules) == 0


# ---------------------------------------------------------------------------
# Condition conversion
# ---------------------------------------------------------------------------


def test_convert_field_eq_condition() -> None:
    """FieldEqCondition converts to IR Condition with eq check."""
    from overture.schema.system.model_constraint.model_constraint import (
        FieldEqCondition,
    )

    cond = _convert_condition(FieldEqCondition("subtype", "country"))
    assert cond.column == "subtype"
    assert cond.check == CheckType.EQ
    assert cond.value == "country"


def test_convert_negated_field_eq_condition() -> None:
    """Not(FieldEqCondition) converts to neq check."""
    from overture.schema.system.model_constraint.model_constraint import (
        FieldEqCondition,
        Not,
    )

    cond = _convert_condition(Not(FieldEqCondition("subtype", "country")))
    assert cond.column == "subtype"
    assert cond.check == CheckType.NEQ
    assert cond.value == "country"


def test_convert_enum_value_extracted() -> None:
    """Enum values in conditions are extracted to their string value."""
    from overture.schema.divisions.enums import PlaceType
    from overture.schema.system.model_constraint.model_constraint import (
        FieldEqCondition,
    )

    cond = _convert_condition(FieldEqCondition("subtype", PlaceType.COUNTRY))
    assert cond.value == "country"


# ---------------------------------------------------------------------------
# Integration: extract(Building)
# ---------------------------------------------------------------------------


@pytest.fixture()
def building_spec():
    from overture.schema.buildings.building import Building

    return extract(Building)


def test_extract_building_dataset_name(building_spec) -> None:
    assert building_spec.name == "building"


def test_extract_building_source_model(building_spec) -> None:
    assert "Building" in building_spec.source_model


def test_extract_building_has_rules(building_spec) -> None:
    assert len(building_spec.rules) > 0


def test_extract_building_unique_rule_names(building_spec) -> None:
    names = [r.name for r in building_spec.rules]
    assert len(names) == len(set(names)), (
        f"Duplicate rule names: {[n for n in names if names.count(n) > 1]}"
    )


def test_extract_building_all_names_start_with_dataset(building_spec) -> None:
    for r in building_spec.rules:
        assert r.name.startswith("building."), (
            f"Rule {r.name} doesn't start with 'building.'"
        )


def test_extract_building_no_int32_storage_ranges(building_spec) -> None:
    """No rules should contain int32 storage range boundaries."""
    int32_bounds = {-(2**31), 2**31 - 1}
    for r in building_spec.rules:
        if r.check == CheckType.BETWEEN and r.value:
            for v in r.value:
                assert v not in int32_bounds, (
                    f"Rule {r.name} has int32 storage boundary {v}"
                )
        if r.check in (CheckType.GTE, CheckType.LTE, CheckType.GT, CheckType.LT):
            if r.value is not None:
                assert r.value not in int32_bounds, (
                    f"Rule {r.name} has int32 storage boundary {r.value}"
                )


def test_extract_building_geometry_type_rule(building_spec) -> None:
    geo_rules = [r for r in building_spec.rules if r.check == CheckType.GEOMETRY_TYPE]
    assert len(geo_rules) == 1
    assert set(geo_rules[0].value) == {"Polygon", "MultiPolygon"}


def test_extract_building_height_positive(building_spec) -> None:
    height_rules = [
        r
        for r in building_spec.rules
        if r.column == "height" and r.check == CheckType.GT
    ]
    assert len(height_rules) == 1
    assert height_rules[0].value == 0


def test_extract_building_roof_direction_ge_lt(building_spec) -> None:
    rd_rules = [r for r in building_spec.rules if r.column == "roof_direction"]
    checks = {r.check for r in rd_rules}
    assert CheckType.GTE in checks
    assert CheckType.LT in checks


def test_extract_building_subtype_enum_in(building_spec) -> None:
    subtype_rules = [
        r
        for r in building_spec.rules
        if r.column == "subtype" and r.check == CheckType.IN
    ]
    assert len(subtype_rules) == 1
    assert "agricultural" in subtype_rules[0].value


def test_extract_building_has_parts_is_type_boolean(building_spec) -> None:
    hp_rules = [
        r
        for r in building_spec.rules
        if r.column == "has_parts" and r.check == CheckType.IS_TYPE
    ]
    assert len(hp_rules) == 1
    assert hp_rules[0].value == "boolean"


def test_extract_building_version_not_null(building_spec) -> None:
    version_rules = [
        r
        for r in building_spec.rules
        if r.column == "version" and r.check == CheckType.NOT_NULL
    ]
    assert len(version_rules) == 1


def test_extract_building_version_gte_0(building_spec) -> None:
    """Version should have ge=0 from FeatureVersion, not int32 range."""
    version_rules = [r for r in building_spec.rules if r.column == "version"]
    # Should have non_negative (gte 0)
    gte_rules = [r for r in version_rules if r.check == CheckType.GTE]
    assert len(gte_rules) == 1
    assert gte_rules[0].value == 0


# ---------------------------------------------------------------------------
# Integration: extract(Division)
# ---------------------------------------------------------------------------


@pytest.fixture()
def division_spec():
    from overture.schema.divisions.division.models import Division

    return extract(Division)


def test_extract_division_dataset_name(division_spec) -> None:
    assert division_spec.name == "division"


def test_extract_division_has_rules(division_spec) -> None:
    assert len(division_spec.rules) > 0


def test_extract_division_unique_rule_names(division_spec) -> None:
    names = [r.name for r in division_spec.rules]
    assert len(names) == len(set(names)), (
        f"Duplicate rule names: {[n for n in names if names.count(n) > 1]}"
    )


def test_extract_division_conditional_require_if_rules(division_spec) -> None:
    """Division should have conditional not_null rules from require_if decorators."""
    required_when = [
        r for r in division_spec.rules if r.name.endswith(".required_when")
    ]
    assert len(required_when) > 0


def test_extract_division_conditional_forbid_if_rules(division_spec) -> None:
    """Division should have conditional is_null rules from forbid_if decorators."""
    forbidden_when = [
        r for r in division_spec.rules if r.name.endswith(".forbidden_when")
    ]
    assert len(forbidden_when) > 0


def test_extract_division_subtype_enum_values(division_spec) -> None:
    subtype_rules = [
        r
        for r in division_spec.rules
        if r.column == "subtype" and r.check == CheckType.IN
    ]
    assert len(subtype_rules) == 1
    assert "country" in subtype_rules[0].value
    assert "locality" in subtype_rules[0].value


def test_extract_division_population_gte_0(division_spec) -> None:
    pop_rules = [
        r
        for r in division_spec.rules
        if r.column == "population" and r.check == CheckType.GTE
    ]
    assert len(pop_rules) == 1
    assert pop_rules[0].value == 0


# ---------------------------------------------------------------------------
# Integration: extract_all()
# ---------------------------------------------------------------------------


def test_extract_all_returns_validation_spec() -> None:
    spec = extract_all()
    assert hasattr(spec, "datasets")
    assert hasattr(spec, "version")


def test_extract_all_has_datasets() -> None:
    spec = extract_all()
    assert len(spec.datasets) > 0


def test_extract_all_each_dataset_has_rules() -> None:
    spec = extract_all()
    for ds in spec.datasets:
        assert len(ds.rules) > 0, f"Dataset {ds.name} has no rules"


# ---------------------------------------------------------------------------
# CheckType extraction — one test per extractable CheckType
# ---------------------------------------------------------------------------
# CheckTypes not produced by extract(): NEQ, NOT_IN, COLUMN_LT, COLUMN_LTE,
# COLUMN_EQ. These are valid IR checks but only created via manual IR/YAML.


def _expected(model, rules):
    """Build expected DatasetSpec for a model extracted with dataset_name='test'."""
    _ID = Rule(
        name="test.id.not_null",
        column="id",
        check=CheckType.NOT_NULL,
        severity=Severity.ERROR,
    )
    return DatasetSpec(
        name="test",
        source_model=f"{model.__module__}.{model.__qualname__}",
        id_column="id",
        rules=[_ID] + rules,
    )


class BaseId(BaseModel):
    id: str


def test_extract_not_null() -> None:
    class M(BaseId):
        col: str

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.not_null",
                column="col",
                check=CheckType.NOT_NULL,
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_gt() -> None:
    class M(BaseId):
        col: int | None = Field(default=None, gt=4)

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.lower",
                column="col",
                check=CheckType.GT,
                value=4,
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_gte() -> None:
    class M(BaseId):
        col: int | None = Field(default=None, ge=5)

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.lower",
                column="col",
                check=CheckType.GTE,
                value=5,
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_lt() -> None:
    class M(BaseId):
        col: float | None = Field(default=None, lt=10.0)

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.upper",
                column="col",
                check=CheckType.LT,
                value=10.0,
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_lte() -> None:
    class M(BaseId):
        col: int | None = Field(default=None, le=10)

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.upper",
                column="col",
                check=CheckType.LTE,
                value=10,
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_eq() -> None:
    class M(BaseId):
        col: Literal["x"] | None = None

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.literal",
                column="col",
                check=CheckType.EQ,
                value="x",
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_between() -> None:
    class M(BaseId):
        col: int | None = Field(default=None, ge=0, le=100)

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.range",
                column="col",
                check=CheckType.BETWEEN,
                value=[0, 100],
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_in() -> None:
    class M(BaseId):
        col: Literal["a", "b", "c"] | None = None

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.valid",
                column="col",
                check=CheckType.IN,
                value=["a", "b", "c"],
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_min_length() -> None:
    class M(BaseId):
        col: str | None = Field(default=None, min_length=3)

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.min_length",
                column="col",
                check=CheckType.MIN_LENGTH,
                value=3,
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_max_length() -> None:
    class M(BaseId):
        col: str | None = Field(default=None, max_length=50)

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.max_length",
                column="col",
                check=CheckType.MAX_LENGTH,
                value=50,
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_is_type() -> None:
    class M(BaseId):
        col: Annotated[bool | None, Field(strict=True)] = None

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.type",
                column="col",
                check=CheckType.IS_TYPE,
                value="boolean",
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_unique() -> None:
    from overture.schema.system.field_constraint import UniqueItemsConstraint

    class M(BaseId):
        col: Annotated[list[str] | None, UniqueItemsConstraint()] = None

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.unique",
                column="col",
                check=CheckType.UNIQUE,
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_pattern() -> None:
    from overture.schema.system.field_constraint import PatternConstraint

    class M(BaseId):
        col: Annotated[str | None, PatternConstraint(r"^[A-Z]{2}$", "msg")] = None

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.col.pattern",
                column="col",
                check=CheckType.PATTERN,
                value=r"^[A-Z]{2}$",
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_geometry_type() -> None:
    from overture.schema.system.primitive import (
        Geometry,
        GeometryType,
        GeometryTypeConstraint,
    )

    class M(BaseId):
        geometry: Annotated[
            Geometry,
            GeometryTypeConstraint(GeometryType.POINT),
        ]

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.geometry.not_null",
                column="geometry",
                check=CheckType.NOT_NULL,
                severity=Severity.ERROR,
            ),
            Rule(
                name="test.geometry.type",
                column="geometry",
                check=CheckType.GEOMETRY_TYPE,
                value=["Point"],
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_is_null() -> None:
    from overture.schema.system.model_constraint import forbid_if
    from overture.schema.system.model_constraint.model_constraint import (
        FieldEqCondition,
    )

    @forbid_if(["col"], FieldEqCondition("flag", "x"))
    class M(BaseId):
        flag: str
        col: str | None = None

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.flag.not_null",
                column="flag",
                check=CheckType.NOT_NULL,
                severity=Severity.ERROR,
            ),
            Rule(
                name="test.col.forbidden_when",
                column="col",
                check=CheckType.IS_NULL,
                when=Condition(column="flag", check=CheckType.EQ, value="x"),
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_exactly_one_of() -> None:
    from overture.schema.system.model_constraint import radio_group

    @radio_group("a", "b")
    class M(BaseId):
        a: bool | None = None
        b: bool | None = None

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.a_b.exactly_one_of",
                columns=["a", "b"],
                check=CheckType.EXACTLY_ONE_OF,
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected


def test_extract_any_of() -> None:
    from overture.schema.system.model_constraint import require_any_of

    @require_any_of("a", "b")
    class M(BaseId):
        a: str | None = None
        b: str | None = None

    result = extract(M, dataset_name="test")
    expected = _expected(
        M,
        [
            Rule(
                name="test.a_b.any_of",
                columns=["a", "b"],
                check=CheckType.ANY_OF,
                severity=Severity.ERROR,
            ),
        ],
    )
    assert result == expected
