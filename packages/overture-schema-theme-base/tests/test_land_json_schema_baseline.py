"""Golden JSON Schema test for Land type."""

from pathlib import Path

import pytest
from overture.schema.base import Land
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "land_baseline_schema.json"


@pytest.mark.baseline
def test_land_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Land, GOLDEN, update=update_baselines)
