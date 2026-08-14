"""Runtime registry of feature validations.

Built at import time from this package's `overture.pyspark_validations`
entry points, one per generated validation module. Reading them through
`importlib.metadata` resolves the same whether the package is installed to a
real directory or loaded straight from a wheel on `sys.path` (as on Glue, via
`--extra-py-files`), so discovery does not depend on the generated tree being
reachable as filesystem paths.

An entry point whose module is simply absent -- a build without the generated
tree, or a stale declaration -- is skipped, so a package missing its generated
modules still imports cleanly with an empty registry. A module that is present
but fails to import (a missing dependency, a codegen bug) raises, rather than
silently dropping that validation.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging

from .check import ModelValidation

logger = logging.getLogger(__name__)

_ENTRY_POINT_GROUP = "overture.pyspark_validations"
_DIST_NAME = "overture-schema-pyspark"


def _canonical(name: str) -> str:
    """Normalize a distribution name for comparison (PEP 503)."""
    return name.replace("_", "-").lower()


def _own_entry_points() -> list[importlib.metadata.EntryPoint]:
    """Return this distribution's own validation entry points.

    `importlib.metadata.entry_points(group=...)` returns matching entry points
    from every installed distribution. Filtering to this one keeps a foreign
    package that happens to declare the same group from injecting validations.
    """
    return [
        ep
        for ep in importlib.metadata.entry_points(group=_ENTRY_POINT_GROUP)
        if _canonical(getattr(ep.dist, "name", "") or "") == _DIST_NAME
    ]


def _walk() -> tuple[dict[str, ModelValidation], dict[str, dict[str, str]]]:
    """Collect registry + partition map from the validation entry points.

    Returns a `(registry, partition_map)` pair:

    * `registry` keys every feature by its `ENTRY_POINT` value.
    * `partition_map` keys partitioned features by entry-point, mapping
      to a Hive partition dict (e.g. `{"theme": "places", "type":
      "place"}`) for path construction. Features with no `PARTITIONS`
      data (empty dict) are omitted; the codegen only sets `PARTITIONS`
      when the data lake organizes the feature by Hive partitions.
      `type` comes from the entry-point name so consumers get a complete
      partition path without the codegen having to duplicate the value.
    """
    registry: dict[str, ModelValidation] = {}
    partition_map: dict[str, dict[str, str]] = {}

    for ep in _own_entry_points():
        try:
            module = importlib.import_module(ep.module)
        except ModuleNotFoundError as e:
            missing = e.name or ""
            # Skip only when the generated module itself (or an ancestor
            # namespace of it) is absent -- a build without the generated tree.
            # A dependency missing *inside* a module that is present is a real
            # failure; re-raise it instead of silently dropping the validation.
            if missing == ep.module or ep.module.startswith(f"{missing}."):
                continue
            raise
        entry_point = getattr(module, "ENTRY_POINT", None)
        validation = getattr(module, "MODEL_VALIDATION", None)
        if entry_point is None or validation is None:
            continue
        registry[entry_point] = validation
        partitions = getattr(module, "PARTITIONS", None) or {}
        if partitions:
            partition_map[entry_point] = {**partitions, "type": ep.name}

    return registry, partition_map


REGISTRY, PARTITION_MAP = _walk()
