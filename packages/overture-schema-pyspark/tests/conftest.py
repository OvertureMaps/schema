"""Shared pytest fixtures for overture-schema-pyspark tests."""

import os
import socket
import sys
from collections.abc import Callable
from typing import Any

import pytest
from pyspark.sql import SparkSession

# Ensure PySpark workers use the same Python as the driver to avoid
# version mismatch errors when a different system Python is on PATH.
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)


def pytest_configure(config: pytest.Config) -> None:
    """Suppress ResourceWarning from PySpark's unclosed py4j sockets.

    PySpark uses py4j to communicate with the JVM. py4j socket proxies
    are GC'd between tests and their __del__ fires ResourceWarning via
    sys.unraisablehook. With -W error this becomes a test failure.

    The original hook is preserved for all other unraisable exceptions.
    """
    original_hook: Callable[[Any], None] = sys.unraisablehook

    def _hook(unraisable: Any) -> None:
        if isinstance(unraisable.exc_value, ResourceWarning) and isinstance(
            unraisable.object, socket.socket
        ):
            return
        original_hook(unraisable)

    sys.unraisablehook = _hook


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    """Provide a local SparkSession for testing."""
    session = (
        SparkSession.builder.master("local[1]")
        .appName("overture-pyspark-tests")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    return session
