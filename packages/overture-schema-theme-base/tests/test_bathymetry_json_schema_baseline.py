"""Golden JSON Schema test for Bathymetry type."""

from pathlib import Path

import pytest
from overture.schema.base import Bathymetry
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "bathymetry_baseline_schema.json"


@pytest.mark.baseline
def test_bathymetry_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Bathymetry, GOLDEN, update=update_baselines)
