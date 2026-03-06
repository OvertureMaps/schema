"""Golden JSON Schema test for DivisionBoundary type."""

from pathlib import Path

import pytest
from overture.schema.divisions import DivisionBoundary
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "division_boundary_baseline_schema.json"


@pytest.mark.baseline
def test_division_boundary_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(DivisionBoundary, GOLDEN, update=update_baselines)
