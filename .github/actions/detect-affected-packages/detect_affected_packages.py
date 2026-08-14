#!/usr/bin/env python3

"""
Detect packages affected by a no-bump push to main.

Composes `package_versions.py diff`'s version-diff JSON with a JSON array of
changed package directories (tj-actions/changed-files' `dir_names` output) to
find packages whose directory changed without also changing their
pyproject.toml version. Those need an internal `.postN` build (see
docs/versioning.md). Packages with a version bump in the same range are
excluded because they release via `release-trigger` instead, and removed
packages are excluded because there is nothing left to build.

Reads a single JSON object from stdin: {"version_diff": [...], "changed_dirs":
[...]}. Run from the repository root:

    jq -n \\
        --argjson version_diff "$(python3 package_versions.py diff BEFORE AFTER)" \\
        --argjson changed_dirs '["packages/overture-schema-common"]' \\
        '{version_diff: $version_diff, changed_dirs: $changed_dirs}' \\
      | python3 detect_affected_packages.py

Prints `$GITHUB_OUTPUT` lines on stdout (progress goes to stderr):

    count=<n>        Number of affected packages.
    packages=<json>  JSON array of affected package directory names, e.g.
                     ["overture-schema-common"]. Suitable as a matrix input.

Exit status:
    0  Success (including the no-affected case).
    1  Malformed input: a changed_dirs entry isn't packages/<pkg>.
"""

import json
import sys


def _package_name(path: str) -> str:
    """Extract <pkg> from a packages/<pkg> changed-directory entry."""
    parts = path.split("/", 1)
    if len(parts) < 2:
        raise ValueError(
            f"Expected a 'packages/<pkg>' changed-directory entry, got {path!r}. "
            "Check dir_names_max_depth on the changed-files step."
        )
    return parts[1]


def main() -> None:
    payload = json.load(sys.stdin)
    version_diff = payload["version_diff"]
    changed_paths = payload["changed_dirs"]

    bumped = {change["package"] for change in version_diff if change["after"] is not None}
    removed = {change["package"] for change in version_diff if change["after"] is None}

    changed = {_package_name(path) for path in changed_paths}
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
