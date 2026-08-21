"""Runtime registry of feature validations.

Built at import time from the generated `_index` module, which imports every
generated validation module and exposes them as `MODULES`. That import is
ordinary, so the registry populates whether the package is installed to a real
directory or loaded straight from a wheel on `sys.path` (as on Glue, via
`--extra-py-files`); discovery never walks the generated tree as files.

A build without the generated tree has no `_index` module, so the registry is
empty and the package still imports cleanly. A module that is present but fails
to import (a missing dependency, a codegen bug) raises, so a real breakage is
loud and a validation is never dropped without notice.
"""

from __future__ import annotations

import importlib
import logging

from .check import ModelValidation

logger = logging.getLogger(__name__)

_INDEX_MODULE = "overture.schema.pyspark.expressions.generated._index"


def _walk() -> tuple[dict[str, ModelValidation], dict[str, dict[str, str]]]:
    """Collect registry + partition map from the generated index.

    Returns a `(registry, partition_map)` pair:

    * `registry` keys every feature by its `ENTRY_POINT` value.
    * `partition_map` keys partitioned features by entry-point, mapping
      to a Hive partition dict (e.g. `{"theme": "places", "type":
      "place"}`) for path construction. Features with no `PARTITIONS`
      data (empty dict) are omitted; the codegen only sets `PARTITIONS`
      when the data lake organizes the feature by Hive partitions.
      `type` comes from the module name so consumers get a complete
      partition path without the codegen having to duplicate the value.
    """
    registry: dict[str, ModelValidation] = {}
    partition_map: dict[str, dict[str, str]] = {}

    try:
        index = importlib.import_module(_INDEX_MODULE)
    except ModuleNotFoundError as e:
        missing = e.name or ""
        # A missing name equal to (or an ancestor of) the index module means
        # the generated tree was never built, which is a legitimately empty
        # registry. Any other missing name is a real dependency failure while
        # importing a module the index references, so let it propagate.
        if missing == _INDEX_MODULE or _INDEX_MODULE.startswith(f"{missing}."):
            return registry, partition_map
        raise

    for module in index.MODULES:
        entry_point = getattr(module, "ENTRY_POINT", None)
        validation = getattr(module, "MODEL_VALIDATION", None)
        if entry_point is None or validation is None:
            continue
        registry[entry_point] = validation
        partitions = getattr(module, "PARTITIONS", None) or {}
        if partitions:
            feature_type = module.__name__.rsplit(".", 1)[-1]
            partition_map[entry_point] = {**partitions, "type": feature_type}

    return registry, partition_map


REGISTRY, PARTITION_MAP = _walk()
