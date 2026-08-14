"""PySpark validation expressions for Overture Maps data."""

# pyspark is an optional extra (the `spark` extra): a bare install lets this
# package's console script and metadata resolve, but every submodule needs
# pyspark to do anything. Guard the import directly so a missing pyspark gives
# an actionable message; anything else this package imports surfaces its own
# error through the real imports below.
try:
    import pyspark  # noqa: F401
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "overture-schema-pyspark requires PySpark, which isn't installed. "
        "Install it with `pip install overture-schema-pyspark[spark]`, or run "
        "in an environment that already provides PySpark (e.g. a Spark cluster)."
    ) from e

from .check import Check, CheckShape
from .schema_check import SchemaMismatch, compare_schemas
from .validate import (
    ValidationResult,
    evaluate_checks,
    explain_errors,
    filter_errors,
    model_keys,
    model_names,
    validate_model,
)

__all__ = [
    "Check",
    "CheckShape",
    "SchemaMismatch",
    "ValidationResult",
    "compare_schemas",
    "evaluate_checks",
    "explain_errors",
    "model_keys",
    "model_names",
    "filter_errors",
    "validate_model",
]
