"""Check dataclass — interface between expression builders and composition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from pyspark.sql import Column
from pyspark.sql.types import StructType

from overture.schema.system.primitive import GeometryType


class CheckShape(Enum):
    """How the composition layer handles a check expression."""

    SCALAR = "scalar"  # expression returns nullable string
    ARRAY = "array"  # expression returns array<string>


@dataclass(frozen=True)
class Check:
    """One validation check.

    `field` identifies what the check is about (for error column naming
    and report grouping), not how to access the data.  The expression in
    `expr` already encodes the access pattern.

    `root_field` is the top-level schema column the check belongs to,
    or None for synthetic model-level checks (radio_group, require_any_of)
    that don't correspond to a single column.  Used by `validate_feature`
    to suppress or skip checks by column name.
    """

    field: str
    name: str
    expr: Column
    shape: CheckShape
    root_field: str | None


@dataclass(frozen=True)
class FeatureValidation:
    """Pairs an expected schema with check builders for a feature type."""

    schema: StructType
    checks: Callable[[], list[Check]]
    geometry_types: tuple[GeometryType, ...] = ()
