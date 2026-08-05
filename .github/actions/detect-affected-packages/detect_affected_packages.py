#!/usr/bin/env python3

"""
Detect packages affected by a no-bump push to main.

Composes `package_versions.py diff`'s version-diff JSON (read from stdin) with
a JSON array of changed package directories (env var `CHANGED_DIRS`, from
tj-actions/changed-files' `dir_names` output) to find packages whose directory
changed without also changing their pyproject.toml version. Those need an
internal `.postN` build (see docs/versioning.md). Packages with a version bump
in the same range are excluded because they release via `release-trigger`
instead, and removed packages are excluded because there is nothing left to
build.

Run from the repository root, piping `package_versions.py diff`'s output in:

    python3 package_versions.py diff BEFORE AFTER \\
      | CHANGED_DIRS='["packages/overture-schema-common"]' python3 detect_affected_packages.py

Prints `$GITHUB_OUTPUT` lines on stdout (progress goes to stderr):

    count=<n>        Number of affected packages.
    packages=<json>  JSON array of affected package directory names, e.g.
                     ["overture-schema-common"]. Suitable as a matrix input.

Exit status:
    0  Success (including the no-affected case).
"""

import json
import os
import sys


def main() -> None:
    version_diff = json.load(sys.stdin)
    bumped = {
        change["package"]
        for change in version_diff
        if change["before"] is not None and change["after"] is not None
    }
    removed = {change["package"] for change in version_diff if change["after"] is None}

    changed_paths = json.loads(os.environ.get("CHANGED_DIRS") or "[]")
    changed = {path.split("/", 1)[1] for path in changed_paths}
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
