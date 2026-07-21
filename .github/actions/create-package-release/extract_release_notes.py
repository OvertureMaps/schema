#!/usr/bin/env python3

"""
Extract one package's release notes from its CHANGELOG.md.

Run by the `Release trigger` workflow. Prints the changelog section for the
given version (the block from `## [<version>]` up to the next `## [` heading,
stripped). Prints nothing if the changelog or the section is absent, so the
caller can fall back to a default message.

Usage:
    extract_release_notes.py <version> <changelog-path>
"""

from pathlib import Path
import sys


def extract(version: str, changelog: str) -> str:
    """Return the trimmed `## [<version>]` section, or "" if not found."""
    path = Path(changelog)
    if not path.is_file():
        return ""

    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(f"## [{version}]")),
        None,
    )
    if start is None:
        return ""

    end = next(
        (j for j in range(start + 1, len(lines)) if lines[j].startswith("## [")),
        len(lines),
    )
    return "\n".join(lines[start:end]).strip()


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <version> <changelog-path>", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(extract(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    main()
