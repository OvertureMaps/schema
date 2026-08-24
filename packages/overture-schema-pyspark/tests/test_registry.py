"""Tests for the runtime registry's discovery of the generated tree.

The generated expression tree is PEP 420 (no `__init__.py`), so the
registry must walk it as a namespace package. No other test exercises the
real on-disk walk -- conformance tests import expression modules directly
and `test_validate.py` registers models through a test shim -- so an empty
registry would otherwise pass the suite unnoticed.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from overture.schema.pyspark._registry import REGISTRY

_GENERATED_ROOT = "overture.schema.pyspark.expressions.generated"


def _generated_leaf_count() -> int:
    """Count generated model modules on disk (excludes namespace dirs).

    Returns 0 when the generated tree is absent -- mirroring the registry's
    own `ImportError` handling -- so the test skips rather than errors.
    """
    try:
        root = importlib.import_module(_GENERATED_ROOT)
    except ImportError:
        return 0
    return sum(
        1
        for base in root.__path__
        for path in Path(base).rglob("*.py")
        if path.name != "__init__.py"
    )


def test_registry_discovers_generated_models() -> None:
    """The registry finds generated modules under the PEP 420 namespace tree."""
    if _generated_leaf_count() == 0:
        pytest.skip("generated tree not present; run `make generate-pyspark`")

    generated_entries = [
        key for key in REGISTRY if ":" in key and key.startswith("overture.schema.")
    ]
    assert generated_entries, "registry found no generated feature modules on disk"
