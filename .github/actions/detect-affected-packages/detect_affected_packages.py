#!/usr/bin/env python3

"""
Detect packages affected by a no-bump push to main.

Composes `package_versions.py diff`'s version-diff JSON (read from stdin) with
a file-level `git diff` to find packages whose directory changed without also
changing their pyproject.toml version. Those need an internal `.postN` build
(see docs/versioning.md). Packages with a version bump in the same range are
excluded because they release via `release-trigger` instead, and removed
packages are excluded because there is nothing left to build.

Run from the repository root, piping `package_versions.py diff`'s output in:

    python3 package_versions.py diff BEFORE AFTER \\
      | python3 detect_affected_packages.py BEFORE AFTER

Prints `$GITHUB_OUTPUT` lines on stdout (progress goes to stderr):

    count=<n>        Number of affected packages.
    packages=<json>  JSON array of affected package directory names, e.g.
                     ["overture-schema-common"]. Suitable as a matrix input.

Exit status:
    0  Success (including the no-affected case).
"""

import json
import subprocess
import sys

PACKAGES_DIR = "packages"


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, check=True)
    return result.stdout.decode("utf-8")


def changed_package_dirs(before: str, after: str) -> set[str]:
    """Package directory names with any file change under packages/<pkg>/."""
    diff = git("diff", "--name-only", f"{before}..{after}", "--", f"{PACKAGES_DIR}/")
    names = set()
    for line in diff.splitlines():
        parts = line.split("/", 2)
        if len(parts) >= 2:
            names.add(parts[1])
    return names


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} BEFORE_COMMIT AFTER_COMMIT", file=sys.stderr)
        sys.exit(1)
    before, after = sys.argv[1], sys.argv[2]

    version_diff = json.load(sys.stdin)
    bumped = {
        change["package"]
        for change in version_diff
        if change["before"] is not None and change["after"] is not None
    }
    removed = {change["package"] for change in version_diff if change["after"] is None}

    changed = changed_package_dirs(before, after)
    affected = sorted(changed - bumped - removed)

    for package in sorted(changed):
        if package in removed:
            print(f"{package}: removed. Skipping.", file=sys.stderr)
        elif package in bumped:
            print(
                f"{package}: version bumped, handled by release-trigger. "
                "Skipping internal build.",
                file=sys.stderr,
            )
        else:
            print(f"{package}: changed, no bump -> internal build.", file=sys.stderr)

    if not affected:
        print("No affected packages (no unreleased changes to publish).", file=sys.stderr)

    print(f"count={len(affected)}")
    print(f"packages={json.dumps(affected)}")


if __name__ == "__main__":
    main()
