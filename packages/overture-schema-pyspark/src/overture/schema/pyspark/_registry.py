"""Runtime registry of feature validations.

Built at import time from the `overture.pyspark_validations` entry points,
one per generated validation module, declared by this package. Reading them
through `importlib.metadata` resolves the same whether the package is
installed to a real directory or loaded straight from a wheel on `sys.path`
(as on Glue, via `--extra-py-files`), so discovery does not depend on the
generated tree being reachable as filesystem paths.

An entry point whose module is absent -- a build without the generated tree,
or a stale declaration -- is skipped, so a package missing its generated
modules still imports cleanly with an empty registry.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging

from .check import ModelValidation

logger = logging.getLogger(__name__)

_ENTRY_POINT_GROUP = "overture.pyspark_validations"


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

    for ep in importlib.metadata.entry_points(group=_ENTRY_POINT_GROUP):
        try:
            module = importlib.import_module(ep.module)
        except ModuleNotFoundError:
            continue
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
