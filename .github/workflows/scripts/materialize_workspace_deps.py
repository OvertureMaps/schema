#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "tomlkit>=0.13",
# ]
# ///

"""
Materialize workspace dependency versions into a package's pyproject.toml.

Run from the repository root, before building a package for publishing:

    uv run ./.github/workflows/scripts/materialize_workspace_deps.py <package>

Intra-repo dependencies are declared as bare names (e.g. "overture-schema-common")
and resolved at dev time through `[tool.uv.sources]` workspace entries. Built
distributions carry the declared metadata as-is, so without this step a published
wheel would depend on an unconstrained package name. uv has no first-class
feature for this (workspace sources are dev-only and dropped at build time).

For each dependency that names a workspace member, this script rewrites the
bare name to a floor constraint from the version currently in the repo, e.g.
"overture-schema-common" becomes "overture-schema-common>=0.1.1". The floor is
the released version only; internal `.postN` build suffixes are never written
into dependency constraints. Edits preserve pyproject.toml formatting.

Dependencies that already carry a constraint, and dependencies on packages
outside this repo, are left untouched.

Exit status:
    0  Success (including nothing-to-do).
    1  Unknown package, or a workspace dependency's pyproject cannot be read.
"""

from pathlib import Path
import re
import sys

import tomlkit

PACKAGES_DIR = Path("packages")

# A bare PEP 508 name: no extras, no specifier, no markers.
BARE_NAME = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$")

VERSION_ASSIGNMENT = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.MULTILINE)


def dynamic_version(package_dir: Path, doc: tomlkit.TOMLDocument) -> str:
    """Resolve a hatch dynamic version from its declared version file."""
    version_path = str(doc["tool"]["hatch"]["version"]["path"])
    content = (package_dir / version_path).read_text(encoding="utf-8")
    match = VERSION_ASSIGNMENT.search(content)
    if not match:
        raise ValueError(f"No __version__ assignment in {package_dir / version_path}")
    return match.group(1)


def workspace_versions() -> dict[str, str]:
    """Map every workspace member's distribution name to its in-repo version."""
    versions: dict[str, str] = {}
    for path in sorted(PACKAGES_DIR.glob("*/pyproject.toml")):
        doc = tomlkit.parse(path.read_text(encoding="utf-8"))
        project = doc["project"]
        if "version" in project:
            version = str(project["version"])
        else:
            version = dynamic_version(path.parent, doc)
        versions[str(project["name"])] = version
    return versions


def materialize(package: str) -> int:
    pyproject_path = PACKAGES_DIR / package / "pyproject.toml"
    if not pyproject_path.is_file():
        print(f"::error::No such package: {package} ({pyproject_path} missing).")
        return 1

    versions = workspace_versions()
    doc = tomlkit.parse(pyproject_path.read_text(encoding="utf-8"))
    dependencies = doc["project"].get("dependencies", [])

    changed = 0
    for i, dep in enumerate(dependencies):
        name = str(dep).strip()
        if not BARE_NAME.match(name) or name not in versions:
            continue
        floor = f"{name}>={versions[name]}"
        dependencies[i] = floor
        changed += 1
        print(f"{package}: {name} -> {floor}")

    if changed:
        pyproject_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
        print(f"{package}: materialized {changed} workspace dependenc{'y' if changed == 1 else 'ies'}.")
    else:
        print(f"{package}: no bare workspace dependencies to materialize.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: materialize_workspace_deps.py <package>", file=sys.stderr)
        sys.exit(1)
    sys.exit(materialize(sys.argv[1]))
