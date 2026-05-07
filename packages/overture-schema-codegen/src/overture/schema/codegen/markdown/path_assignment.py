"""Map types to markdown output file paths.

Uses module-mirrored output directories: output paths derive from
the source Python module path relative to schema_root.
"""

from collections.abc import Sequence
from pathlib import PurePosixPath

from overture.schema.system.case import to_snake_case

from ..extraction.specs import (
    FeatureSpec,
    PydanticTypeSpec,
    SupplementarySpec,
    TypeIdentity,
)
from ..layout.module_layout import compute_output_dir, output_dir_for_entry_point

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
    all_specs: dict[TypeIdentity, SupplementarySpec],
    numeric_names: list[TypeIdentity],
    geometry_names: list[TypeIdentity],
    schema_root: str,
) -> dict[TypeIdentity, PurePosixPath]:
    """Build a mapping from TypeIdentity to output file paths.

    Uses module-mirrored output directories: output paths derive from
    the source Python module path relative to schema_root.
    """
    registry: dict[TypeIdentity, PurePosixPath] = _aggregate_page_entries(
        numeric_names, geometry_names
    )

    feature_dirs: set[PurePosixPath] = set()
    for spec in feature_specs:
        spec_dir = output_dir_for_entry_point(spec.entry_point, schema_root)
        registry[spec.identity] = _md_path(spec_dir, spec.name)
        feature_dirs.add(spec_dir)

    for tid, supp_spec in all_specs.items():
        if tid in registry:
            continue
        if isinstance(supp_spec, PydanticTypeSpec):
            registry[tid] = _md_path(
                PurePosixPath("pydantic") / supp_spec.source_module, tid.name
            )
            continue
        source_module = getattr(supp_spec.source_type, "__module__", None)
        if source_module is None:
            continue
        output_dir = compute_output_dir(source_module, schema_root)
        output_dir = _nest_under_types(output_dir, feature_dirs)
        registry[tid] = _md_path(output_dir, tid.name)

    return registry


def resolve_output_path(
    identity: TypeIdentity,
    registry: dict[TypeIdentity, PurePosixPath] | None,
) -> PurePosixPath:
    """Look up a type's output path from the registry, with flat-file fallback."""
    if registry is not None and identity in registry:
        return registry[identity]
    return _md_path(PurePosixPath(""), identity.name)


def _aggregate_page_entries(
    numeric_names: list[TypeIdentity],
    geometry_names: list[TypeIdentity],
) -> dict[TypeIdentity, PurePosixPath]:
    """Pre-populate registry entries for types documented on aggregate pages."""
    entries: dict[TypeIdentity, PurePosixPath] = dict.fromkeys(
        numeric_names, PRIMITIVES_PAGE
    )
    entries.update(dict.fromkeys(geometry_names, GEOMETRY_PAGE))
    return entries


def _nest_under_types(
    output_dir: PurePosixPath, feature_dirs: set[PurePosixPath]
) -> PurePosixPath:
    """Insert `types/` after the feature directory portion.

    If *output_dir* equals or is a subdirectory of a feature directory,
    returns a path with `types/` inserted after the feature directory.
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
    return directory / f"{to_snake_case(name)}.md"
