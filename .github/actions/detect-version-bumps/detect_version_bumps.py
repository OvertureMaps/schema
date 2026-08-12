#!/usr/bin/env python3

"""
Filter a package version diff down to releasable bumps.

Reads the JSON array produced by `package_versions.py diff` on stdin:

    [ {"package": "p1", "before": "v1", "after": "v2"}, ... ]

and emits `$GITHUB_OUTPUT` lines on stdout (progress goes to stderr):

    count=<n>      Number of bumped packages.
    bumps=<json>   JSON array of {"package", "version", "tag"} objects, one per
                   bump. Consumed as a matrix by the release job.

Policy applied (see docs/versioning.md):
  - Released versions must be plain `<major>.<minor>.<patch>`; PEP 440
    variants like `1.2.3rc4` fail loudly.
  - A version decrease fails: it must never land on main.
  - Added packages (`before` null) count as a bump: a package's first
    version releases to PyPI like any other. Removed packages (`after`
    null) are not releases; they are skipped.

The `detect-version-bumps` action composes this with `package_versions.py`,
which owns reading versions from git (and enforces the major-bump cascade
via its own exit status).

Exit status:
    0  Success (including the no-bump case).
    1  A version is not plain X.Y.Z, or went backwards.
"""

import json
import re
import sys

# Released versions are plain X.Y.Z by policy (docs/versioning.md); PEP 440
# variants like 1.2.3rc4 or 1.2.3.post1 must not appear in pyproject.toml.
PLAIN_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def semver(package: str, version: str) -> tuple[int, int, int]:
    match = PLAIN_SEMVER.match(version)
    if not match:
        raise ValueError(
            f"{package}: version {version!r} is not plain <major>.<minor>.<patch>; "
            "pre-release/post-release segments are not allowed in pyproject.toml "
            "(see docs/versioning.md)"
        )
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def info(message: str) -> None:
    print(message, file=sys.stderr)


def main() -> None:
    changes = json.load(sys.stdin)

    bumps: list[dict[str, str]] = []
    errors: list[str] = []

    for change in changes:
        package = change["package"]
        before_raw = change["before"]
        after_raw = change["after"]

        if after_raw is None:
            info(f"{package}: removed, not a release. Skipping.")
            continue

        after = semver(package, after_raw)

        if before_raw is None:
            info(f"{package}: new package at {after_raw} (bump)")
            bumps.append({"package": package, "version": after_raw, "tag": f"{package}-v{after_raw}"})
            continue

        before = semver(package, before_raw)

        if after < before:
            errors.append(f"{package}: {before_raw} -> {after_raw}")
            continue

        info(f"{package}: {before_raw} -> {after_raw} (bump)")
        bumps.append({"package": package, "version": after_raw, "tag": f"{package}-v{after_raw}"})

    if errors:
        for e in errors:
            info(
                f"::error::{e}: version went backwards. Version decreases "
                "must never land on main; revert or fix the version."
            )
        sys.exit(1)

    if not bumps:
        info("No version bumps detected.")

    print(f"count={len(bumps)}")
    print(f"bumps={json.dumps(bumps)}")


if __name__ == "__main__":
    main()
