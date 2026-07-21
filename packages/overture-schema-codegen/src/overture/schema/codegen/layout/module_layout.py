"""Output directory layout from Python module paths.

Translates dotted module paths into output directory paths by mirroring
the source package structure.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Mapping
from pathlib import PurePosixPath

from overture.schema.system.discovery import split_entry_point

__all__ = [
    "OUTPUT_ROOT",
    "compute_output_dir",
    "compute_schema_root",
    "entry_point_class",
    "entry_point_module",
    "is_package_module",
    "module_relpath",
    "output_dir_for_entry_point",
]

OUTPUT_ROOT = PurePosixPath(".")


def entry_point_module(entry_point_path: str) -> str:
    """Extract module path from entry-point-style path.

    >>> entry_point_module("overture.schema.buildings:Building")
    'overture.schema.buildings'
    """
    return split_entry_point(entry_point_path)[0]


def entry_point_class(entry_point_path: str) -> str:
    """Extract class name from entry-point-style path.

    >>> entry_point_class("overture.schema.buildings:Building")
    'Building'
    """
    return split_entry_point(entry_point_path)[1]


def compute_schema_root(module_paths: Iterable[str]) -> str:
    """Find the longest common dotted prefix of module paths.

    Deduplicates inputs first. For a single unique path, drops the
    last component (the module itself).
    """
    paths = sorted(set(module_paths))
    if not paths:
        msg = "No module paths provided"
        raise ValueError(msg)

    segments = [p.split(".") for p in paths]
    if len(segments) == 1:
        return ".".join(segments[0][:-1])

    common: list[str] = []
    for parts in zip(*segments, strict=False):
        if len(set(parts)) == 1:
            common.append(parts[0])
        else:
            break
    return ".".join(common)


def module_relpath(module: str, root: str) -> str:
    """Strip the schema root prefix from a dotted module path."""
    if not root:
        return module
    if module == root:
        return ""
    prefix = root + "."
    if not module.startswith(prefix):
        msg = f"Module {module!r} does not start with root {root!r}"
        raise ValueError(msg)
    return module[len(prefix) :]


def is_package_module(
    module: str,
    module_registry: Mapping[str, object] | None = None,
) -> bool:
    """Check whether a module is a package (directory) or a file module.

    Packages have `__path__`; file modules do not (PEP 302).
    """
    registry: Mapping[str, object] = (
        module_registry if module_registry is not None else sys.modules
    )
    mod = registry.get(module)
    if mod is None:
        msg = f"Module {module!r} not found in registry"
        raise ValueError(msg)
    return hasattr(mod, "__path__")


def output_dir_for_entry_point(
    entry_point_path: str | None,
    schema_root: str,
    module_registry: Mapping[str, object] | None = None,
) -> PurePosixPath:
    """Compute output directory from an entry-point-style path.

    Raises ValueError if *entry_point_path* is None.
    """
    if entry_point_path is None:
        msg = "entry_point_path must not be None"
        raise ValueError(msg)
    module = entry_point_module(entry_point_path)
    return compute_output_dir(module, schema_root, module_registry)


def compute_output_dir(
    module: str,
    schema_root: str,
    module_registry: Mapping[str, object] | None = None,
) -> PurePosixPath:
    """Compute output directory for a module, mirroring package structure.

    File modules drop their last component (the .py filename).
    Packages keep all components. Returns `PurePosixPath(".")` for
    the root directory.
    """
    relpath = module_relpath(module, schema_root)
    if not relpath:
        return OUTPUT_ROOT

    parts = relpath.split(".")
    if not is_package_module(module, module_registry):
        parts = parts[:-1]

    if not parts:
        return OUTPUT_ROOT
    return PurePosixPath(*parts)
