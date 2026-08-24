"""The PySpark version floor this package declares, checked at import time."""

import importlib.metadata

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

# The distribution this module ships in. A name that stopped resolving would
# disable the check below in silence -- no floor found reads exactly like a
# floor satisfied -- so a test pins that this one finds real metadata.
_DISTRIBUTION = "overture-schema-pyspark"


def declared_pyspark_specifier() -> SpecifierSet | None:
    """Return the PySpark version range this package declares, if readable.

    The range lives in pyproject.toml (`pyspark>=N` on the `spark` extra) and
    reaches the installed distribution as a `Requires-Dist` entry. Reading it
    back from there rather than restating it here means one declaration, so a
    check against it cannot drift from what the package actually requires.

    Returns None when the metadata isn't installed -- a source tree run
    without an install -- because there is then no declaration to enforce.
    """
    try:
        declared = importlib.metadata.requires(_DISTRIBUTION) or ()
    except importlib.metadata.PackageNotFoundError:
        return None
    for raw in declared:
        requirement = Requirement(raw)
        if canonicalize_name(requirement.name) == "pyspark":
            return requirement.specifier
    return None


def pyspark_version_problem(version: str | None) -> str | None:
    """Describe how `version` falls outside the declared range, or None.

    Installing without the `spark` extra is the case the extra exists for --
    a runtime that provides its own PySpark -- and it is also the case no
    resolver sees, so nothing enforces the range at install time. This is
    where it gets enforced instead.

    `version` is `pyspark.__version__` rather than the version recorded in
    PySpark's own metadata, because a PySpark supplied by a Spark
    distribution is on `sys.path` without a `dist-info` directory to read.
    A PySpark that reports no version passes: unjudgeable is not out of range.
    """
    specifier = declared_pyspark_specifier()
    if version is None or specifier is None:
        return None
    # Prereleases count: Spark ships release candidates and dev builds, and a
    # `>=` floor is a statement about the release they belong to.
    if specifier.contains(version, prereleases=True):
        return None
    return (
        f"overture-schema-pyspark requires PySpark {specifier}, but PySpark "
        f"{version} is installed. Upgrade the PySpark in this environment, or "
        f"install this package with its extra (`pip install "
        f"overture-schema-pyspark[spark]`) to let the resolver choose one."
    )
