"""Golden JSON Schema test for BuildingPart type."""

from pathlib import Path

import pytest
from overture.schema.buildings.building_part import BuildingPart
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "building_part_baseline_schema.json"


@pytest.mark.baseline
def test_building_part_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(BuildingPart, GOLDEN, update=update_baselines)
