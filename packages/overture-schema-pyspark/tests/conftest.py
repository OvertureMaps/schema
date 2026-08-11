"""Shared pytest fixtures for overture-schema-pyspark tests."""

import atexit
import os
import shutil
import socket
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pyspark
import pytest
from pyspark.sql import SparkSession

# Tests must be hermetic against ambient Spark/JVM configuration: developers
# commonly have a system-wide Spark install or JVM flags exported for other
# projects, and any of these leaking into the test JVM changes -- or breaks --
# every session. Networking overrides such as SPARK_LOCAL_IP are deliberately
# left alone: those are set to make local sessions *work* (e.g. macOS/VPN
# hostname resolution).
for _var in (
    "PYSPARK_SUBMIT_ARGS",  # injects launcher/JVM flags, jars, even --master
    "SPARK_CONF_DIR",  # points at another install's spark-defaults.conf
    "HADOOP_CONF_DIR",  # redirects filesystem/cluster defaults
    "YARN_CONF_DIR",
    "JAVA_TOOL_OPTIONS",  # picked up unconditionally by every JVM
    "_JAVA_OPTIONS",
    "JDK_JAVA_OPTIONS",
):
    os.environ.pop(_var, None)
# Pin worker and driver Python to this interpreter (overriding, not
# setdefault): an exported PYSPARK_PYTHON pointing at a non-venv Python
# fails with pickle/version-mismatch errors inside executors.
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
# Pin Spark to the venv's bundled distribution: an ambient SPARK_HOME
# pointing at a system-wide Spark install would launch that JVM under this
# venv's PySpark client, and mismatched versions fail at session setup with
# opaque py4j "'JavaPackage' object is not callable" errors.
os.environ["SPARK_HOME"] = os.path.dirname(pyspark.__file__)


def _shimmed_java_home(java_home: Path) -> Path:
    """Mirror *java_home*, replacing bin/java with a flag-filtering wrapper.

    jdk4py ships a jlink-stripped runtime without jdk.incubator.vector
    (upstream declined to bundle it for size: atoti/jdk4py#95), while
    Spark 4.x passes --add-modules=jdk.incubator.vector to every JVM it
    launches -- and a JVM refuses to boot when an --add-modules target is
    missing. The module only enables vectorized BLAS, which Spark treats
    as optional at runtime, so the wrapper drops that one flag and execs
    the real java with everything else intact.
    """
    shim_home = Path(tempfile.mkdtemp(prefix="overture-pyspark-test-jdk-"))
    atexit.register(shutil.rmtree, shim_home, ignore_errors=True)
    for entry in java_home.iterdir():
        if entry.name != "bin":
            (shim_home / entry.name).symlink_to(entry)
    bin_dir = shim_home / "bin"
    bin_dir.mkdir()
    for entry in (java_home / "bin").iterdir():
        if entry.name != "java":
            (bin_dir / entry.name).symlink_to(entry)
    real_java = java_home / "bin" / "java"
    shim_java = bin_dir / "java"
    shim_java.write_text(
        "#!/bin/sh\n"
        "# Drop --add-modules=jdk.incubator.vector; see conftest.py.\n"
        "for arg do\n"
        "  shift\n"
        '  [ "$arg" = "--add-modules=jdk.incubator.vector" ] && continue\n'
        '  set -- "$@" "$arg"\n'
        "done\n"
        f'exec "{real_java}" "$@"\n'
    )
    shim_java.chmod(0o755)
    return shim_home


# Pin the JVM to the venv's bundled JDK (jdk4py, a dev dependency on the
# platforms that have wheels for it). On platforms without a wheel -- or
# when the dev group isn't installed -- fall back to the machine's Java.
# The shim wrapper is a POSIX shell script, so non-POSIX platforms also
# fall back.
try:
    import jdk4py
except ImportError:
    pass
else:
    if os.name == "posix":
        os.environ["JAVA_HOME"] = str(_shimmed_java_home(jdk4py.JAVA_HOME))


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
