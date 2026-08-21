"""Tests for the runtime registry's discovery of the generated tree.

The generated expression tree is PEP 420 (no `__init__.py`), so the
registry must walk it as a namespace package. No other test exercises the
real on-disk walk, since conformance tests import expression modules
directly and `test_validate.py` registers models through a test shim, so an
empty registry would otherwise pass the suite unnoticed.

The zip branch of the walk (a namespace portion inside a wheel on
`sys.path`, as on Glue) has no such incidental coverage either, so it is
exercised directly here against a synthetic archive.
"""

from __future__ import annotations

import importlib
import zipfile
from pathlib import Path

import pytest

from overture.schema.pyspark._registry import (
    _GENERATED_ROOT,
    REGISTRY,
    _iter_generated_module_names,
)


def _generated_leaf_count() -> int:
    """Count generated model modules on disk (excludes namespace dirs).

    Returns 0 when the generated tree is absent, matching the registry's own
    `ImportError` handling, so the test skips cleanly.
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


def test_iter_generated_module_names_reads_zip(tmp_path: Path) -> None:
    """The zip branch lists generated modules inside a wheel on `sys.path`.

    Mirrors how Glue loads the package via `--extra-py-files`: the namespace
    portion is `<wheel>/overture/schema/pyspark/expressions/generated`, and
    its leading `<wheel>` segment is a real zip file. Namespace `__init__.py`
    markers and members outside the generated prefix are excluded, and the
    two feature modules come back as dotted names.
    """
    prefix = "overture/schema/pyspark/expressions/generated"
    wheel = tmp_path / "overture_schema_pyspark-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(f"{prefix}/overture/schema/buildings/building.py", "\n")
        archive.writestr(f"{prefix}/overture/schema/base/water.py", "\n")
        archive.writestr(f"{prefix}/overture/schema/base/__init__.py", "\n")
        archive.writestr("overture/schema/pyspark/check.py", "\n")

    names = _iter_generated_module_names([f"{wheel}/{prefix}"])

    assert names == [
        f"{_GENERATED_ROOT}.overture.schema.base.water",
        f"{_GENERATED_ROOT}.overture.schema.buildings.building",
    ]


def test_iter_generated_module_names_ignores_nonexistent_path(tmp_path: Path) -> None:
    """A portion that is neither a directory nor inside a zip yields nothing."""
    assert _iter_generated_module_names([str(tmp_path / "missing")]) == []
