"""PySpark validation expressions for Overture Maps data."""

try:
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
except ModuleNotFoundError as e:
    # pyspark is an optional extra (the `spark` extra): a bare install lets
    # this package's console script and metadata resolve, but every submodule
    # needs pyspark itself to do anything. Narrow to exactly that case so a
    # genuinely broken pyspark install (or an unrelated missing module) still
    # raises its own real error instead of this actionable one.
    if e.name == "pyspark" or (e.name or "").startswith("pyspark."):
        raise ModuleNotFoundError(
            "overture-schema-pyspark requires PySpark, which isn't installed. "
            "Install it with `pip install overture-schema-pyspark[spark]`, or run "
            "in an environment that already provides PySpark (e.g. a Spark cluster)."
        ) from e
    raise

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
