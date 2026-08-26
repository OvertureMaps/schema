"""Tests for the runtime registry's discovery of the generated tree.

The generated expression tree is PEP 420 (no `__init__.py`), so the
registry must walk it as a namespace package. No other test exercises the
real on-disk walk -- conformance tests import expression modules directly
and `test_validate.py` registers models through a test shim -- so an empty
registry would otherwise pass the suite unnoticed.

The walk has to work for a namespace portion inside a zip as well as one on
disk, because any wheel left unextracted on `sys.path` is zipimported --
Spark's `--py-files` and Glue's `--extra-py-files` both ship wheels that way.
Both shapes are exercised here against a synthetic package put on `sys.path`,
so the portion strings under test come from real import machinery rather than
being hand-written.
"""

from __future__ import annotations

import importlib
import sys
import zipfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

import pytest

from overture.schema.pyspark._registry import REGISTRY, _iter_generated_module_names

_GENERATED_ROOT = "overture.schema.pyspark.expressions.generated"

_PROBE_TOP = "zipimport_probe"
_PROBE_ROOT = f"{_PROBE_TOP}.expressions.generated"


@contextmanager
def _on_sys_path(entry: Path) -> Iterator[None]:
    """Put `entry` on `sys.path` and unimport the probe package after."""
    sys.path.insert(0, str(entry))
    importlib.invalidate_caches()
    try:
        yield
    finally:
        sys.path.remove(str(entry))
        for name in [n for n in sys.modules if n.split(".")[0] == _PROBE_TOP]:
            del sys.modules[name]
        importlib.invalidate_caches()


def _probe_members(relative_paths: Sequence[str]) -> list[str]:
    """Return archive member names for a probe tree holding `relative_paths`."""
    return [f"{_PROBE_ROOT.replace('.', '/')}/{p}" for p in relative_paths]


def _write_probe_wheel(wheel: Path, relative_paths: Sequence[str]) -> None:
    """Write a wheel-shaped zip holding a PEP 420 probe tree.

    Directory entries are written explicitly. `zipimport` recognises a
    namespace portion inside an archive only when the archive carries a
    directory entry for it, and that is what `uv_build` emits, so omitting
    them here would test a shape no real wheel has.
    """
    members = _probe_members(relative_paths)
    directories = sorted(
        {
            f"{parent}/"
            for member in members
            for parent in (str(p) for p in Path(member).parents)
            if parent != "."
        }
    )
    with zipfile.ZipFile(wheel, "w") as archive:
        for directory in directories:
            info = zipfile.ZipInfo(directory)
            info.external_attr = (0o40755 << 16) | 0x10
            archive.writestr(info, b"")
        for member in members:
            archive.writestr(member, "")


def _write_probe_directory(root: Path, relative_paths: Sequence[str]) -> None:
    """Write a PEP 420 probe tree as real directories under `root`."""
    for member in _probe_members(relative_paths):
        path = root / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")


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


def test_iter_generated_module_names_reads_a_zipimported_tree(tmp_path: Path) -> None:
    """Modules inside a wheel on `sys.path` are discovered.

    The wheel is never unpacked, so the namespace portion's `__path__` points
    inside the archive.
    """
    wheel = tmp_path / "zipimport_probe-0.0.0-py3-none-any.whl"
    _write_probe_wheel(wheel, ["schema/base/water.py", "schema/buildings/building.py"])

    with _on_sys_path(wheel):
        names = _iter_generated_module_names(_PROBE_ROOT)

    assert names == [
        f"{_PROBE_ROOT}.schema.base.water",
        f"{_PROBE_ROOT}.schema.buildings.building",
    ]


def test_iter_generated_module_names_reads_a_directory_tree(tmp_path: Path) -> None:
    """Modules in a real directory are discovered, and `__init__.py` is skipped."""
    _write_probe_directory(
        tmp_path, ["schema/base/water.py", "schema/base/__init__.py"]
    )

    with _on_sys_path(tmp_path):
        names = _iter_generated_module_names(_PROBE_ROOT)

    assert names == [f"{_PROBE_ROOT}.schema.base.water"]


def test_iter_generated_module_names_without_a_tree_is_empty() -> None:
    """An absent generated tree yields no names rather than raising."""
    assert _iter_generated_module_names(f"{_PROBE_ROOT}.absent") == []
