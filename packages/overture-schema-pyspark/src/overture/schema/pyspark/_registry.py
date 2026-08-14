"""Runtime registry of feature validations.

Built at import time by walking the generated `expressions.generated`
namespace and collecting every module that exposes the
codegen-emitted `ENTRY_POINT` and `MODEL_VALIDATION` constants.

The generated tree on disk is the runtime source of truth: the
registry contains exactly what was generated, regardless of which
theme packages are installed alongside the pyspark package. A missing
`expressions/generated/` subtree simply yields an empty registry --
the package still imports cleanly.
"""

from __future__ import annotations

import importlib
import logging
import zipfile
from pathlib import Path, PurePosixPath

from .check import ModelValidation

logger = logging.getLogger(__name__)

_GENERATED_ROOT = "overture.schema.pyspark.expressions.generated"


def _zip_boundary(root_path: str) -> tuple[str, str] | None:
    """Split a namespace portion into `(zip file path, internal prefix)`.

    Returns `None` if `root_path` isn't a real directory and isn't inside a
    zip either (e.g. an empty/nonexistent portion). A namespace portion
    loaded straight from a wheel on `sys.path` -- as happens on Glue, via
    `--extra-py-files` -- looks like `.../some_pkg-1.0-py3-none-any.whl/a/b/c`:
    not a directory on disk, but the leading `.../some_pkg....whl` segment is
    a real zip file. `importlib.resources`'s `Traversable` API is meant to
    cover exactly this, but its `MultiplexedPath` (at least through Python
    3.10) raises `NotADirectoryError` the moment any namespace portion isn't
    a real directory, so it can't be used here either.
    """
    path = Path(root_path)
    for parent in (path, *path.parents):
        if parent.is_file() and zipfile.is_zipfile(parent):
            return str(parent), path.relative_to(parent).as_posix()
    return None


def _iter_generated_module_names(root_paths: list[str]) -> list[str]:
    """Return the dotted names of every generated module under `root_paths`.

    The generated tree is PEP 420 (no `__init__.py`), so its subdirectories
    are namespace packages; `pkgutil.walk_packages` skips those, so each
    namespace portion is walked directly instead: as a real directory via
    `pathlib`, or as a zip member list via `zipfile` when the portion is
    inside a wheel on `sys.path` rather than extracted to disk.
    """
    names: list[str] = []
    for root_path in root_paths:
        base = Path(root_path)
        if base.is_dir():
            for path in sorted(base.rglob("*.py")):
                if path.name == "__init__.py":
                    continue
                relative = path.relative_to(base).with_suffix("")
                names.append(".".join([_GENERATED_ROOT, *relative.parts]))
            continue

        boundary = _zip_boundary(root_path)
        if boundary is None:
            continue
        zip_path, prefix = boundary
        prefix = f"{prefix}/" if prefix else ""
        with zipfile.ZipFile(zip_path) as archive:
            for entry in archive.namelist():
                if not entry.startswith(prefix) or not entry.endswith(".py"):
                    continue
                relative = PurePosixPath(entry[len(prefix) :])
                if relative.name == "__init__.py":
                    continue
                dotted = relative.with_suffix("").as_posix().replace("/", ".")
                names.append(".".join([_GENERATED_ROOT, dotted]))
    return sorted(names)


def _walk() -> tuple[dict[str, ModelValidation], dict[str, dict[str, str]]]:
    """Walk the generated tree and collect registry + partition map.

    Returns a `(registry, partition_map)` pair:

    * `registry` keys every feature by its `ENTRY_POINT` value.
    * `partition_map` keys partitioned features by entry-point, mapping
      to a Hive partition dict (e.g. `{"theme": "places", "type":
      "place"}`) for path construction. Features with no `PARTITIONS`
      data (empty dict) are omitted; the codegen only sets `PARTITIONS`
      when the data lake organizes the feature by Hive partitions.
      `type` is appended here from the module file name so consumers
      get a complete partition path without the codegen having to
      duplicate the type value.
    """
    registry: dict[str, ModelValidation] = {}
    partition_map: dict[str, dict[str, str]] = {}

    try:
        root = importlib.import_module(_GENERATED_ROOT)
    except ImportError:
        return registry, partition_map

    for name in _iter_generated_module_names(list(root.__path__)):
        module = importlib.import_module(name)
        entry_point = getattr(module, "ENTRY_POINT", None)
        validation = getattr(module, "MODEL_VALIDATION", None)
        if entry_point is None or validation is None:
            continue
        registry[entry_point] = validation
        partitions = getattr(module, "PARTITIONS", None) or {}
        if partitions:
            feature_type = name.rsplit(".", 1)[-1]
            partition_map[entry_point] = {**partitions, "type": feature_type}

    return registry, partition_map


REGISTRY, PARTITION_MAP = _walk()
