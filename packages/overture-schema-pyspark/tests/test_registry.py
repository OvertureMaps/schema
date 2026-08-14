"""Tests for the runtime registry's discovery of the generated tree.

The registry is built from the generated `_index` module, which codegen emits
alongside the validation modules. One test asserts the registry populates; the
other asserts the index lists exactly the modules on disk, so a codegen bug
that drops a module from the index fails here and never reaches runtime.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from overture.schema.pyspark._registry import REGISTRY

_GENERATED_ROOT = "overture.schema.pyspark.expressions.generated"
_INDEX_MODULE = f"{_GENERATED_ROOT}._index"


def _generated_module_names() -> set[str]:
    """Dotted names of every generated model module on disk.

    Empty when the generated tree is absent, matching the registry's own
    handling, so the tests skip cleanly. The `_index` module is excluded
    because it is discovery machinery; only validation modules are counted.
    """
    try:
        root = importlib.import_module(_GENERATED_ROOT)
    except ImportError:
        return set()
    names: set[str] = set()
    for base in root.__path__:
        for path in Path(base).rglob("*.py"):
            if path.name in ("__init__.py", "_index.py"):
                continue
            relative = path.relative_to(base).with_suffix("")
            names.add(".".join([_GENERATED_ROOT, *relative.parts]))
    return names


def test_registry_discovers_generated_models() -> None:
    """The registry finds generated modules through the index."""
    if not _generated_module_names():
        pytest.skip("generated tree not present; run `make generate-pyspark`")

    generated_entries = [
        key for key in REGISTRY if ":" in key and key.startswith("overture.schema.")
    ]
    assert generated_entries, "registry found no generated feature modules"


def test_index_lists_every_generated_module() -> None:
    """The generated index covers exactly the modules on disk.

    Guards the codegen step that emits `_index`: a module generated but left
    out of the index (or an index entry with no module) would otherwise drop
    that feature type from the registry silently.
    """
    on_disk = _generated_module_names()
    if not on_disk:
        pytest.skip("generated tree not present; run `make generate-pyspark`")

    index = importlib.import_module(_INDEX_MODULE)
    indexed = {module.__name__ for module in index.MODULES}
    assert indexed == on_disk, (
        "generated _index is out of sync with the modules on disk.\n"
        f"  indexed but not on disk: {sorted(indexed - on_disk)}\n"
        f"  on disk but not indexed: {sorted(on_disk - indexed)}"
    )
