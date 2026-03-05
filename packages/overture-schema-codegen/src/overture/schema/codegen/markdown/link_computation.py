"""Relative link computation between rendered output files."""

from dataclasses import dataclass
from pathlib import PurePosixPath

from ..extraction.case_conversion import slug_filename
from ..extraction.specs import TypeIdentity

__all__ = ["LinkContext", "relative_link"]


@dataclass
class LinkContext:
    """Placement context for resolving cross-directory markdown links."""

    page_path: PurePosixPath
    registry: dict[TypeIdentity, PurePosixPath]

    def resolve_link(self, identity: TypeIdentity) -> str | None:
        """Resolve *identity* to a relative link if it exists in the registry."""
        if identity in self.registry:
            return relative_link(self.page_path, self.registry[identity])
        return None

    def resolve_link_or_slug(self, identity: TypeIdentity) -> str:
        """Resolve *identity* to a relative link, falling back to a slug filename.

        Always returns a usable link string. Use when the caller needs a
        link regardless of whether the type has a registered page.
        """
        return self.resolve_link(identity) or slug_filename(identity.name)


def _is_normalized(path: PurePosixPath) -> bool:
    """Check whether the path contains no '..' or '.' components (except root '.')."""
    return ".." not in path.parts and path.parts.count(".") <= 1


def relative_link(source: PurePosixPath, target: PurePosixPath) -> str:
    """Compute a relative path from source file to target file.

    Both paths must be normalized (no ``..`` components) and relative
    to the same output root.
    """
    if not _is_normalized(source):
        msg = f"Source path not normalized: {source}"
        raise ValueError(msg)
    if not _is_normalized(target):
        msg = f"Target path not normalized: {target}"
        raise ValueError(msg)
    source_dir = source.parent
    # Count how many levels up from source_dir to common ancestor,
    # then descend to target. PurePosixPath doesn't have os.path.relpath,
    # so compute manually.
    source_parts = source_dir.parts
    target_parts = target.parts

    # Find common prefix length
    common = 0
    for s, t in zip(source_parts, target_parts, strict=False):
        if s != t:
            break
        common += 1

    ups = len(source_parts) - common
    downs = target_parts[common:]

    parts = [".."] * ups + list(downs)
    return "/".join(parts) if parts else "."
