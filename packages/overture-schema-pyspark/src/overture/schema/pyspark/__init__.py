"""PySpark validation expressions for Overture Maps data."""

import importlib.util

from ._pyspark_version import pyspark_version_problem

# pyspark is an optional extra (the `spark` extra): a bare install lets this
# package's metadata and console script resolve, but every module below needs
# pyspark itself to do anything. Probe for it here -- this module runs on any
# import of any submodule -- so a bare install gets an actionable message. A
# pyspark that is present but broken still raises its own error, because the
# imports below run for real.
if importlib.util.find_spec("pyspark") is None:
    raise ModuleNotFoundError(
        "overture-schema-pyspark requires PySpark, which isn't installed. "
        "Install it with `pip install overture-schema-pyspark[spark]`, or run "
        "in an environment that already provides PySpark (e.g. a Spark cluster)."
    )

import pyspark

# Installing without the extra leaves no resolver to enforce the version floor
# declared alongside it, so enforce it here, against the PySpark that actually
# turned up. The floor is read back out of this package's own metadata.
if _problem := pyspark_version_problem(getattr(pyspark, "__version__", None)):
    raise ImportError(_problem)

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
