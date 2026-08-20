"""Tests for the PySpark guards in the package's __init__."""

import importlib
import importlib.metadata
import sys
from types import ModuleType

import pyspark
import pytest

from overture.schema.pyspark._pyspark_version import declared_pyspark_specifier


class _BlockedFinder:
    """A meta_path finder that reports one module as genuinely absent.

    Raising from `find_spec` reproduces what an uninstalled module does at an
    `import` statement -- a `ModuleNotFoundError` carrying `name`. Setting
    `sys.modules[name] = None` would raise `ImportError` instead, which is not
    the error a missing package actually produces.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def find_spec(
        self, fullname: str, path: object = None, target: ModuleType | None = None
    ) -> None:
        if fullname == self.name or fullname.startswith(f"{self.name}."):
            raise ModuleNotFoundError(f"No module named {fullname!r}", name=fullname)
        return None


def _unload(monkeypatch: pytest.MonkeyPatch, *roots: str) -> None:
    """Drop modules from sys.modules so importing them re-runs their top level.

    monkeypatch restores the original module objects at teardown, so modules
    already imported by the rest of the suite keep their identity.
    """
    for name in [
        name
        for name in sys.modules
        if any(name == root or name.startswith(f"{root}.") for root in roots)
    ]:
        monkeypatch.delitem(sys.modules, name)


def test_missing_pyspark_names_the_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pyspark", None)
    _unload(monkeypatch, "overture.schema.pyspark")

    with pytest.raises(ModuleNotFoundError) as excinfo:
        importlib.import_module("overture.schema.pyspark")

    assert "overture-schema-pyspark[spark]" in str(excinfo.value)


def test_unrelated_missing_dependency_surfaces_its_own_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The guard reports only a missing pyspark, never another package's."""
    _unload(monkeypatch, "overture.schema.pyspark", "overture.schema.system", "shapely")
    monkeypatch.setattr(sys, "meta_path", [_BlockedFinder("shapely"), *sys.meta_path])

    with pytest.raises(ImportError) as excinfo:
        importlib.import_module("overture.schema.pyspark")

    assert "shapely" in str(excinfo.value)
    assert "overture-schema-pyspark[spark]" not in str(excinfo.value)


def test_package_imports_when_pyspark_is_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _unload(monkeypatch, "overture.schema.pyspark")

    module = importlib.import_module("overture.schema.pyspark")

    assert module.Check.__name__ == "Check"


def test_pyspark_below_the_declared_floor_names_both_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pyspark, "__version__", "3.3.4")
    _unload(monkeypatch, "overture.schema.pyspark")

    with pytest.raises(ImportError) as excinfo:
        importlib.import_module("overture.schema.pyspark")

    message = str(excinfo.value)
    assert "3.3.4" in message
    assert ">=3.4" in message


def test_the_floor_is_read_from_package_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The declared floor is the one that applies, not one restated in code.

    A guard carrying its own copy of the version passes the test above and
    fails this one, which is the drift this indirection exists to prevent.
    """
    monkeypatch.setattr(
        importlib.metadata,
        "requires",
        lambda name: ["pyspark>=99.0 ; extra == 'spark'"],
    )
    _unload(monkeypatch, "overture.schema.pyspark")

    with pytest.raises(ImportError) as excinfo:
        importlib.import_module("overture.schema.pyspark")

    assert ">=99.0" in str(excinfo.value)
    assert pyspark.__version__ in str(excinfo.value)  # type: ignore[attr-defined]


def test_unreadable_package_metadata_does_not_block_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No declaration to read means no floor to enforce, not a failed import."""

    def _absent(name: str) -> list[str]:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "requires", _absent)
    _unload(monkeypatch, "overture.schema.pyspark")

    module = importlib.import_module("overture.schema.pyspark")

    assert module.Check.__name__ == "Check"


def test_pyspark_without_a_reported_version_does_not_block_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A PySpark that reports no version is unjudgeable, not out of range."""
    monkeypatch.delattr(pyspark, "__version__")
    _unload(monkeypatch, "overture.schema.pyspark")

    module = importlib.import_module("overture.schema.pyspark")

    assert module.Check.__name__ == "Check"


def test_the_declared_floor_is_readable_here() -> None:
    """The metadata lookup resolves, so the guard is live and not inert.

    Every other test in this file passes whether or not it does: a lookup that
    finds nothing reports no floor, which reads exactly like a floor that is
    satisfied.
    """
    assert declared_pyspark_specifier() is not None
