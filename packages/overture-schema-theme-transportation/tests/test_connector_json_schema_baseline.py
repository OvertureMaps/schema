"""Golden JSON Schema test for Connector type."""

from pathlib import Path

import pytest
from overture.schema.system.testing import assert_json_schema_golden
from overture.schema.transportation import Connector

GOLDEN = Path(__file__).parent / "connector_baseline_schema.json"


@pytest.mark.baseline
def test_connector_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Connector, GOLDEN, update=update_baselines)
