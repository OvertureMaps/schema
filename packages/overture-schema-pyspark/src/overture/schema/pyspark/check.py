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

    `read_columns` names every top-level schema column the expression
    dereferences -- one for a plain field check, several for a model-level
    check that spans columns, plus any discriminator a variant gate reads.
    `validate_model` drops a check when any column it reads is skipped or
    structurally absent, so an unresolvable `F.col()` never reaches Spark;
    it also treats these as the columns a check can be suppressed by name.
    """

    field: str
    name: str
    expr: Column
    shape: CheckShape
    read_columns: frozenset[str]


@dataclass(frozen=True)
class ModelValidation:
    """Pairs an expected schema with check builders for a feature type."""

    schema: StructType
    checks: Callable[[], list[Check]]
    geometry_types: tuple[GeometryType, ...] = ()
