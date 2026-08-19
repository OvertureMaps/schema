"""Tests for the missing-PySpark guard in the package's __init__."""

import importlib
import sys
from types import ModuleType

import pytest


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
