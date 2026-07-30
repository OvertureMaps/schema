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
from pathlib import Path

from .check import ModelValidation

logger = logging.getLogger(__name__)

_GENERATED_ROOT = "overture.schema.pyspark.expressions.generated"


def _iter_generated_module_names(root_paths: list[str]) -> list[str]:
    """Return the dotted names of every generated module on disk.

    The generated tree is PEP 420 (no `__init__.py`), so its subdirectories
    are namespace packages. `pkgutil.walk_packages` skips those, so the tree
    is walked as files instead: every `.py` under the namespace roots, keyed
    to a dotted name relative to `_GENERATED_ROOT`.
    """
    names: list[str] = []
    for root_path in root_paths:
        base = Path(root_path)
        for path in sorted(base.rglob("*.py")):
            if path.name == "__init__.py":
                continue
            relative = path.relative_to(base).with_suffix("")
            names.append(".".join([_GENERATED_ROOT, *relative.parts]))
    return names


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
