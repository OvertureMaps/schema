"""Runtime registry of feature validations.

Built at import time by walking the generated `expressions.generated`
namespace and collecting every module that exposes the
codegen-emitted `ENTRY_POINT` and `MODEL_VALIDATION` constants.

The generated tree is the runtime source of truth: the registry
contains exactly what was generated, regardless of which theme
packages are installed alongside the pyspark package. A missing
`expressions/generated/` subtree simply yields an empty registry --
the package still imports cleanly.

The tree is read through `importlib.resources`, which resolves a
namespace portion whether it is a directory on disk or a member of an
archive. A wheel placed straight on `sys.path` is zipimported rather
than installed -- AWS Glue does this with `--extra-py-files` -- and
`pathlib` cannot traverse into one.
"""

from __future__ import annotations

import importlib
import logging
import sys
from collections.abc import Iterator

if sys.version_info >= (3, 13):
    from importlib.resources import files
    from importlib.resources.abc import Traversable
else:
    # `importlib.resources.files` raises `NotADirectoryError` for a namespace
    # package with any non-directory portion through Python 3.12; the backport
    # carries the 3.13 fix. AWS Glue 4.0 runs Python 3.10 and Glue 5.0 runs
    # 3.11, so on Glue this is always the branch taken.
    from importlib_resources import files
    from importlib_resources.abc import Traversable

from .check import ModelValidation

logger = logging.getLogger(__name__)

_GENERATED_ROOT = "overture.schema.pyspark.expressions.generated"


def _iter_generated_module_names(root: str = _GENERATED_ROOT) -> list[str]:
    """Return the dotted names of every generated module under `root`.

    The generated tree is PEP 420 (no `__init__.py`), so its subdirectories
    are namespace packages, which `pkgutil.walk_packages` skips. It is walked
    as resources instead: every `.py` below `root`, keyed to a dotted name.
    `files` multiplexes every portion of the namespace, so a tree assembled
    from more than one distribution is walked whole.
    """

    def walk(node: Traversable, prefix: tuple[str, ...]) -> Iterator[str]:
        for child in node.iterdir():
            if child.is_dir():
                yield from walk(child, (*prefix, child.name))
            elif child.name.endswith(".py") and child.name != "__init__.py":
                yield ".".join([root, *prefix, child.name[: -len(".py")]])

    try:
        anchor = files(root)
    except ModuleNotFoundError:
        return []
    return sorted(walk(anchor, ()))


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

    for name in _iter_generated_module_names():
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
