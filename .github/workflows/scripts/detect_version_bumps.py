#!/usr/bin/env python3

"""
Detect per-package <major>.<minor> version bumps between two commits on main.

Run from the repository root by the `Release trigger` workflow. Compares each
`packages/*/pyproject.toml` at the pushed commit (the working tree) against its
content at the `before` commit, and records the packages whose <major>.<minor>
increased. Patch-only changes are ignored: the patch component is computed by
CI, not by humans (see docs/versioning.md).

Environment:
    BEFORE         The `before` commit SHA (github.event.before).
    GITHUB_OUTPUT  Step output file; receives `count` and `bumps`.

Outputs (written to $GITHUB_OUTPUT):
    count=<n>      Number of bumped packages.
    bumps=<json>   JSON array of {"package", "version", "tag"} objects, one per
                   bump. Consumed as a matrix by the release job.

Exit status:
    0  Success (including the no-bump case).
    1  A package's <major>.<minor> went backwards; that must never land on main.
"""

from pathlib import Path
import json
import os
import subprocess
import sys
import tomllib


def major_minor(blob: bytes) -> tuple[int, int]:
    """Parse `project.version` from pyproject.toml bytes into (major, minor)."""
    version = str(tomllib.loads(blob.decode("utf-8"))["project"]["version"])
    major, minor, *_ = version.split(".")
    return int(major), int(minor)


def before_major_minor(before: str, pyproject: str) -> tuple[int, int] | None:
    """
    Return the (major, minor) of `pyproject` at the `before` commit.

    The `before` blob can be unreadable after a force-push, a history rewrite,
    or for a brand-new package. Treat that as "no previous version" rather than
    failing every subsequent push.
    """
    result = subprocess.run(
        ["git", "show", f"{before}:{pyproject}"],
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return major_minor(result.stdout)


def main() -> None:
    before = os.environ["BEFORE"]

    bumps: list[dict[str, str]] = []
    errors: list[str] = []

    for path in sorted(Path("packages").glob("*/pyproject.toml")):
        package = path.parent.name
        pyproject = path.as_posix()  # git wants forward slashes on every OS

        after = major_minor(path.read_bytes())

        current = before_major_minor(before, pyproject)
        if current is None:
            print(f"No readable {pyproject} at {before}, skipping {package}.")
            continue

        if after == current:
            continue

        if after < current:
            errors.append(f"{package}: {current[0]}.{current[1]} -> {after[0]}.{after[1]}")
            continue

        version = f"{after[0]}.{after[1]}.0"
        print(f"{package}: {current[0]}.{current[1]} -> {after[0]}.{after[1]} (bump)")
        bumps.append({"package": package, "version": version, "tag": f"{package}-v{version}"})

    if errors:
        for e in errors:
            print(
                f"::error::{e}: major/minor went backwards. Version decreases "
                "must never land on main; revert or fix the version."
            )
        sys.exit(1)

    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        out.write(f"count={len(bumps)}\n")
        out.write(f"bumps={json.dumps(bumps)}\n")

    if not bumps:
        print("No major/minor bumps detected.")


if __name__ == "__main__":
    main()
