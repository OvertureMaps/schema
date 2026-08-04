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

Also enforces the major-bump cascade: a package whose direct workspace
dependency takes a major bump must take one itself (see
`check_major_cascade`).

Form of the JSON array:

    [ {"package": "p1", "before": "v1", "after": "v2"}, ... ]

`before` is null if the package did not exist at the before commit; `after` is
null if it no longer exists at the after commit.

Exit status:
    0  Success.
    1  Usage error, or a major bump that does not cascade to its dependents.
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
    except subprocess.CalledProcessError as e:
        # Expected when the commit is unreadable (force-push, history rewrite)
        # or predates the packages directory; anything else deserves eyes.
        print(
            f"::notice::No readable {PACKAGES_DIR}/ tree at {commit} "
            "(force-push or no packages directory yet); treating as empty.",
            file=sys.stderr,
        )
        stderr = e.stderr.decode("utf-8", errors="replace").strip()
        print(f"::debug::git ls-tree failed: {stderr}", file=sys.stderr)
        return {}

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
    graph = dependency_graph(manifests)
    return list(TopologicalSorter(graph).static_order())


def dependency_graph(manifests: dict[str, dict]) -> dict[str, set[str]]:
    """Map each package directory name to its direct workspace dependencies."""
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
    return graph


def manifest_version(manifests: dict[str, dict], package: str) -> str | None:
    """Static `project.version` of `package`, or None if absent/dynamic."""
    manifest = manifests.get(package)
    if manifest is None:
        return None
    value = manifest["project"].get("version")
    return str(value) if value is not None else None


def check_major_cascade(
    before_manifests: dict[str, dict], after_manifests: dict[str, dict]
) -> list[str]:
    """
    Enforce that major bumps cascade up the dependency tree.

    Workspace dependency floors are declared statically in each package's
    `project.dependencies`, so a major bump of a dependency is a breaking
    change behind every dependent's existing floor. A package whose
    direct workspace dependency takes a major bump must therefore take a
    major bump in the same change. Checking direct dependencies is enough:
    each unbumped link in a longer chain fails its own check.

    Returns a list of violation descriptions (empty when compliant).
    """

    def major(version: str | None) -> int | None:
        return int(version.split(".")[0]) if version else None

    errors = []
    for package, deps in dependency_graph(after_manifests).items():
        pkg_before = major(manifest_version(before_manifests, package))
        pkg_after = major(manifest_version(after_manifests, package))
        pkg_bumped = pkg_before is not None and pkg_after is not None and pkg_after > pkg_before

        for dep in sorted(deps):
            dep_before = major(manifest_version(before_manifests, dep))
            dep_after = major(manifest_version(after_manifests, dep))
            if dep_before is None or dep_after is None or dep_after <= dep_before:
                continue
            if not pkg_bumped:
                errors.append(
                    f"{package} depends on {dep}, which takes a major bump "
                    f"({dep_before}.x -> {dep_after}.x), but {package} does not. "
                    "Major bumps must cascade to dependents."
                )
    return errors


def diff(before: str, after: str) -> None:
    before_manifests = package_manifests(before)
    after_manifests = package_manifests(after)

    # Order from the after commit, which knows about newly added packages;
    # packages that only exist in before (deleted) are appended at the end.
    order = topo_order(after_manifests)
    order += sorted(set(before_manifests) - set(after_manifests))

    changed = [
        {"package": p, "before": b, "after": a}
        for p in order
        if (b := manifest_version(before_manifests, p))
        != (a := manifest_version(after_manifests, p))
    ]
    print(json.dumps(changed, indent=2))

    violations = check_major_cascade(before_manifests, after_manifests)
    if violations:
        for v in violations:
            print(f"::error::{v}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "diff":
        print(f"Usage: {sys.argv[0]} diff BEFORE_COMMIT AFTER_COMMIT", file=sys.stderr)
        sys.exit(1)
    diff(sys.argv[2], sys.argv[3])
