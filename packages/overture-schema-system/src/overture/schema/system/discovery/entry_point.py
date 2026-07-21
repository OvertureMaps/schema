"""Entry-point string utilities."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath

from ..case import to_snake_case

__all__ = [
    "entry_point_class_alias",
    "entry_point_to_path",
    "resolve_entry_point_key",
    "split_entry_point",
]


def split_entry_point(entry_point_path: str) -> tuple[str, str]:
    """Split `"module.path:ClassName"` into dotted module and class name.

    >>> split_entry_point("overture.schema.buildings:Building")
    ('overture.schema.buildings', 'Building')
    """
    if ":" not in entry_point_path:
        msg = f"Expected 'module:Class' format, got {entry_point_path!r}"
        raise ValueError(msg)
    module, cls = entry_point_path.split(":", 1)
    return module, cls


def entry_point_to_path(entry_point_path: str) -> tuple[PurePosixPath, str]:
    """Translate an entry-point string into a directory path and class name.

    Each dotted component of the module becomes a directory, mirroring
    the source package structure. The result is stable regardless of the
    set of installed packages.

    Parameters
    ----------
    entry_point_path
        String in `"module.path:ClassName"` form.

    Returns
    -------
    tuple[PurePosixPath, str]
        Directory derived from the module path, and the class name.

    Examples
    --------
    >>> entry_point_to_path("overture.schema.places:Place")
    (PurePosixPath('overture/schema/places'), 'Place')
    """
    module, cls = split_entry_point(entry_point_path)
    return PurePosixPath(*module.split(".")), cls


def entry_point_class_alias(entry_point_path: str) -> str:
    """Snake-case class name from an entry-point string.

    The alias is the user-friendly form used to look up entry-point
    keys in a registry (e.g. `"place"` resolves
    `"overture.schema.places:Place"`). Input without a colon is treated
    as a bare class name and snake-cased directly, so the function is
    safe to apply to every key in an arbitrary registry mapping.

    Parameters
    ----------
    entry_point_path
        String in `"module.path:ClassName"` form, or a bare name.

    Examples
    --------
    >>> entry_point_class_alias("overture.schema.divisions:DivisionArea")
    'division_area'
    """
    cls = entry_point_path.rsplit(":", 1)[-1]
    return to_snake_case(cls)


def resolve_entry_point_key(name: str, registry: Mapping[str, object]) -> str:
    """Resolve a user-supplied name to a canonical entry-point key.

    Tries exact match first, then snake-case class-name alias. Raises
    `ValueError` when the alias is ambiguous (matches more than one
    registered key) or when the name is unknown.

    Parameters
    ----------
    name
        User-supplied identifier: an entry-point key or a snake-case
        class-name alias.
    registry
        Mapping whose keys are entry-point strings.

    Returns
    -------
    str
        The canonical registry key.

    Raises
    ------
    ValueError
        If `name` matches multiple registry entries via alias, or no
        registry entry at all. The message lists the candidates or the
        known keys to aid recovery.
    """
    if name in registry:
        return name
    candidates = sorted(k for k in registry if entry_point_class_alias(k) == name)
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        raise ValueError(
            f"Entry-point alias {name!r} is ambiguous. "
            f"Specify one of: {', '.join(candidates)}"
        )
    raise ValueError(
        f"Unknown entry-point alias {name!r}. Known: {', '.join(sorted(registry))}"
    )
