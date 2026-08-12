"""Golden JSON Schema test for Infrastructure type."""

from pathlib import Path

import pytest
from overture.schema.base import Infrastructure
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "infrastructure_baseline_schema.json"


@pytest.mark.baseline
def test_infrastructure_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Infrastructure, GOLDEN, update=update_baselines)
