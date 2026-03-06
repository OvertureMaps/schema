"""Golden JSON Schema test for LandUse type."""

from pathlib import Path

import pytest
from overture.schema.base import LandUse
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "land_use_baseline_schema.json"


@pytest.mark.baseline
def test_land_use_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(LandUse, GOLDEN, update=update_baselines)
