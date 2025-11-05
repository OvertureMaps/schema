"""Baseline JSON Schema tests for sources model."""

import json
import os

from overture.schema.annex import Sources
from overture.schema.system.json_schema import json_schema


def test_sources_json_schema_baseline() -> None:
    """Ensure Sources model JSON Schema matches the committed baseline."""
    schema = json_schema(Sources)

    baseline_file = os.path.join(
        os.path.dirname(__file__), "sources_baseline_schema.json"
    )

    if not os.path.exists(baseline_file):
        with open(baseline_file, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, sort_keys=True)

    with open(baseline_file, encoding="utf-8") as f:
        baseline_schema = json.load(f)

    assert schema == baseline_schema, (
        "Generated JSON Schema differs from baseline. "
        "If this change is intentional, delete the baseline file to regenerate it."
    )
