"""Tests for the conformance test harness."""

from __future__ import annotations

import re

import pytest
from overture.schema.pyspark.check import Check, CheckShape
from pyspark.sql import Row, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

from ._support.harness import (
    assert_schema_covers_checks,
    build_scenario_map,
    build_scenario_rows,
    index_violations,
    sanitize_row,
    scenario_uuid,
)
from ._support.helpers import PathTraversalError, set_at_path
from ._support.scenarios import Scenario


class TestScenarioUuid:
    def test_deterministic(self) -> None:
        """Same ID produces same UUID."""
        assert scenario_uuid("building::id:required") == scenario_uuid(
            "building::id:required"
        )

    def test_different_ids_different_uuids(self) -> None:
        assert scenario_uuid("a::b:c") != scenario_uuid("d::e:f")

    def test_valid_uuid_format(self) -> None:
        uuid_str = scenario_uuid("test::x:y")
        assert re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            uuid_str,
        )


class TestBuildScenarioMap:
    def test_scenarios_get_valid_and_invalid_entries(self) -> None:
        scenarios = [
            Scenario(
                id="f::x:required",
                scaffold={},
                mutate=set_at_path("x", None),
                expected_field="x",
                expected_check="required",
            ),
        ]
        scenario_map = build_scenario_map(scenarios, feature_name="f")
        assert scenario_uuid("f::x:required::valid") in scenario_map
        assert (
            scenario_map[scenario_uuid("f::x:required::valid")]
            == "f::x:required::valid"
        )
        assert scenario_uuid("f::x:required::invalid") in scenario_map
        assert (
            scenario_map[scenario_uuid("f::x:required::invalid")]
            == "f::x:required::invalid"
        )

    def test_baseline_plus_two_entries_per_scenario(self) -> None:
        scenarios = [
            Scenario(
                id="f::x:check",
                scaffold={},
                mutate=set_at_path("x", 0),
                expected_field="x",
                expected_check="check",
            ),
        ]
        scenario_map = build_scenario_map(scenarios, feature_name="f")
        # baseline + (::valid, ::invalid) for the one scenario
        assert len(scenario_map) == 3

    def test_duplicate_id_values_raises(self) -> None:
        scenarios = [
            Scenario(
                id="f::x:required",
                scaffold={},
                mutate=set_at_path("x", None),
                expected_field="x",
                expected_check="required",
            ),
            Scenario(
                id="f::x:required",
                scaffold={},
                mutate=set_at_path("x", None),
                expected_field="x",
                expected_check="required",
            ),
        ]
        with pytest.raises(ValueError, match="Duplicate"):
            build_scenario_map(scenarios, feature_name="f")


class TestBuildScenarioRows:
    def test_baseline_row_included(self) -> None:
        base = {"id": "original-uuid", "theme": "buildings", "type": "building", "x": 1}
        rows, scenario_map, skipped = build_scenario_rows(
            base, [], feature_name="building"
        )
        assert len(rows) == 1
        assert rows[0]["theme"] == "buildings"
        assert "_scenario_id" in rows[0]

    def test_path_traversal_error_skips(self) -> None:
        """Mutation functions that raise PathTraversalError produce skips."""
        base = {"theme": "t", "type": "ty"}

        def bad_mutation(row: dict) -> dict:
            raise PathTraversalError("cannot traverse")

        scenarios = [
            Scenario(
                id="f::x:check",
                scaffold={},
                mutate=bad_mutation,
                expected_field="x",
                expected_check="check",
            ),
        ]
        rows, scenario_map, skipped = build_scenario_rows(
            base, scenarios, feature_name="f"
        )
        assert len(rows) == 1
        assert "f::x:check" in skipped

    def test_scenario_creates_valid_and_invalid_rows(self) -> None:
        """Each Scenario produces both a valid and an invalid row."""
        base = {"id": "orig", "theme": "t", "type": "ty", "x": 1}
        scenarios = [
            Scenario(
                id="f::x:required",
                scaffold={},
                mutate=set_at_path("x", None),
                expected_field="x",
                expected_check="required",
            ),
        ]
        rows, scenario_map, skipped = build_scenario_rows(
            base, scenarios, feature_name="f"
        )
        # baseline + valid + invalid
        assert len(rows) == 3
        assert rows[1]["x"] == 1  # valid row is a copy of base_row
        assert rows[2]["x"] is None
        assert rows[1]["_scenario_id"] == scenario_uuid("f::x:required::valid")
        assert rows[2]["_scenario_id"] == scenario_uuid("f::x:required::invalid")

    def test_valid_row_uses_base_row_not_scaffold(self) -> None:
        """Valid row is a copy of base_row, not the scaffold-merged row."""
        base = {"id": "orig", "theme": "t", "type": "ty", "items": [{"a": 1, "b": 2}]}
        scenarios = [
            Scenario(
                id="f::items[].a:required",
                scaffold={"items": [{"a": 0}]},
                mutate=set_at_path("items[].a", None),
                expected_field="items[].a",
                expected_check="required",
            ),
        ]
        rows, scenario_map, skipped = build_scenario_rows(
            base, scenarios, feature_name="f"
        )
        assert len(rows) == 3
        # Valid row uses base_row (preserves all fields in items element)
        assert rows[1]["items"] == [{"a": 1, "b": 2}]
        # Invalid row uses scaffold-merged row
        assert rows[2]["items"][0]["a"] is None

    def test_scaffold_merged_onto_invalid_row(self) -> None:
        base_row = {"id": "x", "a": 1}
        s = Scenario(
            id="test::b:check",
            scaffold={"b": 10},
            mutate=set_at_path("b", 0),
            expected_field="b",
            expected_check="check",
        )
        rows, scenario_map, skipped = build_scenario_rows(
            base_row, [s], feature_name="test"
        )
        invalid_id = scenario_uuid("test::b:check::invalid")
        invalid_row = next(r for r in rows if r["_scenario_id"] == invalid_id)
        # base field preserved, scaffold provides b, path overrides b
        assert invalid_row["a"] == 1
        assert invalid_row["b"] == 0

    def test_applies_scaffold_then_mutation(self) -> None:
        base_row = {"id": "x", "a": 1}
        s = Scenario(
            id="test::model:check",
            scaffold={"b": 10},
            mutate=lambda row: {**row, "a": None},
            expected_field="a",
            expected_check="required",
        )
        rows, scenario_map, skipped = build_scenario_rows(
            base_row, [s], feature_name="test"
        )
        assert len(rows) == 3
        assert not skipped
        invalid_id = scenario_uuid("test::model:check::invalid")
        invalid_row = next(r for r in rows if r["_scenario_id"] == invalid_id)
        # scaffold merged: b exists
        assert invalid_row["b"] == 10
        # mutation applied: a is None
        assert invalid_row["a"] is None


