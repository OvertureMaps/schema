"""Golden JSON Schema test for DivisionArea type."""

from pathlib import Path

import pytest
from overture.schema.divisions import DivisionArea
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "division_area_baseline_schema.json"


@pytest.mark.baseline
def test_division_area_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(DivisionArea, GOLDEN, update=update_baselines)
