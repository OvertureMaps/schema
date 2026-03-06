"""Golden JSON Schema test for Address type."""

from pathlib import Path

import pytest
from overture.schema.addresses import Address
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "address_baseline_schema.json"


@pytest.mark.baseline
def test_address_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Address, GOLDEN, update=update_baselines)
