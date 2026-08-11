"""Golden JSON Schema test for LandCover type."""

from pathlib import Path

import pytest
from overture.schema.base import LandCover
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "land_cover_baseline_schema.json"


@pytest.mark.baseline
def test_land_cover_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(LandCover, GOLDEN, update=update_baselines)
