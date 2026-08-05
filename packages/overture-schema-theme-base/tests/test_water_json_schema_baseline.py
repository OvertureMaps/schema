"""Golden JSON Schema test for Water type."""

from pathlib import Path

import pytest
from overture.schema.base import Water
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "water_baseline_schema.json"


@pytest.mark.baseline
def test_water_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Water, GOLDEN, update=update_baselines)
