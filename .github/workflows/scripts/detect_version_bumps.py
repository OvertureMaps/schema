#!/usr/bin/env python3

"""
Detect per-package version bumps between two commits on main.

Run from the repository root by the `Release trigger` workflow. Compares each
`packages/*/pyproject.toml` at the pushed commit (the working tree) against its
content at the `before` commit, and records the packages whose
`<major>.<minor>.<patch>` increased. All three components are human-owned
(see docs/versioning.md); any increase, including patch-only, cuts a release.

Environment:
    BEFORE         The `before` commit SHA (github.event.before).
    GITHUB_OUTPUT  Step output file; receives `count` and `bumps`.

Outputs (written to $GITHUB_OUTPUT):
    count=<n>      Number of bumped packages.
    bumps=<json>   JSON array of {"package", "version", "tag"} objects, one per
                   bump. Consumed as a matrix by the release job.

Exit status:
    0  Success (including the no-bump case).
    1  A package's version went backwards; that must never land on main.
"""

from collections.abc import Callable
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import tomllib

VERSION_ASSIGNMENT = re.compile(rb"""^__version__\s*=\s*["']([^"']+)["']""", re.MULTILINE)


def semver(
    pyproject_blob: bytes,
    package_dir: str,
    read_file: Callable[[str], bytes | None],
) -> tuple[int, int, int] | None:
    """
    Resolve a package's (major, minor, patch) from its pyproject.toml bytes.

    Static `project.version` is read directly. A hatch dynamic version is
    resolved by reading the declared version file through `read_file`, which
    takes a repo-relative posix path and returns its bytes (or None if
    unreadable, in which case the version is unresolvable).
    """
    doc = tomllib.loads(pyproject_blob.decode("utf-8"))
    if "version" in doc["project"]:
        version = str(doc["project"]["version"])
    else:
        version_path = f'{package_dir}/{doc["tool"]["hatch"]["version"]["path"]}'
        content = read_file(version_path)
        if content is None:
            return None
        match = VERSION_ASSIGNMENT.search(content)
        if not match:
            return None
        version = match.group(1).decode("utf-8")
    major, minor, patch, *_ = version.split(".")
    return int(major), int(minor), int(patch)


def git_show(commit: str, path: str) -> bytes | None:
    """
    Return the bytes of `path` at `commit`, or None if unreadable.

    A blob can be unreadable after a force-push, a history rewrite, or for a
    brand-new file. Treat that as "no previous version" rather than failing
    every subsequent push.
    """
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def main() -> None:
    before = os.environ["BEFORE"]

    bumps: list[dict[str, str]] = []
    errors: list[str] = []

    def read_working_tree(path: str) -> bytes | None:
        try:
            return Path(path).read_bytes()
        except OSError:
            return None

    for path in sorted(Path("packages").glob("*/pyproject.toml")):
        package = path.parent.name
        package_dir = path.parent.as_posix()  # git wants forward slashes on every OS
        pyproject = path.as_posix()

        after = semver(path.read_bytes(), package_dir, read_working_tree)
        if after is None:
            print(f"Cannot resolve version for {package} in the working tree, skipping.")
            continue

        before_blob = git_show(before, pyproject)
        current = (
            semver(before_blob, package_dir, lambda p: git_show(before, p))
            if before_blob is not None
            else None
        )
        if current is None:
            print(f"No resolvable version for {package} at {before}, skipping.")
            continue

        if after == current:
            continue

        before_str = ".".join(map(str, current))
        after_str = ".".join(map(str, after))

        if after < current:
            errors.append(f"{package}: {before_str} -> {after_str}")
            continue

        print(f"{package}: {before_str} -> {after_str} (bump)")
        bumps.append({"package": package, "version": after_str, "tag": f"{package}-v{after_str}"})

    if errors:
        for e in errors:
            print(
                f"::error::{e}: version went backwards. Version decreases "
                "must never land on main; revert or fix the version."
            )
        sys.exit(1)

    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        out.write(f"count={len(bumps)}\n")
        out.write(f"bumps={json.dumps(bumps)}\n")

    if not bumps:
        print("No version bumps detected.")


if __name__ == "__main__":
    main()
