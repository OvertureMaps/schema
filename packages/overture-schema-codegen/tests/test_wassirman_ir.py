"""Tests for wassirman IR data types."""

import yaml
from overture.schema.codegen.wassirman.ir import (
    ConditionIR,
    DatasetIR,
    RuleIR,
    ValidationIR,
)


class TestRuleIR:
    def test_to_dict_excludes_none(self) -> None:
        rule = RuleIR(
            name="t.id.not_null", check="not_null", severity="error", column="id"
        )
        d = rule.to_dict()
        assert d == {
            "name": "t.id.not_null",
            "column": "id",
            "check": "not_null",
            "severity": "error",
        }
        assert "value" not in d
        assert "list_columns" not in d
        assert "when" not in d

    def test_to_dict_with_all_fields(self) -> None:
        rule = RuleIR(
            name="t.x.not_null",
            check="not_null",
            severity="error",
            column="x",
            list_columns=["a"],
            when=ConditionIR(column="a", check="not_null"),
        )
        d = rule.to_dict()
        assert d["list_columns"] == ["a"]
        assert d["when"] == {"column": "a", "check": "not_null"}

    def test_to_dict_multi_field(self) -> None:
        rule = RuleIR(
            name="t.any_of", check="any_of", severity="error", columns=["a", "b"]
        )
        d = rule.to_dict()
        assert d["columns"] == ["a", "b"]
        assert "column" not in d

    def test_to_dict_with_value(self) -> None:
        rule = RuleIR(
            name="t.x.gte", check="gte", severity="error", column="x", value=0
        )
        assert rule.to_dict()["value"] == 0


class TestConditionIR:
    def test_to_dict_no_value(self) -> None:
        cond = ConditionIR(column="a", check="not_null")
        assert cond.to_dict() == {"column": "a", "check": "not_null"}

    def test_to_dict_with_value(self) -> None:
        cond = ConditionIR(column="a", check="eq", value="x")
        assert cond.to_dict() == {"column": "a", "check": "eq", "value": "x"}


class TestDatasetIR:
    def test_to_dict(self) -> None:
        rule = RuleIR(
            name="t.id.not_null", check="not_null", severity="error", column="id"
        )
        ds = DatasetIR(
            name="test", source_model="mod.Test", id_column="id", rules=[rule]
        )
        d = ds.to_dict()
        assert d["name"] == "test"
        assert d["source_model"] == "mod.Test"
        assert d["id_column"] == "id"
        assert len(d["rules"]) == 1  # type: ignore[arg-type]


class TestValidationIR:
    def test_to_yaml_roundtrips(self) -> None:
        rule = RuleIR(
            name="t.id.not_null", check="not_null", severity="error", column="id"
        )
        ds = DatasetIR(
            name="test", source_model="mod.Test", id_column="id", rules=[rule]
        )
        ir = ValidationIR(datasets=[ds])
        text = ir.to_yaml()
        parsed = yaml.safe_load(text)
        assert parsed["version"] == "1"
        assert len(parsed["datasets"]) == 1
        assert parsed["datasets"][0]["rules"][0]["check"] == "not_null"
