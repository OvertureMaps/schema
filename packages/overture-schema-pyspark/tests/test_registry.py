"""Tests for the runtime registry's discovery of the generated tree.

The registry is built from the `overture.pyspark_validations` entry points,
a hand-maintained table in `pyproject.toml`. These tests hold that table to
the generated tree `make generate-pyspark` produces: one asserts the
registry actually populates, the other that the declared entry points match
the modules on disk exactly, so a forgotten or stale declaration fails here
rather than silently dropping a feature type at runtime.
"""

from __future__ import annotations

import importlib
import importlib.metadata
from pathlib import Path

import pytest

from overture.schema.pyspark._registry import REGISTRY

_GENERATED_ROOT = "overture.schema.pyspark.expressions.generated"
_ENTRY_POINT_GROUP = "overture.pyspark_validations"


def _generated_module_names() -> set[str]:
    """Dotted names of every generated model module on disk.

    Empty when the generated tree is absent -- mirroring the registry's own
    handling -- so the tests skip rather than error.
    """
    try:
        root = importlib.import_module(_GENERATED_ROOT)
    except ImportError:
        return set()
    names: set[str] = set()
    for base in root.__path__:
        for path in Path(base).rglob("*.py"):
            if path.name == "__init__.py":
                continue
            relative = path.relative_to(base).with_suffix("")
            names.add(".".join([_GENERATED_ROOT, *relative.parts]))
    return names


def _declared_entry_point_modules() -> set[str]:
    """Modules targeted by the declared `overture.pyspark_validations` entry points."""
    eps = importlib.metadata.entry_points(group=_ENTRY_POINT_GROUP)
    return {ep.module for ep in eps}


def test_registry_discovers_generated_models() -> None:
    """The registry finds generated modules through the declared entry points."""
    if not _generated_module_names():
        pytest.skip("generated tree not present; run `make generate-pyspark`")

    generated_entries = [
        key for key in REGISTRY if ":" in key and key.startswith("overture.schema.")
    ]
    assert generated_entries, "registry found no generated feature modules"


def test_entry_points_match_generated_tree() -> None:
    """Declared entry points match the generated modules on disk exactly.

    Catches a new feature whose entry point was never declared (present on
    disk, missing from the table) and a stale declaration left behind after
    a feature was removed (in the table, absent on disk).
    """
    on_disk = _generated_module_names()
    if not on_disk:
        pytest.skip("generated tree not present; run `make generate-pyspark`")

    declared = _declared_entry_point_modules()
    assert declared == on_disk, (
        "overture.pyspark_validations entry points are out of sync with the "
        "generated tree.\n"
        f"  declared but not on disk: {sorted(declared - on_disk)}\n"
        f"  on disk but not declared: {sorted(on_disk - declared)}"
    )
