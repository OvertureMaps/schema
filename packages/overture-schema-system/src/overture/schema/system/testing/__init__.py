"""Test helpers for Overture schema implementers.

Helpers for golden file comparison and JSON Schema baseline tests. Pure
helpers live in `golden`; pytest plumbing lives in `plugin` and is opt-in
via a `pytest11` entry point declared by consuming packages.
"""

from .golden import assert_golden, assert_json_schema_golden

__all__ = [
    "assert_golden",
    "assert_json_schema_golden",
]
