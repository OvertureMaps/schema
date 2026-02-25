"""Map types to markdown output file paths.

Uses module-mirrored output directories: output paths derive from
the source Python module path relative to schema_root.
"""

from collections.abc import Sequence
from pathlib import PurePosixPath

from .case_conversion import slug_filename
from .module_layout import compute_output_dir, output_dir_for_entry_point
from .specs import FeatureSpec, SupplementarySpec

__all__ = [
    "GEOMETRY_PAGE",
    "PRIMITIVES_PAGE",
    "build_placement_registry",
    "resolve_output_path",
]

# Aggregate page paths.
PRIMITIVES_PAGE = PurePosixPath("system/primitive/primitives.md")
GEOMETRY_PAGE = PurePosixPath("system/primitive/geometry.md")


def build_placement_registry(
    feature_specs: Sequence[FeatureSpec],
    all_specs: dict[str, SupplementarySpec],
    primitive_names: list[str],
    geometry_names: list[str],
    schema_root: str,
) -> dict[str, PurePosixPath]:
    """Build a mapping from type names to output file paths.

    Uses module-mirrored output directories: output paths derive from
    the source Python module path relative to schema_root.
    """
    registry: dict[str, PurePosixPath] = _aggregate_page_entries(
        primitive_names, geometry_names
    )

    feature_dirs: set[PurePosixPath] = set()
    for spec in feature_specs:
        spec_dir = output_dir_for_entry_point(spec.entry_point, schema_root)
        registry[spec.name] = _md_path(spec_dir, spec.name)
        feature_dirs.add(spec_dir)

    for name, supp_spec in all_specs.items():
        if name in registry:
            continue
        source_module = getattr(supp_spec.source_type, "__module__", None)
        if source_module is None:
            continue
        output_dir = compute_output_dir(source_module, schema_root)
        output_dir = _nest_under_types(output_dir, feature_dirs)
        registry[name] = _md_path(output_dir, name)

    return registry


def resolve_output_path(
    type_name: str,
    registry: dict[str, PurePosixPath] | None,
) -> PurePosixPath:
    """Look up a type's output path from the registry, with flat-file fallback."""
    if registry is not None and type_name in registry:
        return registry[type_name]
    return PurePosixPath(slug_filename(type_name))


def _aggregate_page_entries(
    primitive_names: list[str],
    geometry_names: list[str],
) -> dict[str, PurePosixPath]:
    """Pre-populate registry entries for types documented on aggregate pages."""
    entries: dict[str, PurePosixPath] = dict.fromkeys(primitive_names, PRIMITIVES_PAGE)
    entries.update(dict.fromkeys(geometry_names, GEOMETRY_PAGE))
    return entries


def _nest_under_types(
    output_dir: PurePosixPath, feature_dirs: set[PurePosixPath]
) -> PurePosixPath:
    """Insert ``types/`` after the feature directory portion.

    If *output_dir* equals or is a subdirectory of a feature directory,
    returns a path with ``types/`` inserted after the feature directory.
    Otherwise returns *output_dir* unchanged.
    """
    for fd in sorted(feature_dirs, key=lambda p: len(p.parts), reverse=True):
        try:
            relative = output_dir.relative_to(fd)
        except ValueError:
            continue
        return fd / "types" / relative
    return output_dir


def _md_path(directory: PurePosixPath, name: str) -> PurePosixPath:
    """Build a .md file path from a directory and a PascalCase type name."""
    return directory / slug_filename(name)
