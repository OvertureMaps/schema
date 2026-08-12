"""Golden JSON Schema test for Building type."""

from pathlib import Path

import pytest
from overture.schema.buildings.building import Building
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "building_baseline_schema.json"


@pytest.mark.baseline
def test_building_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Building, GOLDEN, update=update_baselines)
