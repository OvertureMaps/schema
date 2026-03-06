"""Golden JSON Schema test for Sources type."""

from pathlib import Path

import pytest
from overture.schema.annex import Sources
from overture.schema.system.testing import assert_json_schema_golden

GOLDEN = Path(__file__).parent / "sources_baseline_schema.json"


@pytest.mark.baseline
def test_sources_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Sources, GOLDEN, update=update_baselines)
