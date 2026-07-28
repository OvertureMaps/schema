#!/usr/bin/env python3

"""
Diff per-package versions between two git commits.

Run from the repository root:

    python3 package_versions.py diff <before-commit> <after-commit>

Reads each `packages/*/pyproject.toml` blob directly from git at both commits
(no checkout switching, no environment sync) and prints the packages whose
version changed as a JSON array, topologically sorted so that packages with no
changed dependencies come first. The dependency order is derived from each
package's declared `project.dependencies`, restricted to workspace members.

Form of the JSON array:

    [ {"package": "p1", "before": "v1", "after": "v2"}, ... ]

`before` is null if the package did not exist at the before commit; `after` is
null if it no longer exists at the after commit.

Exit status:
    0  Success.
    1  Usage error.
"""

from graphlib import TopologicalSorter
import json
import re
import subprocess
import sys
import tomllib

PACKAGES_DIR = "packages"

# The distribution name at the start of a PEP 508 requirement string.
REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)")


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, check=True)
    return result.stdout.decode("utf-8")


def package_manifests(commit: str) -> dict[str, dict]:
    """Map package directory name -> parsed pyproject.toml at `commit`."""
    try:
        listing = git("ls-tree", "--name-only", commit, f"{PACKAGES_DIR}/")
    except subprocess.CalledProcessError:
        return {}  # commit unreadable (force-push) or no packages dir yet

    manifests: dict[str, dict] = {}
    for line in listing.splitlines():
        package = line.removeprefix(f"{PACKAGES_DIR}/")
        try:
            blob = git("show", f"{commit}:{PACKAGES_DIR}/{package}/pyproject.toml")
        except subprocess.CalledProcessError:
            continue  # not a package directory
        manifests[package] = tomllib.loads(blob)
    return manifests


def topo_order(manifests: dict[str, dict]) -> list[str]:
    """Package names sorted so dependencies come before their dependents."""
    dist_to_dir = {
        str(m["project"]["name"]): package for package, m in manifests.items()
    }
    graph: dict[str, set[str]] = {}
    for package, manifest in manifests.items():
        deps = set()
        for requirement in manifest["project"].get("dependencies", []):
            match = REQUIREMENT_NAME.match(str(requirement))
            if match and match.group(1) in dist_to_dir:
                deps.add(dist_to_dir[match.group(1)])
        graph[package] = deps
    return list(TopologicalSorter(graph).static_order())


def diff(before: str, after: str) -> None:
    before_manifests = package_manifests(before)
    after_manifests = package_manifests(after)

    def version(manifests: dict[str, dict], package: str) -> str | None:
        manifest = manifests.get(package)
        if manifest is None:
            return None
        # A dynamic version (no static `project.version`) also maps to None.
        value = manifest["project"].get("version")
        return str(value) if value is not None else None

    # Order from the after commit, which knows about newly added packages;
    # packages that only exist in before (deleted) are appended at the end.
    order = topo_order(after_manifests)
    order += sorted(set(before_manifests) - set(after_manifests))

    changed = [
        {"package": p, "before": b, "after": a}
        for p in order
        if (b := version(before_manifests, p)) != (a := version(after_manifests, p))
    ]
    print(json.dumps(changed, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "diff":
        print(f"Usage: {sys.argv[0]} diff BEFORE_COMMIT AFTER_COMMIT", file=sys.stderr)
        sys.exit(1)
    diff(sys.argv[2], sys.argv[3])
