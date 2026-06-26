"""Registry registration helper for tests.

Provides a context manager that registers a model type in the runtime
`REGISTRY` and guarantees teardown on exit, even if the test body raises.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from overture.schema.pyspark._registry import REGISTRY
from overture.schema.pyspark.check import Check, ModelValidation
from pyspark.sql.types import StructType


@contextmanager
def register_model(
    model_type: str,
    schema: StructType,
    checks: Callable[[], list[Check]],
) -> Iterator[None]:
    """Register a model type in `REGISTRY` for the duration of a test.

    Removes `REGISTRY[model_type]` on exit so a failed test body never
    leaks an entry into sibling tests. Uses `pop(..., None)` so a body that
    already removed or rebound the key does not raise a `KeyError` that
    would mask the body's own exception.

    Parameters
    ----------
    model_type
        The registry key string (e.g. `"_test_cli"`).
    schema
        StructType to associate with the model type.
    checks
        Callable returning the list of `Check` objects for the model type.

    Yields
    ------
    None
    """
    REGISTRY[model_type] = ModelValidation(schema=schema, checks=checks)
    try:
        yield
    finally:
        REGISTRY.pop(model_type, None)
