"""Golden JSON Schema test for Segment type."""

from pathlib import Path

import pytest
from overture.schema.system.testing import assert_json_schema_golden
from overture.schema.transportation import Segment

GOLDEN = Path(__file__).parent / "segment_baseline_schema.json"


@pytest.mark.baseline
def test_segment_json_schema(update_baselines: bool) -> None:
    assert_json_schema_golden(Segment, GOLDEN, update=update_baselines)
