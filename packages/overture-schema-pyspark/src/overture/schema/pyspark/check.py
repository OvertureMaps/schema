"""Check dataclass — interface between expression builders and composition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from pyspark.sql import Column
from pyspark.sql.types import StructType

from overture.schema.system.geometric import GeometryType


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

    `expr` and `read_columns` are two views of one computation, and each is
    a "column" in a different sense.  `read_columns` are real columns of the
    underlying schema model -- the top-level columns the check must read to
    evaluate.  There is always at least one; a model-level constraint that
    spans fields names several, plus any discriminator a variant gate reads.
    `expr` is a *virtual column*: it is not a column of the schema model but
    one synthesized by the generated validation machinery to hold the
    composed expression the Spark engine evaluates.  The two travel together
    because the builder knows the read-set as it composes `expr`; recording
    it is surer than recovering it from the finished `Column`.

    `validate_model` drops a check when any column in `read_columns` is
    skipped or structurally absent, so an unresolvable `F.col()` never
    reaches Spark; it also treats these as the columns a check can be
    suppressed by name.
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
