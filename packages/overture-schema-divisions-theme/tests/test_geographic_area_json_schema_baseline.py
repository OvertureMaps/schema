"""Baseline JSON Schema tests for geographic area type."""

import json
import os

from overture.schema.divisions import GeographicArea
from overture.schema.system.json_schema import json_schema


def test_geographic_area_json_schema_baseline() -> None:
    """Test that GeographicArea generates consistent JSON Schema (baseline comparison)."""
    schema = json_schema(GeographicArea)

    # Path to baseline file
    baseline_file = os.path.join(
        os.path.dirname(__file__), "geographic_area_baseline_schema.json"
    )

    # If baseline doesn't exist, create it
    if not os.path.exists(baseline_file):
        with open(baseline_file, "w") as f:
            json.dump(schema, f, indent=2, sort_keys=True)

    # Load baseline and compare
    with open(baseline_file) as f:
        baseline_schema = json.load(f)

    # Compare the generated schema with the baseline
    assert schema == baseline_schema, (
        "Generated JSON Schema differs from baseline. "
        "If this change is intentional, delete the baseline file to regenerate it."
    )