class TestSanitizeRow:
    def test_nested_geometry_converted(self) -> None:
        row = {
            "id": "x",
            "nested": {"geometry": "POINT (1 2)"},
        }
        result = sanitize_row(row)
        assert isinstance(result["nested"]["geometry"], bytes)

    def test_top_level_geometry_converted(self) -> None:
        row = {"id": "x", "geometry": "POINT (1 2)"}
        result = sanitize_row(row)
        assert isinstance(result["geometry"], bytes)

    def test_non_wkt_string_at_geometry_key_unchanged(self) -> None:
        row = {"id": "x", "geometry": "not-a-geometry"}
        result = sanitize_row(row)
        assert result["geometry"] == "not-a-geometry"

    def test_non_geometry_keys_unchanged(self) -> None:
        row = {"id": "x", "name": "POINT (1 2)"}
        result = sanitize_row(row)
        assert result["name"] == "POINT (1 2)"


class TestSchemaAssertions:
    def test_assert_schema_covers_checks_passes(self, spark: SparkSession) -> None:
        schema = StructType(
            [
                StructField("id", StringType()),
                StructField("x", IntegerType()),
            ]
        )
        checks = [
            Check(
                field="id",
                name="required",
                expr=F.lit(None),
                shape=CheckShape.SCALAR,
                root_field="id",
            )
        ]
        assert_schema_covers_checks(schema, checks)  # should not raise

    def test_assert_schema_covers_synthetic_field(self, spark: SparkSession) -> None:
        schema = StructType([StructField("sources", ArrayType(StringType()))])
        checks = [
            Check(
                field="sources_min_length",
                name="min_length",
                expr=F.lit(None),
                shape=CheckShape.SCALAR,
                root_field="sources",
            )
        ]
        assert_schema_covers_checks(schema, checks)  # should not raise

    def test_assert_schema_covers_checks_missing_field(
        self, spark: SparkSession
    ) -> None:
        schema = StructType([StructField("id", StringType())])
        checks = [
            Check(
                field="missing",
                name="required",
                expr=F.lit(None),
                shape=CheckShape.SCALAR,
                root_field="missing",
            )
        ]
        with pytest.raises(AssertionError, match="missing"):
            assert_schema_covers_checks(schema, checks)

    def test_assert_schema_covers_synthetic_model_check(
        self, spark: SparkSession
    ) -> None:
        """root_field=None passes regardless of schema (radio_group, etc.)."""
        schema = StructType([StructField("id", StringType())])
        checks = [
            Check(
                field="radio_group",
                name="radio_group",
                expr=F.lit(None),
                shape=CheckShape.SCALAR,
                root_field=None,
            )
        ]
        assert_schema_covers_checks(schema, checks)  # should not raise


class TestIndexViolations:
    def test_groups_by_scenario_id(self) -> None:
        uuid_a = scenario_uuid("f::a:required")
        uuid_b = scenario_uuid("f::b:enum")
        scenario_map = {uuid_a: "f::a:required", uuid_b: "f::b:enum"}
        violation_rows = [
            Row(
                _scenario_id=uuid_a,
                x=1,
                field="a",
                check="required",
                message="missing",
            ),
            Row(
                _scenario_id=uuid_b,
                x=2,
                field="b",
                check="enum",
                message="invalid",
            ),
        ]
        result = index_violations(violation_rows, scenario_map)
        assert result["f::a:required"] == {("a", "required")}
        assert result["f::b:enum"] == {("b", "enum")}

    def test_multiple_violations_per_scenario(self) -> None:
        uuid_a = scenario_uuid("f::a:r")
        scenario_map = {uuid_a: "f::a:r"}
        violation_rows = [
            Row(
                _scenario_id=uuid_a,
                x=1,
                field="a",
                check="required",
                message="m1",
            ),
            Row(
                _scenario_id=uuid_a,
                x=1,
                field="a",
                check="bounds",
                message="m2",
            ),
        ]
        result = index_violations(violation_rows, scenario_map)
        assert result["f::a:r"] == {("a", "required"), ("a", "bounds")}

    def test_empty_violations(self) -> None:
        result = index_violations([], {})
        assert result == {}
