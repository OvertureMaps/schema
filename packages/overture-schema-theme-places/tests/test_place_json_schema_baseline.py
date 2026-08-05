"""Golden JSON Schema test for Place type."""

from pathlib import Path

import pytest
from overture.schema.places import Place
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "place_baseline_schema.json"


@pytest.mark.baseline
def test_place_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Place, GOLDEN, update=update_baselines)
