"""Golden JSON Schema test for Division type."""

from pathlib import Path

import pytest
from overture.schema.divisions import Division
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "division_baseline_schema.json"


@pytest.mark.baseline
def test_division_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Division, GOLDEN, update=update_baselines)
